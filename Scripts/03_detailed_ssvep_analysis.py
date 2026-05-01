"""
Step 03: detailed SSVEP analysis for the overt/direct-gaze pilot.

Inputs expected:
- g.USBamp HDF5 files in data_dir
- Step 02 outputs in data_dir/_analysis_report/step02:
    02_trial_event_match.csv
    02_channel_quality.csv
    02_summary_report.txt

Outputs:
- data_dir/_analysis_report/step03/03_summary_report.txt
- Trial-level, channel-level, and condition-level SSVEP summaries
- Diagnostic plots for SSVEP evidence
"""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

import h5py
import numpy as np
import pandas as pd
from scipy import signal
import matplotlib.pyplot as plt


# -----------------------------
# HDF5 helpers
# -----------------------------
def dtext(x):
    if isinstance(x, np.ndarray):
        x = x[0]
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    return str(x)


def tag(x):
    return x.split("}", 1)[-1] if "}" in x else x


def child_text(elem, name, default=None):
    for c in elem:
        if tag(c.tag) == name:
            return c.text
    return default


def parse_acq_xml(xml_text):
    root = ET.fromstring(xml_text)
    out = {"recording_date_begin": None, "sampling_frequency": None, "channels": []}

    for e in root.iter():
        t = tag(e.tag)
        if t == "RecordingDateBegin":
            out["recording_date_begin"] = e.text
        elif t == "SamplingFrequency":
            try:
                out["sampling_frequency"] = float(e.text)
            except Exception:
                pass

    for e in root.iter():
        if tag(e.tag) != "ChannelProperties":
            continue

        name = child_text(e, "ChannelName")
        logical = child_text(e, "LogicalChannelNumber")

        if not name or name.strip() == "" or logical is None:
            continue

        try:
            logical = int(logical)
        except Exception:
            continue

        sr = child_text(e, "SampleRate")
        try:
            sr = float(sr)
        except Exception:
            sr = np.nan

        out["channels"].append({
            "logical_channel_number": logical,
            "channel_name": name,
            "channel_type": child_text(e, "ChannelType"),
            "sample_rate": sr,
            "device_number": child_text(e, "DeviceNumber"),
            "device_name": child_text(e, "DeviceName"),
        })

    out["channels"] = sorted(out["channels"], key=lambda r: r["logical_channel_number"])
    return out


def dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def inspect_h5(path):
    path = Path(path)
    with h5py.File(path, "r") as f:
        samples_shape = tuple(f["/RawData/Samples"].shape)
        acq = parse_acq_xml(dtext(f["/RawData/AcquisitionTaskDescription"][()]))
        fs = acq.get("sampling_frequency")
        if fs is None:
            srs = [
                c["sample_rate"]
                for c in acq["channels"]
                if np.isfinite(c["sample_rate"]) and c["sample_rate"] > 0
            ]
            fs = float(pd.Series(srs).mode().iloc[0]) if srs else np.nan

        t = np.asarray(f["/AsynchronData/Time"][:]).reshape(-1).astype(np.int64)
        typ = np.asarray(f["/AsynchronData/TypeID"][:]).reshape(-1).astype(np.int64)
        val = np.asarray(f["/AsynchronData/Value"][:]).reshape(-1).astype(np.int64)

    return {
        "path": str(path),
        "name": path.name,
        "n_samples": int(samples_shape[0]),
        "n_channels": int(samples_shape[1]),
        "fs": float(fs),
        "duration_s": float(samples_shape[0] / fs),
        "recording_date_begin": acq.get("recording_date_begin"),
        "recording_datetime": dt(acq.get("recording_date_begin")),
        "channels": acq["channels"],
        "trigger_times_local": t,
        "trigger_typeids": typ,
        "trigger_values": val,
    }


def load_samples(path):
    with h5py.File(path, "r") as f:
        return np.asarray(f["/RawData/Samples"][:], dtype=np.float32)


def load_merge(h5_files):
    infos = [inspect_h5(p) for p in h5_files]
    infos = sorted(
        infos,
        key=lambda r: (
            r["recording_datetime"] is None,
            r["recording_datetime"] or datetime.min,
            r["name"],
        ),
    )

    if len(set(round(i["fs"], 6) for i in infos)) != 1:
        raise RuntimeError("Sampling rates differ across files.")

    fs = infos[0]["fs"]
    names = [c["channel_name"] for c in infos[0]["channels"]]

    xs = []
    offset = 0
    trigger_rows = []

    for fi, info in enumerate(infos):
        print(f"Loading EEG samples: {info['name']}")
        xs.append(load_samples(info["path"]))

        for t, typ, val in zip(info["trigger_times_local"], info["trigger_typeids"], info["trigger_values"]):
            trigger_rows.append({
                "file_index": fi,
                "file_name": info["name"],
                "local_sample": int(t),
                "merged_sample": int(t + offset),
                "time_s": float((t + offset) / fs),
                "type_id": int(typ),
                "value": int(val),
            })

        offset += info["n_samples"]

    data = np.vstack(xs)
    triggers = pd.DataFrame(trigger_rows).sort_values("merged_sample").reset_index(drop=True)
    return data, triggers, infos, fs, names


# -----------------------------
# Analysis helpers
# -----------------------------
def normalize_status(s):
    if pd.isna(s):
        return "unknown"
    return str(s).strip().lower()


def choose_channels(names, qc, include_status=("good", "review")):
    posterior_priority = [
        "O1", "Oz", "O2",
        "PO7", "PO3", "POz", "PO4", "PO8",
        "P7", "P5", "P3", "P1", "Pz", "P2", "P4", "P6", "P8",
    ]

    qc_status = {
        row["channel_name"]: normalize_status(row["auto_status"])
        for _, row in qc.iterrows()
    }

    selected = []
    for ch in posterior_priority:
        if ch in names and qc_status.get(ch, "unknown") in include_status:
            selected.append(ch)

    # Fallback: if metadata names differ, take all non-bad channels.
    if not selected:
        selected = [ch for ch in names if qc_status.get(ch, "unknown") in include_status]

    selected_idx = [names.index(ch) for ch in selected]
    return selected, selected_idx, qc_status


def bandpass_notch_filter(x, fs, highpass=1.0, lowpass=45.0, notch=50.0, apply_notch=True):
    """Filter shape: samples x channels."""
    y = np.asarray(x, dtype=np.float64)

    if highpass is not None or lowpass is not None:
        nyq = fs / 2.0
        if highpass is not None and lowpass is not None:
            b, a = signal.butter(4, [highpass / nyq, lowpass / nyq], btype="bandpass")
        elif highpass is not None:
            b, a = signal.butter(4, highpass / nyq, btype="highpass")
        else:
            b, a = signal.butter(4, lowpass / nyq, btype="lowpass")
        y = signal.filtfilt(b, a, y, axis=0)

    if apply_notch and notch is not None and notch < fs / 2.0:
        b, a = signal.iirnotch(w0=notch, Q=30.0, fs=fs)
        y = signal.filtfilt(b, a, y, axis=0)

    return y


def compute_psd(seg, fs, nperseg_s=8.0):
    nper = int(min(len(seg), round(nperseg_s * fs)))
    nper = max(nper, int(min(len(seg), fs * 2)))
    nover = min(nper // 2, max(0, len(seg) // 2 - 1))
    f, p = signal.welch(
        seg,
        fs=fs,
        axis=0,
        nperseg=nper,
        noverlap=nover,
        detrend=False,
        scaling="density",
    )
    return f, p


def snr_from_psd(f, p, f0, noise_width=2.0, exclude_width=0.35):
    """Return SNR dB per channel for PSD matrix frequency x channels."""
    idx = int(np.argmin(np.abs(f - f0)))
    power = p[idx, :]

    noise_mask = (
        (f >= f0 - noise_width)
        & (f <= f0 + noise_width)
        & (np.abs(f - f0) >= exclude_width)
    )

    # Remove possible target-adjacent bins and ensure enough noise bins.
    if not np.any(noise_mask):
        return np.full(p.shape[1], np.nan), power, np.full(p.shape[1], np.nan), float(f[idx])

    noise = np.nanmean(p[noise_mask, :], axis=0)
    snr = power / noise
    snr_db = 10.0 * np.log10(snr)
    return snr_db, power, noise, float(f[idx])


def parse_stim_duration_from_match(tev):
    durations = tev["stim_end_time_s"] - tev["stim_start_time_s"]
    durations = durations.replace([np.inf, -np.inf], np.nan).dropna()
    return float(durations.median()) if len(durations) else np.nan


def condition_label(side):
    side = str(side).lower()
    return "left_9hz" if side == "left" else "right_14hz"


def safe_mean(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.mean(x)) if len(x) else np.nan


def safe_median(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if len(x) else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", required=True, help="Folder containing the HDF5 EEG files.")
    ap.add_argument("--step02_dir", default=None, help="Folder containing Step 02 outputs. Default: data_dir/_analysis_report/step02")
    ap.add_argument("--out_dir", default=None, help="Output folder. Default: data_dir/_analysis_report/step03")
    ap.add_argument("--analysis_start_s", type=float, default=2.0, help="Seconds to skip after each trial onset.")
    ap.add_argument("--analysis_end_s", type=float, default=29.0, help="End of analysis window relative to trial onset.")
    ap.add_argument("--include_review_channels", action="store_true", help="Include review channels in posterior channel set.")
    ap.add_argument("--no_filter", action="store_true", help="Disable 1-45 Hz + 50 Hz notch filtering.")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    step02_dir = Path(args.step02_dir) if args.step02_dir else data_dir / "_analysis_report" / "step02"
    out_dir = Path(args.out_dir) if args.out_dir else data_dir / "_analysis_report" / "step03"
    out_dir.mkdir(parents=True, exist_ok=True)

    tev_path = step02_dir / "02_trial_event_match.csv"
    qc_path = step02_dir / "02_channel_quality.csv"

    if not tev_path.exists():
        raise FileNotFoundError(f"Missing Step 02 trial-event file: {tev_path}")
    if not qc_path.exists():
        raise FileNotFoundError(f"Missing Step 02 channel-QC file: {qc_path}")

    tev = pd.read_csv(tev_path)
    qc = pd.read_csv(qc_path)

    h5s = sorted(list(data_dir.glob("*.hdf5")) + list(data_dir.glob("*.h5")))
    if not h5s:
        raise FileNotFoundError(f"No .hdf5/.h5 files found in: {data_dir}")

    data, triggers, infos, fs, names = load_merge(h5s)
    print(f"Merged data shape: {data.shape}, fs={fs}, channels={len(names)}")

    include_status = ("good", "review") if args.include_review_channels else ("good",)
    selected_ch, selected_idx, qc_status = choose_channels(names, qc, include_status=include_status)

    if not selected_idx:
        raise RuntimeError("No selected channels available after QC filtering.")

    print("Selected posterior channels:", ", ".join(selected_ch))

    stim_dur_s = parse_stim_duration_from_match(tev)
    analysis_start_s = args.analysis_start_s
    analysis_end_s = args.analysis_end_s

    if not np.isfinite(stim_dur_s):
        stim_dur_s = 30.0

    if analysis_end_s > stim_dur_s:
        analysis_end_s = max(analysis_start_s + 1.0, stim_dur_s - 1.0)

    freqs = [9.0, 14.0]
    harmonics = [18.0, 28.0]
    all_check_freqs = freqs + harmonics

    trial_rows = []
    channel_rows = []
    psd_acc = {
        "left": [],
        "right": [],
    }

    f_ref = None

    for _, tr in tev.iterrows():
        trial = int(tr["trial_index_1based"])
        side = str(tr["attend_side"]).lower()
        target_freq = 9.0 if side == "left" else 14.0
        non_target_freq = 14.0 if side == "left" else 9.0

        start_sample = int(round(float(tr["stim_start_sample"]) + analysis_start_s * fs))
        end_sample = int(round(float(tr["stim_start_sample"]) + analysis_end_s * fs))

        if start_sample < 0 or end_sample > data.shape[0] or end_sample <= start_sample:
            continue

        seg_all = data[start_sample:end_sample, :].astype(np.float64)
        seg = seg_all[:, selected_idx]

        # Detrend and center before filtering.
        seg = signal.detrend(seg, axis=0, type="linear")
        seg = seg - np.nanmean(seg, axis=0, keepdims=True)

        if not args.no_filter:
            seg = bandpass_notch_filter(seg, fs=fs, highpass=1.0, lowpass=45.0, notch=50.0, apply_notch=True)

        f, p = compute_psd(seg, fs=fs, nperseg_s=8.0)
        f_ref = f

        # Save condition-average PSD over selected posterior channels.
        psd_acc[side].append(np.nanmean(p, axis=1))

        # SNRs for each selected channel at each frequency.
        snr_by_freq = {}
        for f0 in all_check_freqs:
            snr_db, power, noise, nearest_bin = snr_from_psd(f, p, f0)
            snr_by_freq[f0] = snr_db

            for ch_i, ch_name in enumerate(selected_ch):
                is_target = abs(f0 - target_freq) < 1e-9
                is_second_harmonic_target = abs(f0 - 2.0 * target_freq) < 1e-9
                channel_rows.append({
                    "trial_index_1based": trial,
                    "block": int(tr["block"]),
                    "trial_in_block": int(tr["trial_in_block"]),
                    "attend_side": side,
                    "condition": condition_label(side),
                    "channel_name": ch_name,
                    "qc_status": qc_status.get(ch_name, "unknown"),
                    "frequency_checked_hz": f0,
                    "nearest_psd_bin_hz": nearest_bin,
                    "snr_db": snr_db[ch_i],
                    "is_target_fundamental": bool(is_target),
                    "is_target_second_harmonic": bool(is_second_harmonic_target),
                })

        target_snr_ch = snr_by_freq[target_freq]
        non_target_snr_ch = snr_by_freq[non_target_freq]

        target_snr_mean = safe_mean(target_snr_ch)
        non_target_snr_mean = safe_mean(non_target_snr_ch)
        evidence_db = target_snr_mean - non_target_snr_mean

        snr_9_mean = safe_mean(snr_by_freq[9.0])
        snr_14_mean = safe_mean(snr_by_freq[14.0])
        predicted_side = "left" if snr_9_mean > snr_14_mean else "right"

        # Harmonics
        target_h2 = 2.0 * target_freq
        non_target_h2 = 2.0 * non_target_freq

        target_h2_snr = safe_mean(snr_by_freq[target_h2]) if target_h2 in snr_by_freq else np.nan
        non_target_h2_snr = safe_mean(snr_by_freq[non_target_h2]) if non_target_h2 in snr_by_freq else np.nan

        trial_rows.append({
            "trial_index_1based": trial,
            "block": int(tr["block"]),
            "trial_in_block": int(tr["trial_in_block"]),
            "attend_side": side,
            "condition": condition_label(side),
            "target_freq_hz": target_freq,
            "non_target_freq_hz": non_target_freq,
            "analysis_start_s": analysis_start_s,
            "analysis_end_s": analysis_end_s,
            "analysis_duration_s": analysis_end_s - analysis_start_s,
            "n_selected_channels": len(selected_ch),
            "selected_channels": ",".join(selected_ch),
            "mean_snr_9hz_db": snr_9_mean,
            "mean_snr_14hz_db": snr_14_mean,
            "mean_target_snr_db": target_snr_mean,
            "mean_non_target_snr_db": non_target_snr_mean,
            "target_minus_nontarget_snr_db": evidence_db,
            "mean_target_second_harmonic_snr_db": target_h2_snr,
            "mean_nontarget_second_harmonic_snr_db": non_target_h2_snr,
            "predicted_side_from_9_vs_14": predicted_side,
            "prediction_correct": bool(predicted_side == side),
        })

    trial_df = pd.DataFrame(trial_rows)
    channel_df = pd.DataFrame(channel_rows)

    if len(trial_df) == 0:
        raise RuntimeError("No valid trials were analyzed. Check trigger samples and analysis window.")

    # Summaries
    condition_summary = (
        trial_df
        .groupby("condition", dropna=False)
        .agg(
            n_trials=("trial_index_1based", "count"),
            mean_target_snr_db=("mean_target_snr_db", "mean"),
            median_target_snr_db=("mean_target_snr_db", "median"),
            mean_non_target_snr_db=("mean_non_target_snr_db", "mean"),
            median_non_target_snr_db=("mean_non_target_snr_db", "median"),
            mean_target_minus_nontarget_db=("target_minus_nontarget_snr_db", "mean"),
            median_target_minus_nontarget_db=("target_minus_nontarget_snr_db", "median"),
            mean_target_h2_snr_db=("mean_target_second_harmonic_snr_db", "mean"),
            prediction_accuracy=("prediction_correct", "mean"),
        )
        .reset_index()
    )

    channel_condition_summary = (
        channel_df[
            (channel_df["is_target_fundamental"])
            | (channel_df["frequency_checked_hz"].isin([9.0, 14.0]))
        ]
        .groupby(["channel_name", "condition", "frequency_checked_hz"], dropna=False)
        .agg(
            mean_snr_db=("snr_db", "mean"),
            median_snr_db=("snr_db", "median"),
            n=("snr_db", "count"),
        )
        .reset_index()
    )

    # Best channels based on target-minus-nontarget evidence.
    best_rows = []
    for ch in selected_ch:
        sub = channel_df[channel_df["channel_name"] == ch]
        if len(sub) == 0:
            continue

        per_trial = []
        for trial in trial_df["trial_index_1based"]:
            tr_side = trial_df.loc[trial_df["trial_index_1based"] == trial, "attend_side"].iloc[0]
            target = 9.0 if tr_side == "left" else 14.0
            nontarget = 14.0 if tr_side == "left" else 9.0
            a = sub[(sub["trial_index_1based"] == trial) & (sub["frequency_checked_hz"] == target)]["snr_db"]
            b = sub[(sub["trial_index_1based"] == trial) & (sub["frequency_checked_hz"] == nontarget)]["snr_db"]
            if len(a) and len(b):
                per_trial.append(float(a.iloc[0] - b.iloc[0]))

        best_rows.append({
            "channel_name": ch,
            "qc_status": qc_status.get(ch, "unknown"),
            "mean_target_minus_nontarget_snr_db": safe_mean(per_trial),
            "median_target_minus_nontarget_snr_db": safe_median(per_trial),
            "n_trials": len(per_trial),
        })

    best_channels = pd.DataFrame(best_rows).sort_values(
        "mean_target_minus_nontarget_snr_db",
        ascending=False,
    )

    # Save CSV outputs.
    trial_df.to_csv(out_dir / "03_trial_level_ssvep.csv", index=False)
    channel_df.to_csv(out_dir / "03_channel_trial_snr_long.csv", index=False)
    condition_summary.to_csv(out_dir / "03_condition_summary.csv", index=False)
    channel_condition_summary.to_csv(out_dir / "03_channel_condition_summary.csv", index=False)
    best_channels.to_csv(out_dir / "03_best_channels.csv", index=False)
    pd.DataFrame({"selected_channel": selected_ch}).to_csv(out_dir / "03_selected_channels.csv", index=False)

    # -----------------------------
    # Plots
    # -----------------------------
    # Condition bar plot.
    plt.figure(figsize=(8, 5))
    x = np.arange(len(condition_summary))
    width = 0.35
    plt.bar(x - width / 2, condition_summary["mean_target_snr_db"], width, label="target freq")
    plt.bar(x + width / 2, condition_summary["mean_non_target_snr_db"], width, label="non-target freq")
    plt.xticks(x, condition_summary["condition"])
    plt.ylabel("Mean SNR (dB)")
    plt.title("Target vs non-target SSVEP SNR by condition")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "03_condition_target_vs_nontarget_snr.png", dpi=150)
    plt.close()

    # Trial-level evidence plot.
    plt.figure(figsize=(12, 5))
    colors = ["C0" if s == "left" else "C1" for s in trial_df["attend_side"]]
    plt.bar(trial_df["trial_index_1based"], trial_df["target_minus_nontarget_snr_db"], color=colors)
    plt.axhline(0, linewidth=1)
    plt.xlabel("Trial")
    plt.ylabel("Target - non-target SNR (dB)")
    plt.title("Trial-level SSVEP evidence")
    plt.tight_layout()
    plt.savefig(out_dir / "03_trial_level_evidence.png", dpi=150)
    plt.close()

    # 9 vs 14 scatter.
    plt.figure(figsize=(6, 6))
    for side, label in [("left", "left trials"), ("right", "right trials")]:
        sub = trial_df[trial_df["attend_side"] == side]
        plt.scatter(sub["mean_snr_9hz_db"], sub["mean_snr_14hz_db"], label=label)
    mn = np.nanmin([trial_df["mean_snr_9hz_db"].min(), trial_df["mean_snr_14hz_db"].min()])
    mx = np.nanmax([trial_df["mean_snr_9hz_db"].max(), trial_df["mean_snr_14hz_db"].max()])
    plt.plot([mn, mx], [mn, mx], linestyle="--", linewidth=1)
    plt.xlabel("Mean SNR at 9 Hz (dB)")
    plt.ylabel("Mean SNR at 14 Hz (dB)")
    plt.title("Trial classification evidence: 9 Hz vs 14 Hz")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "03_snr_9_vs_14_scatter.png", dpi=150)
    plt.close()

    # Best channels plot.
    top_n = min(15, len(best_channels))
    plt.figure(figsize=(10, 5))
    top = best_channels.head(top_n)
    plt.bar(top["channel_name"], top["mean_target_minus_nontarget_snr_db"])
    plt.xticks(rotation=45)
    plt.ylabel("Mean target - non-target SNR (dB)")
    plt.title("Best posterior channels for SSVEP evidence")
    plt.tight_layout()
    plt.savefig(out_dir / "03_best_channels_evidence.png", dpi=150)
    plt.close()

    # Average PSD over selected posterior channels.
    if f_ref is not None:
        plt.figure(figsize=(10, 6))
        for side, label in [("left", "left / 9 Hz target"), ("right", "right / 14 Hz target")]:
            if psd_acc[side]:
                pmean = np.nanmean(np.vstack(psd_acc[side]), axis=0)
                plt.semilogy(f_ref, pmean, label=label)
        for f0 in [9, 14, 18, 28]:
            plt.axvline(f0, linestyle="--", linewidth=1)
        plt.xlim(1, 35)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD")
        plt.title("Average posterior PSD by condition")
        plt.legend()
        plt.tight_layout()
        plt.savefig(out_dir / "03_selected_posterior_psd_by_condition.png", dpi=150)
        plt.close()

    # -----------------------------
    # Summary report
    # -----------------------------
    acc = float(trial_df["prediction_correct"].mean())
    mean_target = float(trial_df["mean_target_snr_db"].mean())
    mean_nontarget = float(trial_df["mean_non_target_snr_db"].mean())
    mean_diff = float(trial_df["target_minus_nontarget_snr_db"].mean())
    med_diff = float(trial_df["target_minus_nontarget_snr_db"].median())

    left_acc = float(trial_df[trial_df["attend_side"] == "left"]["prediction_correct"].mean())
    right_acc = float(trial_df[trial_df["attend_side"] == "right"]["prediction_correct"].mean())

    with open(out_dir / "03_summary_report.txt", "w", encoding="utf-8") as f:
        f.write("STEP 03 DETAILED SSVEP REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write("Input and alignment\n")
        f.write("-" * 80 + "\n")
        f.write(f"HDF5 files loaded: {len(infos)}\n")
        for i, info in enumerate(infos, start=1):
            f.write(f"  {i}. {info['name']} | duration={info['duration_s']:.2f}s | triggers={len(info['trigger_typeids'])}\n")
        f.write(f"Sampling rate: {fs:.3f} Hz\n")
        f.write(f"Total merged samples: {data.shape[0]}\n")
        f.write(f"Total merged duration: {data.shape[0] / fs:.2f} s\n")
        f.write(f"Step 02 trials used: {len(tev)}\n")
        f.write(f"Trials analyzed in Step 03: {len(trial_df)}\n")
        f.write(f"Analysis window: {analysis_start_s:.2f} to {analysis_end_s:.2f} s after trial onset\n")
        f.write(f"Filtering: {'disabled' if args.no_filter else '1-45 Hz bandpass + 50 Hz notch'}\n\n")

        f.write("Channel selection\n")
        f.write("-" * 80 + "\n")
        f.write(f"Included QC statuses: {', '.join(include_status)}\n")
        f.write(f"Selected channels ({len(selected_ch)}): {', '.join(selected_ch)}\n")
        f.write("Best channels by target-minus-non-target evidence:\n")
        for _, row in best_channels.head(10).iterrows():
            f.write(
                f"  {row['channel_name']}: "
                f"mean diff={row['mean_target_minus_nontarget_snr_db']:.3f} dB, "
                f"median diff={row['median_target_minus_nontarget_snr_db']:.3f} dB, "
                f"status={row['qc_status']}\n"
            )
        f.write("\n")

        f.write("SSVEP evidence\n")
        f.write("-" * 80 + "\n")
        f.write(f"Mean target SNR: {mean_target:.3f} dB\n")
        f.write(f"Mean non-target SNR: {mean_nontarget:.3f} dB\n")
        f.write(f"Mean target-minus-non-target SNR: {mean_diff:.3f} dB\n")
        f.write(f"Median target-minus-non-target SNR: {med_diff:.3f} dB\n")
        f.write(f"Simple 9-vs-14 trial classification accuracy: {acc * 100:.1f}%\n")
        f.write(f"  Left/9Hz trials accuracy: {left_acc * 100:.1f}%\n")
        f.write(f"  Right/14Hz trials accuracy: {right_acc * 100:.1f}%\n\n")

        f.write("Condition summary\n")
        f.write("-" * 80 + "\n")
        for _, row in condition_summary.iterrows():
            f.write(
                f"{row['condition']}: n={int(row['n_trials'])}, "
                f"target SNR={row['mean_target_snr_db']:.3f} dB, "
                f"non-target SNR={row['mean_non_target_snr_db']:.3f} dB, "
                f"target-non-target={row['mean_target_minus_nontarget_db']:.3f} dB, "
                f"classification acc={row['prediction_accuracy'] * 100:.1f}%\n"
            )
        f.write("\n")

        f.write("Interpretation guide\n")
        f.write("-" * 80 + "\n")
        if mean_diff > 1.0 and acc >= 0.65:
            interpretation = "Positive: the recording shows usable SSVEP evidence."
        elif mean_diff > 0.3:
            interpretation = "Weak-positive: SSVEP evidence is present but not very strong."
        else:
            interpretation = "Inconclusive/weak: SSVEP evidence is limited with this channel set."
        f.write(f"{interpretation}\n")
        f.write("Important caveat: 9 Hz overlaps with natural alpha activity, so 9 Hz effects should be interpreted carefully.\n")
        f.write("The 14 Hz response and 28 Hz harmonic are useful additional evidence for the right-target condition.\n\n")

        f.write("Generated files\n")
        f.write("-" * 80 + "\n")
        for p in sorted(out_dir.glob("*")):
            f.write(f"{p.name}\n")

    print("\nDone. Output folder:", out_dir)
    print("Please send back these files:")
    for name in [
        "03_summary_report.txt",
        "03_condition_summary.csv",
        "03_best_channels.csv",
        "03_trial_level_ssvep.csv",
        "03_channel_condition_summary.csv",
    ]:
        print(" ", out_dir / name)

    print("Useful plots:")
    for name in [
        "03_condition_target_vs_nontarget_snr.png",
        "03_trial_level_evidence.png",
        "03_snr_9_vs_14_scatter.png",
        "03_best_channels_evidence.png",
        "03_selected_posterior_psd_by_condition.png",
    ]:
        print(" ", out_dir / name)


if __name__ == "__main__":
    main()
