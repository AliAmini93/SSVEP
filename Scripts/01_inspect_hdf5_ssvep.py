import argparse
import json
import os
from pathlib import Path

import h5py
import numpy as np
import pandas as pd


def safe_decode(x):
    """Decode bytes if needed."""
    if isinstance(x, bytes):
        try:
            return x.decode("utf-8")
        except Exception:
            return str(x)
    return x


def summarize_numeric_sample(arr):
    """Return lightweight summary from a sampled numeric array."""
    out = {}

    try:
        arr = np.asarray(arr)
        arr = arr[np.isfinite(arr)] if np.issubdtype(arr.dtype, np.number) else arr

        if arr.size == 0:
            return {"empty_or_nonfinite": True}

        out["sample_min"] = float(np.min(arr))
        out["sample_max"] = float(np.max(arr))
        out["sample_mean"] = float(np.mean(arr))
        out["sample_std"] = float(np.std(arr))

        unique_vals = np.unique(arr[: min(arr.size, 5000)])
        out["sample_unique_count_limited"] = int(len(unique_vals))

        if len(unique_vals) <= 20:
            out["sample_unique_values"] = [
                safe_decode(v.item() if hasattr(v, "item") else v) for v in unique_vals
            ]

    except Exception as exc:
        out["summary_error"] = str(exc)

    return out


def sample_dataset(ds, max_points=5000):
    """Take a small sample from a dataset without loading the whole file."""
    try:
        shape = ds.shape

        if shape == ():
            return np.asarray(ds[()])

        if len(shape) == 1:
            n = min(shape[0], max_points)
            return ds[:n]

        if len(shape) == 2:
            n0 = min(shape[0], max_points)
            n1 = min(shape[1], 16)
            return ds[:n0, :n1]

        slices = tuple(slice(0, min(dim, 4)) for dim in shape)
        return ds[slices]

    except Exception as exc:
        return f"Could not sample dataset: {exc}"


def classify_dataset(path, ds):
    """Heuristic labels for possible EEG, trigger, time, channel-name datasets."""
    labels = []

    shape = ds.shape
    dtype_str = str(ds.dtype)
    path_low = path.lower()

    if any(k in path_low for k in ["trigger", "trig", "event", "marker", "stim", "digital", "photodiode"]):
        labels.append("name_suggests_trigger_or_events")

    if any(k in path_low for k in ["eeg", "signal", "data", "raw", "samples", "channel"]):
        labels.append("name_suggests_signal_data")

    if any(k in path_low for k in ["time", "timestamp"]):
        labels.append("name_suggests_time")

    if any(k in path_low for k in ["chan", "label", "name"]):
        labels.append("name_suggests_channel_names")

    if len(shape) == 2:
        big_dim = max(shape)
        small_dim = min(shape)

        if big_dim > 1000 and 1 <= small_dim <= 512:
            labels.append("shape_suggests_continuous_multichannel_data")

        if big_dim > 1000 and small_dim <= 8:
            labels.append("shape_suggests_possible_trigger_or_aux_channels")

    if len(shape) == 1 and shape[0] > 1000:
        labels.append("shape_suggests_continuous_single_channel_or_time")

    if "S" in dtype_str or "U" in dtype_str or "object" in dtype_str:
        labels.append("dtype_suggests_text_or_labels")

    if np.issubdtype(ds.dtype, np.integer):
        labels.append("dtype_suggests_integer_possible_events")

    return labels


def inspect_hdf5_file(h5_path):
    info = {
        "file": str(h5_path),
        "file_size_mb": round(os.path.getsize(h5_path) / (1024 * 1024), 3),
        "attrs": {},
        "datasets": [],
        "groups": [],
        "possible_sampling_rate_locations": [],
    }

    with h5py.File(h5_path, "r") as f:
        for k, v in f.attrs.items():
            info["attrs"][str(k)] = safe_decode(v)

            k_low = str(k).lower()
            if any(term in k_low for term in ["fs", "sample", "sampling", "rate", "hz"]):
                info["possible_sampling_rate_locations"].append({
                    "location": "/",
                    "attribute": str(k),
                    "value": safe_decode(v),
                })

        def visitor(name, obj):
            full_path = "/" + name

            if isinstance(obj, h5py.Group):
                group_info = {
                    "path": full_path,
                    "attrs": {},
                }

                for k, v in obj.attrs.items():
                    group_info["attrs"][str(k)] = safe_decode(v)

                    k_low = str(k).lower()
                    if any(term in k_low for term in ["fs", "sample", "sampling", "rate", "hz"]):
                        info["possible_sampling_rate_locations"].append({
                            "location": full_path,
                            "attribute": str(k),
                            "value": safe_decode(v),
                        })

                info["groups"].append(group_info)

            elif isinstance(obj, h5py.Dataset):
                ds_info = {
                    "path": full_path,
                    "shape": obj.shape,
                    "dtype": str(obj.dtype),
                    "attrs": {},
                    "labels": classify_dataset(full_path, obj),
                }

                for k, v in obj.attrs.items():
                    ds_info["attrs"][str(k)] = safe_decode(v)

                    k_low = str(k).lower()
                    if any(term in k_low for term in ["fs", "sample", "sampling", "rate", "hz"]):
                        info["possible_sampling_rate_locations"].append({
                            "location": full_path,
                            "attribute": str(k),
                            "value": safe_decode(v),
                        })

                sample = sample_dataset(obj)

                if isinstance(sample, str):
                    ds_info["sample_error"] = sample
                elif np.issubdtype(obj.dtype, np.number):
                    ds_info["numeric_sample_summary"] = summarize_numeric_sample(sample)
                else:
                    try:
                        flat = np.asarray(sample).ravel()[:20]
                        ds_info["sample_values_first_20"] = [safe_decode(x) for x in flat.tolist()]
                    except Exception as exc:
                        ds_info["sample_error"] = str(exc)

                info["datasets"].append(ds_info)

        f.visititems(visitor)

    return info


def find_psychopy_files(psychopy_dir):
    p = Path(psychopy_dir)
    if not p.exists():
        return {}

    files = {
        "trials": sorted(p.glob("*_trials.csv")),
        "meta": sorted(p.glob("*_meta.txt")),
        "timing": sorted(p.glob("*_timingSummary.txt")),
        "frame_intervals": sorted(p.glob("*_frameIntervals_ms.txt")),
    }
    return files


def summarize_psychopy_trials(trial_file):
    df = pd.read_csv(trial_file)

    summary = {
        "file": str(trial_file),
        "n_rows": int(len(df)),
        "columns": list(df.columns),
    }

    if len(df) > 0:
        if "block" in df.columns:
            summary["blocks"] = sorted(df["block"].dropna().unique().tolist())

        if "trial_in_block" in df.columns and "block" in df.columns:
            summary["trials_per_block"] = (
                df.groupby("block")["trial_in_block"]
                .count()
                .to_dict()
            )

        if "attend_side" in df.columns:
            summary["attend_side_counts"] = df["attend_side"].value_counts(dropna=False).to_dict()

        if "gaze_target_side" in df.columns:
            summary["gaze_target_side_counts"] = df["gaze_target_side"].value_counts(dropna=False).to_dict()

        if "target_freq" in df.columns:
            summary["target_freq_counts"] = df["target_freq"].value_counts(dropna=False).to_dict()

        if "expected_photodiode_pulses" in df.columns:
            summary["expected_total_photodiode_pulses"] = int(df["expected_photodiode_pulses"].sum())
            summary["expected_pulses_per_trial_unique"] = sorted(
                df["expected_photodiode_pulses"].dropna().unique().tolist()
            )

        if "dropped_frames_trial" in df.columns:
            summary["dropped_frames_total_from_trials_csv"] = int(df["dropped_frames_trial"].sum())
            summary["trials_with_dropped_frames_from_trials_csv"] = int((df["dropped_frames_trial"] > 0).sum())

    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", required=True, help="Folder containing HDF5 EEG files.")
    parser.add_argument(
        "--psychopy_dir",
        default=None,
        help="Folder containing PsychoPy CSV/TXT files. If omitted, the script searches data_dir and parent/data.",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Output folder. Default: data_dir/_analysis_report",
    )

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data folder does not exist: {data_dir}")

    out_dir = Path(args.out_dir) if args.out_dir else data_dir / "_analysis_report"
    out_dir.mkdir(parents=True, exist_ok=True)

    h5_files = sorted(list(data_dir.glob("*.hdf5")) + list(data_dir.glob("*.h5")))

    if not h5_files:
        raise FileNotFoundError(f"No .hdf5 or .h5 files found in: {data_dir}")

    all_h5_info = []
    for h5_path in h5_files:
        print(f"Inspecting: {h5_path.name}")
        info = inspect_hdf5_file(h5_path)
        all_h5_info.append(info)

    json_path = out_dir / "01_hdf5_inventory.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_h5_info, f, indent=2, ensure_ascii=False, default=str)

    txt_path = out_dir / "01_hdf5_inventory_readable.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        for file_info in all_h5_info:
            f.write("=" * 100 + "\n")
            f.write(f"FILE: {file_info['file']}\n")
            f.write(f"SIZE MB: {file_info['file_size_mb']}\n")
            f.write("\nRoot attrs:\n")
            for k, v in file_info["attrs"].items():
                f.write(f"  {k}: {v}\n")

            f.write("\nPossible sampling rate locations:\n")
            if file_info["possible_sampling_rate_locations"]:
                for sr in file_info["possible_sampling_rate_locations"]:
                    f.write(f"  {sr}\n")
            else:
                f.write("  None found by attribute-name heuristic.\n")

            f.write("\nDatasets:\n")
            for ds in file_info["datasets"]:
                f.write("-" * 80 + "\n")
                f.write(f"Path: {ds['path']}\n")
                f.write(f"Shape: {ds['shape']}\n")
                f.write(f"Dtype: {ds['dtype']}\n")
                f.write(f"Labels: {', '.join(ds['labels']) if ds['labels'] else 'none'}\n")

                if ds.get("attrs"):
                    f.write("Attrs:\n")
                    for k, v in ds["attrs"].items():
                        f.write(f"  {k}: {v}\n")

                if "numeric_sample_summary" in ds:
                    f.write(f"Numeric sample summary: {ds['numeric_sample_summary']}\n")

                if "sample_values_first_20" in ds:
                    f.write(f"First sample values: {ds['sample_values_first_20']}\n")

                if "sample_error" in ds:
                    f.write(f"Sample error: {ds['sample_error']}\n")

            f.write("\n\n")

    psychopy_dirs_to_try = []

    if args.psychopy_dir:
        psychopy_dirs_to_try.append(Path(args.psychopy_dir))

    psychopy_dirs_to_try.append(data_dir)
    psychopy_dirs_to_try.append(data_dir.parent / "data")
    psychopy_dirs_to_try.append(Path.cwd() / "data")

    psychopy_summary = {
        "searched_dirs": [str(p) for p in psychopy_dirs_to_try],
        "found_files": {},
        "trial_summaries": [],
    }

    seen_trial_files = set()

    for pdir in psychopy_dirs_to_try:
        if not pdir.exists():
            continue

        found = find_psychopy_files(pdir)
        for key, paths in found.items():
            psychopy_summary["found_files"].setdefault(key, [])
            psychopy_summary["found_files"][key].extend([str(x) for x in paths])

        for trial_file in found.get("trials", []):
            if str(trial_file) in seen_trial_files:
                continue
            seen_trial_files.add(str(trial_file))

            try:
                psychopy_summary["trial_summaries"].append(summarize_psychopy_trials(trial_file))
            except Exception as exc:
                psychopy_summary["trial_summaries"].append({
                    "file": str(trial_file),
                    "error": str(exc),
                })

    psychopy_json_path = out_dir / "01_psychopy_inventory.json"
    with open(psychopy_json_path, "w", encoding="utf-8") as f:
        json.dump(psychopy_summary, f, indent=2, ensure_ascii=False, default=str)

    psychopy_txt_path = out_dir / "01_psychopy_inventory_readable.txt"
    with open(psychopy_txt_path, "w", encoding="utf-8") as f:
        f.write("Searched PsychoPy directories:\n")
        for p in psychopy_summary["searched_dirs"]:
            f.write(f"  {p}\n")

        f.write("\nFound files:\n")
        for key, paths in psychopy_summary["found_files"].items():
            f.write(f"\n{key}:\n")
            for path in paths:
                f.write(f"  {path}\n")

        f.write("\nTrial summaries:\n")
        for s in psychopy_summary["trial_summaries"]:
            f.write("-" * 80 + "\n")
            for k, v in s.items():
                f.write(f"{k}: {v}\n")

    print("\nDone.")
    print(f"HDF5 inventory JSON: {json_path}")
    print(f"HDF5 readable report: {txt_path}")
    print(f"PsychoPy inventory JSON: {psychopy_json_path}")
    print(f"PsychoPy readable report: {psychopy_txt_path}")


if __name__ == "__main__":
    main()
