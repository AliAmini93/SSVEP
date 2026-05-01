"""
Step 04 v4: harmonic-aware / CCA-based SSVEP analysis.

Purpose
-------
Step 03 showed usable but asymmetric SSVEP evidence:
- 9 Hz/left was strong, but partly overlaps with alpha.
- 14 Hz/right was weaker at the fundamental, but showed a strong 28 Hz harmonic.

This script runs a more standard SSVEP detector using multichannel CCA
with sine/cosine reference signals and harmonics.

Inputs expected:
- g.USBamp HDF5 files in data_dir
- Step 02 outputs in data_dir/_analysis_report/step02:
    02_trial_event_match.csv
    02_channel_quality.csv
- Step 03 helper script next to this file:
    03_detailed_ssvep_analysis.py

Outputs:
- data_dir/_analysis_report/step04/
    04_summary_report.txt
    04_trial_level_cca.csv
    04_condition_cca_summary.csv
    04_cca_9_vs_14_scatter.png
    04_cca_accuracy_by_condition.png
    04_cca_trial_margin.png
"""

import argparse
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal
import matplotlib.pyplot as plt


LEFT_FREQ = 9.0
RIGHT_FREQ = 14.0


def load_step03_helpers(script_dir):
    helper_path = script_dir / "03_detailed_ssvep_analysis.py"
    if not helper_path.exists():
        raise FileNotFoundError(
            f"Could not find {helper_path}. Put this Step 04 script next to 03_detailed_ssvep_analysis.py"
        )

    spec = importlib.util.spec_from_file_location("step03_helpers", str(helper_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_reference_signals(freq_hz, fs, n_samples, n_harmonics=3, max_freq=45.0):
    """Create sin/cos reference matrix for CCA."""
    t = np.arange(n_samples) / float(fs)
    cols = []

    used_harmonics = []
    for h in range(1, n_harmonics + 1):
        f = freq_hz * h
        if f > max_freq:
            continue
        cols.append(np.sin(2 * np.pi * f * t))
        cols.append(np.cos(2 * np.pi * f * t))
        used_harmonics.append(f)

    if not cols:
        raise ValueError(f"No valid harmonics for {freq_hz} Hz")

    Y = np.column_stack(cols)
    return Y, used_harmonics


def center_scale(X):
    X = np.asarray(X, dtype=float)
    X = X - np.mean(X, axis=0, keepdims=True)
    sd = np.std(X, axis=0, keepdims=True)
    sd[sd == 0] = 1.0
    return X / sd


def invsqrtm_sym(C, reg=1e-6):
    C = np.asarray(C, dtype=float)
    C = (C + C.T) / 2.0
    vals, vecs = np.linalg.eigh(C)
    vals = np.maximum(vals, reg)
    return vecs @ np.diag(1.0 / np.sqrt(vals)) @ vecs.T


def cca_first_corr(X, Y, reg=1e-5):
    """First canonical correlation between multichannel EEG X and reference Y."""
    X = center_scale(X)
    Y = center_scale(Y)

    n = X.shape[0]
    if n < 10:
        return np.nan

    Cxx = (X.T @ X) / (n - 1)
    Cyy = (Y.T @ Y) / (n - 1)
    Cxy = (X.T @ Y) / (n - 1)

    Wx = invsqrtm_sym(Cxx, reg=reg)
    Wy = invsqrtm_sym(Cyy, reg=reg)
    M = Wx @ Cxy @ Wy

    try:
        s = np.linalg.svd(M, compute_uv=False)
        return float(np.clip(s[0], 0, 1))
    except Exception:
        return np.nan


def condition_label(side):
    side = str(side).lower()
    return "left_9hz" if side == "left" else "right_14hz"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--include_review_channels", action="store_true")
    ap.add_argument("--analysis_start_s", type=float, default=2.0)
    ap.add_argument("--analysis_end_s", type=float, default=29.0)
    ap.add_argument("--n_harmonics", type=int, default=3)
    ap.add_argument("--max_ref_freq", type=float, default=45.0)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    script_dir = Path(__file__).resolve().parent
    step03 = load_step03_helpers(script_dir)

    out_dir = data_dir / "_analysis_report" / "step04"
    out_dir.mkdir(parents=True, exist_ok=True)

    step02_dir = data_dir / "_analysis_report" / "step02"
    trial_match_path = step02_dir / "02_trial_event_match.csv"
    qc_path = step02_dir / "02_channel_quality.csv"

    if not trial_match_path.exists():
        raise FileNotFoundError(f"Missing Step 02 trial match file: {trial_match_path}")
    if not qc_path.exists():
        raise FileNotFoundError(f"Missing Step 02 channel quality file: {qc_path}")

    trial_match = pd.read_csv(trial_match_path)
    qc = pd.read_csv(qc_path)

    h5_files = sorted(list(data_dir.glob("*.hdf5")) + list(data_dir.glob("*.h5")))
    if not h5_files:
        raise FileNotFoundError(f"No HDF5 files found in {data_dir}")

    print("Loading and merging HDF5 files...")

    # Step 03 helper versions have changed across our iterations.
    # Some versions return:
    #   (data, triggers, file_summaries, fs, names)
    # while earlier variants may return:
    #   (data, names, fs, file_summaries)
    # We infer each object by type/shape so this script does not break again.
    load_result = step03.load_merge(h5_files)
    if not isinstance(load_result, (tuple, list)):
        raise RuntimeError("step03.load_merge did not return a tuple/list; cannot continue.")

    merged = None
    names = None
    fs = None
    file_summaries = None

    for item in load_result:
        if isinstance(item, np.ndarray) and item.ndim == 2:
            merged = item
        elif isinstance(item, (int, float, np.integer, np.floating)):
            fs = float(item)
        elif isinstance(item, (list, tuple)) and item:
            # Channel names: list of strings, length should match n_channels if data is already known.
            if all(isinstance(x, str) for x in item):
                names = list(item)
            # File summaries: list of dictionaries containing HDF5 metadata.
            elif all(isinstance(x, dict) for x in item):
                file_summaries = list(item)

    if merged is None:
        raise RuntimeError("Could not identify merged EEG data from step03.load_merge output.")
    if fs is None:
        raise RuntimeError("Could not identify sampling rate from step03.load_merge output.")
    if names is None:
        raise RuntimeError("Could not identify channel names from step03.load_merge output.")
    if file_summaries is None:
        file_summaries = []

    print(f"Merged data shape: {merged.shape}, fs={fs}, channels={len(names)}")

    include_status = ("good", "review") if args.include_review_channels else ("good",)
    choose_result = step03.choose_channels(names, qc, include_status=include_status)
    if not isinstance(choose_result, (tuple, list)) or len(choose_result) < 2:
        raise RuntimeError("step03.choose_channels returned an unexpected format.")

    a, b = choose_result[0], choose_result[1]

    # Current Step 03 returns: (selected_channel_names, selected_indices, qc_status)
    # Some older variants may return: (selected_indices, selected_channel_names)
    if isinstance(a, (list, tuple)) and a and all(isinstance(x, str) for x in a):
        ch_names = list(a)
        ch_idx = list(b)
    else:
        ch_idx = list(a)
        ch_names = list(b)

    if not ch_idx:
        raise RuntimeError("No selected channels. Check Step 02 channel quality output.")

    print("Selected channels:", ", ".join(ch_names))

    # Filter the selected posterior channels only.
    x = merged[:, ch_idx]
    x_filt = step03.bandpass_notch_filter(x, fs, highpass=1.0, lowpass=45.0, notch=50.0)

    # Step 02 variants may store trial onset as either:
    # - stim_start_sample / stim_end_sample  (current version)
    # - stim_onset_time_s                    (older/alternate version)
    # Use samples when available because they avoid ambiguity after merging HDF5 files.
    available_cols = set(trial_match.columns)
    if "stim_start_sample" in available_cols:
        onset_mode = "sample"
        print("Using trial onsets from column: stim_start_sample")
    elif "stim_onset_time_s" in available_cols:
        onset_mode = "time"
        print("Using trial onsets from column: stim_onset_time_s")
    else:
        raise KeyError(
            "Could not find trial onset column. Expected 'stim_start_sample' or 'stim_onset_time_s'. "
            f"Available columns are: {list(trial_match.columns)}"
        )

    rows = []

    for _, tr in trial_match.iterrows():
        if onset_mode == "sample":
            onset_sample = int(round(float(tr["stim_start_sample"])))
            start_i = int(round(onset_sample + args.analysis_start_s * fs))
            end_i = int(round(onset_sample + args.analysis_end_s * fs))
        else:
            onset_s = float(tr["stim_onset_time_s"])
            start_i = int(round((onset_s + args.analysis_start_s) * fs))
            end_i = int(round((onset_s + args.analysis_end_s) * fs))

        if start_i < 0 or end_i > x_filt.shape[0] or end_i <= start_i:
            continue

        seg = x_filt[start_i:end_i, :]
        n_samples = seg.shape[0]

        ref9, harm9 = make_reference_signals(
            LEFT_FREQ, fs, n_samples, n_harmonics=args.n_harmonics, max_freq=args.max_ref_freq
        )
        ref14, harm14 = make_reference_signals(
            RIGHT_FREQ, fs, n_samples, n_harmonics=args.n_harmonics, max_freq=args.max_ref_freq
        )

        rho9 = cca_first_corr(seg, ref9)
        rho14 = cca_first_corr(seg, ref14)

        predicted = "left" if rho9 > rho14 else "right"
        actual = str(tr["attend_side"]).lower()

        rows.append({
            "trial_index_1based": int(tr["trial_index_1based"]),
            "block": int(tr["block"]),
            "trial_in_block": int(tr["trial_in_block"]),
            "attend_side": actual,
            "condition": condition_label(actual),
            "analysis_start_s": args.analysis_start_s,
            "analysis_end_s": args.analysis_end_s,
            "analysis_duration_s": args.analysis_end_s - args.analysis_start_s,
            "n_selected_channels": len(ch_names),
            "selected_channels": ",".join(ch_names),
            "cca_rho_9hz": rho9,
            "cca_rho_14hz": rho14,
            "cca_margin_9_minus_14": rho9 - rho14,
            "predicted_side_cca": predicted,
            "prediction_correct_cca": bool(predicted == actual),
            "ref_9hz_harmonics_used": ",".join(f"{x:g}" for x in harm9),
            "ref_14hz_harmonics_used": ",".join(f"{x:g}" for x in harm14),
        })

    trial_df = pd.DataFrame(rows)
    trial_csv = out_dir / "04_trial_level_cca.csv"
    trial_df.to_csv(trial_csv, index=False)

    cond_rows = []
    for cond, d in trial_df.groupby("condition"):
        cond_rows.append({
            "condition": cond,
            "n_trials": int(len(d)),
            "mean_cca_rho_9hz": float(d["cca_rho_9hz"].mean()),
            "median_cca_rho_9hz": float(d["cca_rho_9hz"].median()),
            "mean_cca_rho_14hz": float(d["cca_rho_14hz"].mean()),
            "median_cca_rho_14hz": float(d["cca_rho_14hz"].median()),
            "mean_cca_margin_9_minus_14": float(d["cca_margin_9_minus_14"].mean()),
            "median_cca_margin_9_minus_14": float(d["cca_margin_9_minus_14"].median()),
            "cca_prediction_accuracy": float(d["prediction_correct_cca"].mean()),
        })

    cond_df = pd.DataFrame(cond_rows)
    cond_csv = out_dir / "04_condition_cca_summary.csv"
    cond_df.to_csv(cond_csv, index=False)

    overall_acc = float(trial_df["prediction_correct_cca"].mean()) if len(trial_df) else np.nan
    left_acc = float(trial_df.loc[trial_df["attend_side"] == "left", "prediction_correct_cca"].mean())
    right_acc = float(trial_df.loc[trial_df["attend_side"] == "right", "prediction_correct_cca"].mean())

    # Plot 1: CCA scatter
    plt.figure(figsize=(8, 7))
    for side, label in [("left", "left trials"), ("right", "right trials")]:
        d = trial_df[trial_df["attend_side"] == side]
        plt.scatter(d["cca_rho_9hz"], d["cca_rho_14hz"], label=label)
    mn = min(trial_df["cca_rho_9hz"].min(), trial_df["cca_rho_14hz"].min())
    mx = max(trial_df["cca_rho_9hz"].max(), trial_df["cca_rho_14hz"].max())
    plt.plot([mn, mx], [mn, mx], "--")
    plt.xlabel("CCA rho for 9 Hz references")
    plt.ylabel("CCA rho for 14 Hz references")
    plt.title("CCA evidence: 9 Hz vs 14 Hz")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "04_cca_9_vs_14_scatter.png", dpi=150)
    plt.close()

    # Plot 2: accuracy by condition
    plt.figure(figsize=(7, 5))
    acc_by_cond = cond_df.set_index("condition")["cca_prediction_accuracy"].sort_index()
    plt.bar(acc_by_cond.index, acc_by_cond.values)
    plt.ylim(0, 1)
    plt.ylabel("CCA classification accuracy")
    plt.title("CCA accuracy by condition")
    plt.tight_layout()
    plt.savefig(out_dir / "04_cca_accuracy_by_condition.png", dpi=150)
    plt.close()

    # Plot 3: trial margins
    colors = ["tab:blue" if s == "left" else "tab:orange" for s in trial_df["attend_side"]]
    plt.figure(figsize=(12, 5))
    plt.bar(trial_df["trial_index_1based"], trial_df["cca_margin_9_minus_14"], color=colors)
    plt.axhline(0, linewidth=1)
    plt.xlabel("Trial")
    plt.ylabel("CCA margin: rho(9 Hz) - rho(14 Hz)")
    plt.title("Trial-level CCA margin")
    plt.tight_layout()
    plt.savefig(out_dir / "04_cca_trial_margin.png", dpi=150)
    plt.close()

    report_path = out_dir / "04_summary_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("STEP 04 HARMONIC-AWARE CCA SSVEP REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write("Input\n")
        f.write("-" * 80 + "\n")
        f.write(f"HDF5 files loaded: {len(h5_files)}\n")
        for i, s in enumerate(file_summaries, 1):
            file_label = s.get("file", s.get("path", s.get("name", "unknown_file")))
            duration_s = float(s.get("duration_s", float("nan")))
            n_triggers = int(len(s.get("trigger_typeids", []))) if "trigger_typeids" in s else int(s.get("n_triggers", 0))
            f.write(f"  {i}. {file_label} | duration={duration_s:.2f}s | triggers={n_triggers}\n")
        f.write(f"Sampling rate: {fs:.3f} Hz\n")
        f.write(f"Total merged samples: {merged.shape[0]}\n")
        f.write(f"Trials analyzed: {len(trial_df)}\n")
        f.write(f"Analysis window: {args.analysis_start_s:.2f} to {args.analysis_end_s:.2f} s after trial onset\n")
        f.write(f"Included QC statuses: {', '.join(include_status)}\n")
        f.write(f"Selected channels ({len(ch_names)}): {', '.join(ch_names)}\n")
        f.write(f"CCA harmonics for 9 Hz: {trial_df['ref_9hz_harmonics_used'].iloc[0] if len(trial_df) else 'NA'}\n")
        f.write(f"CCA harmonics for 14 Hz: {trial_df['ref_14hz_harmonics_used'].iloc[0] if len(trial_df) else 'NA'}\n\n")

        f.write("CCA classification\n")
        f.write("-" * 80 + "\n")
        f.write(f"Overall CCA accuracy: {overall_acc * 100:.1f}%\n")
        f.write(f"Left / 9 Hz CCA accuracy: {left_acc * 100:.1f}%\n")
        f.write(f"Right / 14 Hz CCA accuracy: {right_acc * 100:.1f}%\n\n")

        f.write("Condition summary\n")
        f.write("-" * 80 + "\n")
        for _, r in cond_df.iterrows():
            f.write(
                f"{r['condition']}: n={int(r['n_trials'])}, "
                f"mean rho9={r['mean_cca_rho_9hz']:.4f}, "
                f"mean rho14={r['mean_cca_rho_14hz']:.4f}, "
                f"mean margin 9-14={r['mean_cca_margin_9_minus_14']:.4f}, "
                f"accuracy={r['cca_prediction_accuracy'] * 100:.1f}%\n"
            )

        f.write("\nInterpretation guide\n")
        f.write("-" * 80 + "\n")
        f.write("CCA is a standard SSVEP detection approach because it uses sine/cosine references and harmonics.\n")
        f.write("For left trials, rho(9 Hz) should be higher than rho(14 Hz).\n")
        f.write("For right trials, rho(14 Hz) should be higher than rho(9 Hz).\n")
        f.write("This is especially useful here because the right/14 Hz condition showed a strong 28 Hz harmonic in Step 03.\n")

    print("\nDone. Output folder:", out_dir)
    print("Please send back:")
    print(" ", report_path)
    print(" ", trial_csv)
    print(" ", cond_csv)
    print("Useful plots:")
    print(" ", out_dir / "04_cca_9_vs_14_scatter.png")
    print(" ", out_dir / "04_cca_accuracy_by_condition.png")
    print(" ", out_dir / "04_cca_trial_margin.png")


if __name__ == "__main__":
    main()
