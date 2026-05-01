"""
Step 02: merge g.USBamp HDF5 recordings, check photodiode triggers, run channel QC,
and perform a first SSVEP PSD/SNR check.
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
            "physical_channel_number": child_text(e, "PhysicalChannelNumber"),
            "channel_name": name,
            "channel_type": child_text(e, "ChannelType"),
            "sample_rate": sr,
            "device_number": child_text(e, "DeviceNumber"),
            "device_name": child_text(e, "DeviceName"),
            "notch_filter": child_text(e, "NotchFilter"),
            "highpass_filter": child_text(e, "HighpassFilter"),
            "lowpass_filter": child_text(e, "LowpassFilter"),
        })
    out["channels"] = sorted(out["channels"], key=lambda r: r["logical_channel_number"])
    return out


def parse_async_xml(xml_text):
    root = ET.fromstring(xml_text)
    rows = []
    for e in root.iter():
        if tag(e.tag) != "AsynchronSignalDescription":
            continue
        row = {
            "name": child_text(e, "Name"),
            "id": child_text(e, "ID"),
            "edge": child_text(e, "Edge"),
            "description": child_text(e, "Description"),
            "channel_number": child_text(e, "ChannelNumber"),
            "is_trigger": child_text(e, "IsTrigger"),
        }
        for k in ["id", "channel_number"]:
            try:
                row[k] = int(row[k])
            except Exception:
                pass
        rows.append(row)
    seen, clean = set(), []
    for r in rows:
        key = tuple(sorted(r.items()))
        if key not in seen:
            seen.add(key)
            clean.append(r)
    return clean


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
        async_desc = parse_async_xml(dtext(f["/AsynchronData/AsynchronSignalTypes"][()]))
        fs = acq.get("sampling_frequency")
        if fs is None:
            srs = [c["sample_rate"] for c in acq["channels"] if np.isfinite(c["sample_rate"]) and c["sample_rate"] > 0]
            fs = float(pd.Series(srs).mode().iloc[0]) if srs else np.nan
        t = np.asarray(f["/AsynchronData/Time"][:]).reshape(-1).astype(np.int64)
        typ = np.asarray(f["/AsynchronData/TypeID"][:]).reshape(-1).astype(np.int64)
        val = np.asarray(f["/AsynchronData/Value"][:]).reshape(-1).astype(np.int64)
    return {
        "path": str(path),
        "name": path.name,
        "size_mb": round(path.stat().st_size / (1024 * 1024), 3),
        "samples_shape": samples_shape,
        "n_samples": int(samples_shape[0]),
        "n_channels": int(samples_shape[1]),
        "fs": float(fs),
        "duration_s": float(samples_shape[0] / fs),
        "recording_date_begin": acq.get("recording_date_begin"),
        "recording_datetime": dt(acq.get("recording_date_begin")),
        "channels": acq["channels"],
        "async_descriptions": async_desc,
        "trigger_times_local": t,
        "trigger_typeids": typ,
        "trigger_values": val,
    }


def load_samples(path):
    with h5py.File(path, "r") as f:
        return np.asarray(f["/RawData/Samples"][:], dtype=np.float32)


def load_merge(h5_files):
    infos = [inspect_h5(p) for p in h5_files]
    infos = sorted(infos, key=lambda r: (r["recording_datetime"] is None, r["recording_datetime"] or datetime.min, r["name"]))
    if len(set(round(i["fs"], 6) for i in infos)) != 1:
        raise RuntimeError("Sampling rates differ across files.")
    fs = infos[0]["fs"]
    names = [c["channel_name"] for c in infos[0]["channels"]]
    xs, trig_rows = [], []
    offset = 0
    for fi, info in enumerate(infos):
        print("Loading", info["name"])
        xs.append(load_samples(info["path"]))
        for t, typ, val in zip(info["trigger_times_local"], info["trigger_typeids"], info["trigger_values"]):
            trig_rows.append({
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
    triggers = pd.DataFrame(trig_rows).sort_values("merged_sample").reset_index(drop=True)
    return data, triggers, infos, fs, names


def best_trials_csv(psychopy_dir):
    candidates = sorted(Path(psychopy_dir).glob("*_trials.csv"))
    if not candidates:
        raise FileNotFoundError("No *_trials.csv found.")
    scored = []
    for p in candidates:
        try:
            scored.append((len(pd.read_csv(p)), p))
        except Exception:
            scored.append((-1, p))
    scored.sort(key=lambda x: (x[0], str(x[1])), reverse=True)
    if scored[0][0] <= 0:
        raise RuntimeError("No non-empty trials CSV found.")
    return scored[0][1]


def parse_stim_dur(meta_path):
    if not meta_path or not Path(meta_path).exists():
        return None
    txt = Path(meta_path).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"Stimulation duration:\s*([0-9.]+)\s*s", txt, re.I)
    return float(m.group(1)) if m else None


def load_psychopy(psychopy_dir, trials_csv=None):
    p = Path(trials_csv) if trials_csv else best_trials_csv(psychopy_dir)
    trials = pd.read_csv(p)
    meta = None
    if p.name.endswith("_trials.csv"):
        m = p.with_name(p.name.replace("_trials.csv", "_meta.txt"))
        if m.exists():
            meta = m
    return trials, p, meta, parse_stim_dur(meta)


def infer_mapping(triggers, trials):
    counts = trials["expected_photodiode_pulses"].astype(int).to_list()
    sides = trials["attend_side"].astype(str).str.lower().to_list()
    typ = triggers["type_id"].astype(int).to_numpy()
    uniq = sorted(np.unique(typ).tolist())
    if len(uniq) != 2:
        return None, {"error": f"Expected 2 TypeIDs, found {uniq}"}
    candidates = [{uniq[0]: "left", uniq[1]: "right"}, {uniq[0]: "right", uniq[1]: "left"}]
    scores = []
    for mp in candidates:
        idx, good_events, good_trials = 0, 0, 0
        for ti, n in enumerate(counts):
            seg = typ[idx:idx+n]
            idx += n
            mapped = [mp.get(int(x), "unknown") for x in seg]
            ng = sum(1 for x in mapped if x == sides[ti])
            good_events += ng
            good_trials += int(ng == len(seg) and len(seg) == n)
        scores.append({"mapping": mp, "good_events": int(good_events), "good_trials": int(good_trials), "total_events": int(sum(counts)), "total_trials": len(counts)})
    best = sorted(scores, key=lambda r: (r["good_events"], r["good_trials"]), reverse=True)[0]
    return best["mapping"], {"scores": scores, "chosen": best}


def trial_event_table(triggers, trials, mapping, fs, stim_dur_s):
    rows, idx = [], 0
    if stim_dur_s is None:
        stim_dur_s = float(trials["expected_photodiode_pulses"].iloc[0]) * float(trials["photodiode_pulse_interval_s"].iloc[0])
    for ti, tr in trials.reset_index(drop=True).iterrows():
        n = int(tr.get("expected_photodiode_pulses", 30))
        seg = triggers.iloc[idx:idx+n].copy()
        idx += n
        types = seg["type_id"].astype(int).tolist()
        mapped = [mapping.get(t, "unknown") for t in types]
        side = str(tr.get("attend_side", "")).lower()
        first = int(seg["merged_sample"].iloc[0]) if len(seg) else np.nan
        last = int(seg["merged_sample"].iloc[-1]) if len(seg) else np.nan
        diffs = np.diff(seg["merged_sample"].to_numpy()) / fs if len(seg) > 1 else np.array([])
        rows.append({
            "trial_index_1based": ti + 1,
            "block": int(tr.get("block", np.nan)),
            "trial_in_block": int(tr.get("trial_in_block", np.nan)),
            "attend_side": side,
            "gaze_target_side": str(tr.get("gaze_target_side", side)).lower(),
            "target_freq": float(tr.get("target_freq", np.nan)),
            "expected_pulses": n,
            "n_events_assigned": len(seg),
            "unique_type_ids": ",".join(str(x) for x in sorted(set(types))),
            "unique_mapped_sides": ",".join(sorted(set(mapped))),
            "n_side_matches": sum(1 for x in mapped if x == side),
            "all_side_match": bool(len(seg) == n and all(x == side for x in mapped)),
            "first_trigger_sample": first,
            "last_trigger_sample": last,
            "stim_start_sample": first,
            "stim_end_sample": int(first + round(stim_dur_s * fs)) if not pd.isna(first) else np.nan,
            "stim_start_time_s": first / fs if not pd.isna(first) else np.nan,
            "stim_end_time_s": (first + round(stim_dur_s * fs)) / fs if not pd.isna(first) else np.nan,
            "trigger_span_first_to_last_s": (last - first) / fs if not pd.isna(first) else np.nan,
            "mean_inter_pulse_interval_s": float(np.mean(diffs)) if len(diffs) else np.nan,
            "min_inter_pulse_interval_s": float(np.min(diffs)) if len(diffs) else np.nan,
            "max_inter_pulse_interval_s": float(np.max(diffs)) if len(diffs) else np.nan,
        })
    return pd.DataFrame(rows)


def robust_std(x, axis=0):
    med = np.nanmedian(x, axis=axis)
    mad = np.nanmedian(np.abs(x - med), axis=axis)
    return 1.4826 * mad


def channel_qc(data, names, fs):
    x = data.astype(np.float64)
    xc = x - np.nanmedian(x, axis=0, keepdims=True)
    std = np.nanstd(xc, axis=0)
    rstd = robust_std(x, axis=0)
    ptp = np.nanpercentile(x, 99.5, axis=0) - np.nanpercentile(x, 0.5, axis=0)
    abs95 = np.nanpercentile(np.abs(xc), 95, axis=0)
    abs99 = np.nanpercentile(np.abs(xc), 99, axis=0)
    step = max(1, int(fs // 64))
    xs = xc[::step]
    g = np.nanmedian(xs, axis=1)
    corr = []
    for i in range(xs.shape[1]):
        if np.nanstd(xs[:, i]) < 1e-12 or np.nanstd(g) < 1e-12:
            corr.append(np.nan)
        else:
            corr.append(float(np.corrcoef(xs[:, i], g)[0, 1]))
    med_rstd = np.nanmedian(rstd[(rstd > 0) & np.isfinite(rstd)])
    rows = []
    for i, name in enumerate(names):
        flags = []
        if std[i] < 0.05:
            flags.append("flat_or_near_flat")
        if rstd[i] > 5 * med_rstd:
            flags.append("very_high_robust_std")
        if rstd[i] < 0.15 * med_rstd:
            flags.append("very_low_robust_std")
        if ptp[i] > 5000:
            flags.append("very_large_peak_to_peak")
        if abs99[i] > 1000:
            flags.append("large_99pct_amplitude")
        status = "good" if not flags else "review"
        if "flat_or_near_flat" in flags or "very_large_peak_to_peak" in flags:
            status = "bad"
        rows.append({
            "channel_index_1based": i + 1,
            "channel_name": name,
            "std_uV": std[i],
            "robust_std_uV": rstd[i],
            "robust_std_ratio_to_median": rstd[i] / med_rstd if med_rstd > 0 else np.nan,
            "ptp_0p5_99p5_uV": ptp[i],
            "abs95_uV": abs95[i],
            "abs99_uV": abs99[i],
            "corr_with_global_median": corr[i],
            "flags": ";".join(flags),
            "auto_status": status,
        })
    return pd.DataFrame(rows)


def psd_snr(data, fs, trials, names, qc, freqs_to_check, out_dir):
    occ_names = ["O1", "Oz", "O2", "POz", "PO3", "PO4", "PO7", "PO8", "Pz", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
    occ_idx = [names.index(c) for c in occ_names if c in names]
    rows = []
    acc = {"left": [], "right": []}
    nper = int(min(fs * 8, fs * 30))
    qmap = dict(zip(qc["channel_name"], qc["auto_status"]))
    for _, tr in trials.iterrows():
        s = int(tr["stim_start_sample"])
        e = int(tr["stim_end_sample"])
        if s < 0 or e > data.shape[0] or e <= s:
            continue
        seg = data[s:e, :].astype(np.float64)
        seg = signal.detrend(seg - np.mean(seg, axis=0, keepdims=True), axis=0)
        for ch in range(seg.shape[1]):
            f, p = signal.welch(seg[:, ch], fs=fs, nperseg=min(nper, seg.shape[0]), noverlap=min(nper//2, seg.shape[0]//2-1), detrend=False, scaling="density")
            for f0 in freqs_to_check:
                bi = int(np.argmin(np.abs(f - f0)))
                mask = (f >= f0 - 2) & (f <= f0 + 2) & (np.abs(f - f0) >= 0.4)
                noise = float(np.mean(p[mask])) if np.any(mask) else np.nan
                power = float(p[bi])
                snr = power / noise if noise and np.isfinite(noise) and noise > 0 else np.nan
                rows.append({
                    "trial_index_1based": int(tr["trial_index_1based"]),
                    "block": int(tr["block"]),
                    "attend_side": tr["attend_side"],
                    "target_freq": float(tr["target_freq"]),
                    "channel_index_1based": ch + 1,
                    "channel_name": names[ch],
                    "frequency_checked_hz": float(f0),
                    "nearest_psd_bin_hz": float(f[bi]),
                    "psd_power": power,
                    "neighbor_noise_power": noise,
                    "snr_linear": snr,
                    "snr_db": 10 * np.log10(snr) if np.isfinite(snr) and snr > 0 else np.nan,
                    "is_target_frequency_for_trial": abs(float(tr["target_freq"]) - f0) < 1e-9,
                    "is_occipital_channel": names[ch] in occ_names,
                    "qc_status": qmap.get(names[ch], "unknown"),
                })
        if occ_idx:
            f, p = signal.welch(seg[:, occ_idx], fs=fs, axis=0, nperseg=min(nper, seg.shape[0]), noverlap=min(nper//2, seg.shape[0]//2-1), detrend=False, scaling="density")
            acc[tr["attend_side"]].append(np.mean(p, axis=1))
    df = pd.DataFrame(rows)
    if len(df):
        summ = df.groupby(["channel_name", "frequency_checked_hz", "attend_side", "is_target_frequency_for_trial", "is_occipital_channel", "qc_status"], dropna=False).agg(mean_snr_db=("snr_db", "mean"), median_snr_db=("snr_db", "median"), n=("snr_db", "count")).reset_index()
    else:
        summ = pd.DataFrame()
    if occ_idx:
        plt.figure(figsize=(10, 6))
        for side in ["left", "right"]:
            if acc[side]:
                plt.semilogy(f, np.mean(np.vstack(acc[side]), axis=0), label=f"{side} trials")
        for f0 in freqs_to_check:
            plt.axvline(f0, linestyle="--", linewidth=1)
        plt.xlim(1, 35)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD")
        plt.title("Average occipital PSD by attended side")
        plt.legend()
        plt.tight_layout()
        plt.savefig(Path(out_dir) / "02_occipital_psd_left_vs_right.png", dpi=150)
        plt.close()
    return df, summ


def plots(triggers, qc, out_dir):
    plt.figure(figsize=(12, 4))
    plt.scatter(triggers["time_s"], triggers["type_id"], s=8)
    plt.xlabel("Merged recording time (s)")
    plt.ylabel("Trigger TypeID")
    plt.title("Trigger timeline")
    plt.tight_layout()
    plt.savefig(Path(out_dir) / "02_trigger_timeline.png", dpi=150)
    plt.close()
    plt.figure(figsize=(14, 5))
    plt.bar(qc["channel_name"], qc["robust_std_uV"])
    plt.xticks(rotation=90, fontsize=7)
    plt.ylabel("Robust STD (uV)")
    plt.title("Channel robust standard deviation")
    plt.tight_layout()
    plt.savefig(Path(out_dir) / "02_channel_qc_robust_std.png", dpi=150)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", required=True)
    ap.add_argument("--psychopy_dir", required=True)
    ap.add_argument("--trials_csv", default=None)
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--stim_dur_s", type=float, default=None)
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir) if args.out_dir else data_dir / "_analysis_report" / "step02"
    out_dir.mkdir(parents=True, exist_ok=True)

    h5s = sorted(list(data_dir.glob("*.hdf5")) + list(data_dir.glob("*.h5")))
    if not h5s:
        raise FileNotFoundError("No .hdf5/.h5 files found.")

    trials, trials_csv, meta_path, meta_stim = load_psychopy(args.psychopy_dir, args.trials_csv)
    stim_dur = args.stim_dur_s if args.stim_dur_s is not None else meta_stim
    print("Using trials:", trials_csv)
    print("Using meta:", meta_path)
    print("Stim duration:", stim_dur)

    data, triggers, infos, fs, names = load_merge(h5s)
    print("Merged data shape:", data.shape, "fs:", fs)

    pd.DataFrame([{
        "merge_order": i + 1,
        "file_name": inf["name"],
        "recording_date_begin": inf["recording_date_begin"],
        "size_mb": inf["size_mb"],
        "n_samples": inf["n_samples"],
        "duration_s": inf["duration_s"],
        "n_triggers": len(inf["trigger_typeids"]),
        "trigger_typeids": ",".join(str(x) for x in sorted(np.unique(inf["trigger_typeids"])))
    } for i, inf in enumerate(infos)]).to_csv(out_dir / "02_hdf5_file_summary.csv", index=False)
    pd.DataFrame(infos[0]["channels"]).to_csv(out_dir / "02_channel_metadata.csv", index=False)
    pd.DataFrame(infos[0]["async_descriptions"]).to_csv(out_dir / "02_async_trigger_descriptions.csv", index=False)
    triggers.to_csv(out_dir / "02_merged_triggers.csv", index=False)
    triggers.groupby(["file_name", "type_id"]).size().reset_index(name="count").to_csv(out_dir / "02_trigger_counts_by_file.csv", index=False)

    mapping, minfo = infer_mapping(triggers, trials)
    with open(out_dir / "02_trigger_mapping_info.json", "w", encoding="utf-8") as f:
        json.dump(minfo, f, indent=2, default=str)
    if mapping is None:
        mapping = {int(t): f"type_{int(t)}" for t in sorted(triggers["type_id"].unique())}
    print("Inferred mapping:", mapping)

    tev = trial_event_table(triggers, trials, mapping, fs, stim_dur)
    tev.to_csv(out_dir / "02_trial_event_match.csv", index=False)

    qc = channel_qc(data, names, fs)
    qc.to_csv(out_dir / "02_channel_quality.csv", index=False)

    freqs = sorted([float(x) for x in trials["target_freq"].dropna().unique()]) if "target_freq" in trials.columns else [9.0, 14.0]
    snr, snrs = psd_snr(data, fs, tev, names, qc, freqs, out_dir)
    snr.to_csv(out_dir / "02_ssvep_trial_channel_snr.csv", index=False)
    snrs.to_csv(out_dir / "02_ssvep_channel_summary.csv", index=False)
    plots(triggers, qc, out_dir)

    expected = int(trials["expected_photodiode_pulses"].sum()) if "expected_photodiode_pulses" in trials.columns else np.nan
    good = int((qc["auto_status"] == "good").sum())
    review = int((qc["auto_status"] == "review").sum())
    bad = int((qc["auto_status"] == "bad").sum())
    matches = int(tev["all_side_match"].sum())

    occ = snr[snr["is_occipital_channel"] & snr["qc_status"].isin(["good", "review"])] if len(snr) else pd.DataFrame()
    occ_t = occ[occ["is_target_frequency_for_trial"]] if len(occ) else pd.DataFrame()
    occ_nt = occ[~occ["is_target_frequency_for_trial"]] if len(occ) else pd.DataFrame()
    mt = float(occ_t["snr_db"].mean()) if len(occ_t) else np.nan
    mn = float(occ_nt["snr_db"].mean()) if len(occ_nt) else np.nan

    best = pd.DataFrame()
    if len(occ_t):
        best = occ_t.groupby("channel_name").agg(mean_target_snr_db=("snr_db", "mean"), n=("snr_db", "count")).reset_index().sort_values("mean_target_snr_db", ascending=False).head(10)

    with open(out_dir / "02_summary_report.txt", "w", encoding="utf-8") as f:
        f.write("STEP 02 SUMMARY REPORT\n" + "=" * 80 + "\n\n")
        f.write("Input files in merge order:\n")
        for i, inf in enumerate(infos):
            f.write(f"  {i+1}. {inf['name']} | start={inf['recording_date_begin']} | samples={inf['n_samples']} | duration={inf['duration_s']:.2f}s | triggers={len(inf['trigger_typeids'])}\n")
        f.write("\nRecording:\n")
        f.write(f"  Sampling rate: {fs} Hz\n  Merged samples: {data.shape[0]}\n  Merged duration: {data.shape[0]/fs:.2f} s\n  Channels: {data.shape[1]}\n")
        f.write("\nPsychoPy:\n")
        f.write(f"  Trials CSV: {trials_csv}\n  Number of trials: {len(trials)}\n  Expected photodiode pulses: {expected}\n")
        f.write("\nTriggers:\n")
        f.write(f"  Observed triggers: {len(triggers)}\n")
        for _, r in triggers.groupby("type_id").size().reset_index(name="count").iterrows():
            f.write(f"    TypeID {r['type_id']}: {r['count']}\n")
        f.write(f"  Inferred mapping: {mapping}\n  Trials with full side match: {matches}/{len(tev)}\n")
        f.write("\nChannel QC:\n")
        f.write(f"  Good: {good}\n  Review: {review}\n  Bad: {bad}\n")
        f.write("\nFirst SSVEP check:\n")
        f.write(f"  Frequencies checked: {freqs}\n  Mean occipital target SNR: {mt:.3f} dB\n  Mean occipital non-target SNR: {mn:.3f} dB\n")
        f.write("  Top occipital channels by target SNR:\n")
        if len(best):
            for _, r in best.iterrows():
                f.write(f"    {r['channel_name']}: {r['mean_target_snr_db']:.3f} dB (n={int(r['n'])})\n")
        else:
            f.write("    None available.\n")
        f.write("\nGenerated files:\n")
        for p in sorted(out_dir.glob("*")):
            f.write(f"  {p.name}\n")

    print("\nDone. Output folder:", out_dir)
    print("Please send back these files:")
    for name in ["02_summary_report.txt", "02_trial_event_match.csv", "02_channel_quality.csv", "02_ssvep_channel_summary.csv"]:
        print(" ", out_dir / name)
    print("Useful plots:")
    for name in ["02_trigger_timeline.png", "02_channel_qc_robust_std.png", "02_occipital_psd_left_vs_right.png"]:
        print(" ", out_dir / name)


if __name__ == "__main__":
    main()
