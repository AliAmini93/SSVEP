#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Step 05: Permutation / sanity-check control for harmonic-aware CCA SSVEP results
------------------------------------------------------------------------------

Purpose
-------
This script checks whether the 100% CCA classification result from Step 04 is
likely to be a real condition-specific SSVEP effect rather than a trivial
artifact or label/order accident.

It uses the already-created Step 04 file:
    _analysis_report/step04/04_trial_level_cca.csv

It does NOT need to reload the raw HDF5 EEG files.

Outputs
-------
Creates:
    _analysis_report/step05/05_summary_report.txt
    _analysis_report/step05/05_trial_sanity_check.csv
    _analysis_report/step05/05_permutation_accuracy_distribution.csv
    _analysis_report/step05/05_permutation_accuracy_hist.png
    _analysis_report/step05/05_signed_margin_hist.png
    _analysis_report/step05/05_target_vs_nontarget_rho.png

Recommended run
---------------
python 05_permutation_sanity_check.py --data_dir "PATH_TO_RECORDING_FOLDER"

Example
-------
python 05_permutation_sanity_check.py --data_dir "F:\\KTU\\Lithuania\\Secondment Denmark\\Codes\\First SSVEP EEG Recording- Overt"
"""

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def find_step04_file(data_dir: Path, step04_dir: str = None) -> Path:
    """Find 04_trial_level_cca.csv."""
    if step04_dir is not None:
        candidate = Path(step04_dir) / "04_trial_level_cca.csv"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Could not find: {candidate}")

    candidate = data_dir / "_analysis_report" / "step04" / "04_trial_level_cca.csv"
    if candidate.exists():
        return candidate

    matches = list(data_dir.rglob("04_trial_level_cca.csv"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        # Prefer one inside step04 if possible
        for m in matches:
            if "step04" in [p.lower() for p in m.parts]:
                return m
        return matches[0]

    raise FileNotFoundError(
        "Could not find 04_trial_level_cca.csv. "
        "Run Step 04 first, or pass --step04_dir."
    )


def exact_label_permutation_p_value(true_labels, pred_labels, observed_correct):
    """Exact p-value for fixed predictions and shuffled labels in a binary balanced-ish setup.

    We assume labels are left/right. Predictions are fixed, and labels are randomly
    permuted while preserving the number of left/right labels.

    This is equivalent to a hypergeometric test over the number of true-left labels
    falling inside the predicted-left set.
    """
    true_labels = np.asarray(true_labels)
    pred_labels = np.asarray(pred_labels)

    n = len(true_labels)
    n_left = int(np.sum(true_labels == "left"))
    n_pred_left = int(np.sum(pred_labels == "left"))

    # Let X = number of true-left labels among predicted-left positions.
    # X ~ Hypergeometric(N=n, K=n_left, draws=n_pred_left)
    # total correct = X + true-right among predicted-right
    # true-right among predicted-right = (n - n_pred_left) - (n_left - X)
    # correct = n - n_pred_left - n_left + 2X
    denom = math.comb(n, n_pred_left)
    p = 0.0
    rows = []
    x_min = max(0, n_pred_left - (n - n_left))
    x_max = min(n_left, n_pred_left)

    for x in range(x_min, x_max + 1):
        ways = math.comb(n_left, x) * math.comb(n - n_left, n_pred_left - x)
        prob = ways / denom
        correct = n - n_pred_left - n_left + 2 * x
        acc = correct / n
        rows.append((x, correct, acc, prob))
        if correct >= observed_correct:
            p += prob

    return p, pd.DataFrame(rows, columns=["x_true_left_in_pred_left", "correct", "accuracy", "probability"])


def permutation_accuracy(true_labels, pred_labels, n_perm=10000, seed=12345):
    """Monte-Carlo label-shuffle control."""
    rng = np.random.default_rng(seed)
    true_labels = np.asarray(true_labels)
    pred_labels = np.asarray(pred_labels)

    acc = np.empty(n_perm, dtype=float)
    for i in range(n_perm):
        shuffled = rng.permutation(true_labels)
        acc[i] = np.mean(shuffled == pred_labels)

    observed = np.mean(true_labels == pred_labels)
    p = (np.sum(acc >= observed) + 1.0) / (n_perm + 1.0)
    return observed, acc, p


def sign_flip_margin_test(signed_margins, n_perm=10000, seed=54321):
    """Sign-flip test for target-vs-non-target CCA margin."""
    rng = np.random.default_rng(seed)
    signed_margins = np.asarray(signed_margins, dtype=float)
    observed_mean = float(np.mean(signed_margins))
    null_means = np.empty(n_perm, dtype=float)

    for i in range(n_perm):
        signs = rng.choice([-1.0, 1.0], size=len(signed_margins), replace=True)
        null_means[i] = np.mean(signed_margins * signs)

    p = (np.sum(null_means >= observed_mean) + 1.0) / (n_perm + 1.0)
    return observed_mean, null_means, p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True, help="Recording folder containing _analysis_report/step04")
    parser.add_argument("--step04_dir", default=None, help="Optional direct path to step04 folder")
    parser.add_argument("--n_perm", type=int, default=10000, help="Number of Monte-Carlo permutations")
    parser.add_argument("--seed", type=int, default=12345)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    step04_file = find_step04_file(data_dir, args.step04_dir)

    out_dir = data_dir / "_analysis_report" / "step05"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(step04_file)

    required = ["attend_side", "cca_rho_9hz", "cca_rho_14hz"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {step04_file}: {missing}")

    # Normalize labels
    df["attend_side"] = df["attend_side"].astype(str).str.strip().str.lower()

    # Recompute predicted side directly from CCA scores
    df["predicted_side_recomputed"] = np.where(df["cca_rho_9hz"] > df["cca_rho_14hz"], "left", "right")
    df["prediction_correct_recomputed"] = df["predicted_side_recomputed"] == df["attend_side"]

    # Target and non-target rho according to true label
    df["target_rho"] = np.where(df["attend_side"] == "left", df["cca_rho_9hz"], df["cca_rho_14hz"])
    df["nontarget_rho"] = np.where(df["attend_side"] == "left", df["cca_rho_14hz"], df["cca_rho_9hz"])
    df["signed_target_margin"] = df["target_rho"] - df["nontarget_rho"]

    observed_accuracy, null_acc, perm_p = permutation_accuracy(
        df["attend_side"].values,
        df["predicted_side_recomputed"].values,
        n_perm=args.n_perm,
        seed=args.seed,
    )

    exact_p, exact_dist = exact_label_permutation_p_value(
        df["attend_side"].values,
        df["predicted_side_recomputed"].values,
        int(df["prediction_correct_recomputed"].sum()),
    )

    observed_mean_margin, null_margin, margin_perm_p = sign_flip_margin_test(
        df["signed_target_margin"].values,
        n_perm=args.n_perm,
        seed=args.seed + 1,
    )

    # Per-condition summary
    cond_summary = (
        df.groupby("attend_side")
        .agg(
            n_trials=("attend_side", "size"),
            mean_rho9=("cca_rho_9hz", "mean"),
            mean_rho14=("cca_rho_14hz", "mean"),
            mean_target_rho=("target_rho", "mean"),
            mean_nontarget_rho=("nontarget_rho", "mean"),
            mean_signed_target_margin=("signed_target_margin", "mean"),
            min_signed_target_margin=("signed_target_margin", "min"),
            max_signed_target_margin=("signed_target_margin", "max"),
            accuracy=("prediction_correct_recomputed", "mean"),
        )
        .reset_index()
    )

    # Save CSVs
    df.to_csv(out_dir / "05_trial_sanity_check.csv", index=False)

    pd.DataFrame({
        "permutation_index": np.arange(1, args.n_perm + 1),
        "accuracy": null_acc,
        "signed_margin_null_mean": null_margin,
    }).to_csv(out_dir / "05_permutation_accuracy_distribution.csv", index=False)

    exact_dist.to_csv(out_dir / "05_exact_label_shuffle_distribution.csv", index=False)
    cond_summary.to_csv(out_dir / "05_condition_sanity_summary.csv", index=False)

    # Plots
    plt.figure(figsize=(9, 5))
    plt.hist(null_acc, bins=np.linspace(0, 1, 21), edgecolor="black")
    plt.axvline(observed_accuracy, linestyle="--", linewidth=2)
    plt.xlabel("Accuracy after shuffled labels")
    plt.ylabel("Count")
    plt.title("Permutation control: shuffled-label accuracy")
    plt.tight_layout()
    plt.savefig(out_dir / "05_permutation_accuracy_hist.png", dpi=150)
    plt.close()

    plt.figure(figsize=(9, 5))
    plt.hist(null_margin, bins=30, edgecolor="black")
    plt.axvline(observed_mean_margin, linestyle="--", linewidth=2)
    plt.xlabel("Mean signed target margin under sign-flip null")
    plt.ylabel("Count")
    plt.title("Sign-flip control: target-vs-non-target CCA margin")
    plt.tight_layout()
    plt.savefig(out_dir / "05_signed_margin_hist.png", dpi=150)
    plt.close()

    plt.figure(figsize=(7, 6))
    x = np.arange(len(df))
    plt.scatter(x, df["target_rho"], label="target rho")
    plt.scatter(x, df["nontarget_rho"], label="non-target rho")
    plt.xlabel("Trial")
    plt.ylabel("CCA rho")
    plt.title("Target vs non-target CCA rho per trial")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "05_target_vs_nontarget_rho.png", dpi=150)
    plt.close()

    plt.figure(figsize=(7, 6))
    plt.scatter(df["nontarget_rho"], df["target_rho"])
    lim_min = float(min(df["nontarget_rho"].min(), df["target_rho"].min()))
    lim_max = float(max(df["nontarget_rho"].max(), df["target_rho"].max()))
    plt.plot([lim_min, lim_max], [lim_min, lim_max], linestyle="--")
    plt.xlabel("Non-target CCA rho")
    plt.ylabel("Target CCA rho")
    plt.title("Target rho should exceed non-target rho")
    plt.tight_layout()
    plt.savefig(out_dir / "05_target_vs_nontarget_scatter.png", dpi=150)
    plt.close()

    # Summary text
    n_trials = len(df)
    n_left = int(np.sum(df["attend_side"].values == "left"))
    n_right = int(np.sum(df["attend_side"].values == "right"))
    n_pred_left = int(np.sum(df["predicted_side_recomputed"].values == "left"))
    n_pred_right = int(np.sum(df["predicted_side_recomputed"].values == "right"))
    n_correct = int(df["prediction_correct_recomputed"].sum())

    report = []
    report.append("STEP 05 PERMUTATION / SANITY-CHECK REPORT")
    report.append("=" * 80)
    report.append("")
    report.append("Input")
    report.append("-" * 80)
    report.append(f"Step 04 trial file: {step04_file}")
    report.append(f"Trials analyzed: {n_trials}")
    report.append(f"True labels: left={n_left}, right={n_right}")
    report.append(f"Predicted labels: left={n_pred_left}, right={n_pred_right}")
    report.append("")
    report.append("Observed result")
    report.append("-" * 80)
    report.append(f"Observed correct trials: {n_correct}/{n_trials}")
    report.append(f"Observed accuracy: {observed_accuracy * 100.0:.2f}%")
    report.append(f"Mean target rho: {df['target_rho'].mean():.6f}")
    report.append(f"Mean non-target rho: {df['nontarget_rho'].mean():.6f}")
    report.append(f"Mean signed target margin: {observed_mean_margin:.6f}")
    report.append(f"Minimum signed target margin: {df['signed_target_margin'].min():.6f}")
    report.append("")
    report.append("Condition summary")
    report.append("-" * 80)
    for _, row in cond_summary.iterrows():
        report.append(
            f"{row['attend_side']}: n={int(row['n_trials'])}, "
            f"accuracy={row['accuracy'] * 100.0:.1f}%, "
            f"mean target rho={row['mean_target_rho']:.6f}, "
            f"mean non-target rho={row['mean_nontarget_rho']:.6f}, "
            f"mean margin={row['mean_signed_target_margin']:.6f}, "
            f"min margin={row['min_signed_target_margin']:.6f}"
        )
    report.append("")
    report.append("Permutation controls")
    report.append("-" * 80)
    report.append(f"Monte-Carlo label-shuffle permutations: {args.n_perm}")
    report.append(f"Monte-Carlo shuffled-label p-value for accuracy >= observed: {perm_p:.8f}")
    report.append(f"Exact label-shuffle p-value for accuracy >= observed: {exact_p:.12g}")
    report.append(f"Monte-Carlo sign-flip p-value for mean target margin >= observed: {margin_perm_p:.8f}")
    report.append("")
    report.append("Interpretation")
    report.append("-" * 80)
    if observed_accuracy == 1.0 and exact_p < 0.001:
        report.append(
            "The observed CCA classification is far above what would be expected "
            "from shuffled labels. This supports the interpretation that the Step 04 "
            "classification reflects condition-specific SSVEP structure rather than "
            "a trivial label/order artifact."
        )
    else:
        report.append(
            "The observed CCA classification should be interpreted with caution. "
            "Check the permutation distribution, condition balance, and trial-level margins."
        )

    if df["signed_target_margin"].min() > 0:
        report.append(
            "Every trial had target CCA rho greater than non-target CCA rho. "
            "This is a strong trial-level sanity check."
        )
    else:
        report.append(
            "At least one trial had non-target CCA rho greater than target CCA rho. "
            "Inspect 05_trial_sanity_check.csv for those trials."
        )

    (out_dir / "05_summary_report.txt").write_text("\n".join(report), encoding="utf-8")

    print("")
    print("Done. Output folder:", out_dir)
    print("Please send back:")
    print(" ", out_dir / "05_summary_report.txt")
    print(" ", out_dir / "05_trial_sanity_check.csv")
    print(" ", out_dir / "05_condition_sanity_summary.csv")
    print("Useful plots:")
    print(" ", out_dir / "05_permutation_accuracy_hist.png")
    print(" ", out_dir / "05_signed_margin_hist.png")
    print(" ", out_dir / "05_target_vs_nontarget_rho.png")
    print(" ", out_dir / "05_target_vs_nontarget_scatter.png")


if __name__ == "__main__":
    main()
