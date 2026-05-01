# Reproducibility Guide — SSVEP Overt/Covert EEG Pilot

**Project:** First SSVEP EEG Recording — Overt / Direct-Gaze Pilot  
**Updated after folder reorganization:** 2026-05-01  
**Root folder:**

```text
F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt
```

This guide explains how to reproduce the full SSVEP experiment and analysis for future subjects using the current organized folder structure.

---

## 1. Current folder structure

```text
First SSVEP EEG Recording- Overt/
│
├── reorganize_ssvep_project.py
├── run_analysis_all.bat
│
├── EEG Recorded data/
│   ├── Subject12026.04.30_13.59.13.hdf5
│   └── Subject1-12026.04.30_14.20.19.hdf5
│
├── data/
│   ├── *_trials.csv
│   ├── *_meta.txt
│   ├── *_timingSummary.txt
│   └── *_frameIntervals_ms.txt
│
├── Scripts/
│   ├── psychopy_ssvep_pilot.py
│   ├── psychopy_ssvep_pilot_V2.py
│   ├── psychopy_ssvep_pilot_V3.py
│   ├── psychopy_ssvep_pilot_V4.py
│   ├── 01_inspect_hdf5_ssvep.py
│   ├── 02_merge_qc_triggers_ssvep.py
│   ├── 03_detailed_ssvep_analysis.py
│   ├── 04_harmonic_cca_ssvep_analysis.py
│   └── 05_permutation_sanity_check.py
│
├── trigger_images/
│   ├── ScreenTrigOn.png
│   └── ScreenTrigOff.png
│
├── figures/
│   ├── Impedance.PNG
│   └── Impedance_After.PNG
│
└── _analysis_report/
```

### Folder roles

| Folder | Role |
|---|---|
| `EEG Recorded data/` | Raw `.hdf5` EEG files |
| `data/` | PsychoPy trial, meta, timing, and frame interval files |
| `Scripts/` | PsychoPy and analysis Python scripts |
| `trigger_images/` | Photodiode trigger images |
| `figures/` | Impedance screenshots and manual figures |
| `_analysis_report/` | Automatically generated analysis outputs |

---

## 2. Path behavior after reorganization

The PsychoPy scripts were patched so that they work from the new structure:

```python
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)

save_dir = os.path.join(project_dir, "data")
trigger_on_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOn.png")
trigger_off_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOff.png")
```

Therefore:

- the active PsychoPy script can stay in `Scripts/`,
- trigger images stay in `trigger_images/`,
- PsychoPy outputs are saved to `data/`,
- analysis scripts are run from the project root.

---

## 3. Software environments

### Run PsychoPy

```bat
conda activate psychopy
cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"
python Scripts\psychopy_ssvep_pilot_V4.py
```

### Run analysis

```bat
conda activate base
cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"
run_analysis_all.bat
```

Required Python packages for analysis:

```text
numpy
pandas
scipy
matplotlib
h5py
```

Optional:

```text
mne
scikit-learn
```

---

## 4. Hardware checklist before recording

- [ ] g.USBamp amplifiers connected.
- [ ] g.TRIGbox connected.
- [ ] Photodiode/optical sensor connected.
- [ ] External monitor connected by HDMI.
- [ ] Correct display mode selected.
- [ ] Photodiode aligned with trigger images.
- [ ] EEG acquisition software detects triggers.
- [ ] EEG cap prepared.
- [ ] Impedance checked, especially posterior channels.
- [ ] Background programs closed.
- [ ] Laptop plugged in and performance mode enabled.

Important posterior channels:

```text
O1, Oz, O2, PO7, PO3, POz, PO4, PO8
```

---

## 5. Display and PsychoPy checklist

Before the real run:

- [ ] Confirm `SCREEN_INDEX`.
- [ ] Prefer second-screen-only mode if using external monitor.
- [ ] Confirm full-screen mode.
- [ ] Confirm no taskbar or desktop overlay is visible during the paradigm.
- [ ] Run a short timing test.
- [ ] Inspect `*_timingSummary.txt`.

Current validated setting used:

```python
SCREEN_INDEX = 1
```

If PsychoPy opens on the wrong monitor, try:

```python
SCREEN_INDEX = 0
```

or:

```python
SCREEN_INDEX = 1
```

---

## 6. Photodiode trigger setup

The files must exist:

```text
trigger_images/ScreenTrigOn.png
trigger_images/ScreenTrigOff.png
```

Current trigger settings:

```python
LEFT_PHOTODIODE_POS = (-0.7, -0.4)
RIGHT_PHOTODIODE_POS = (0.7, -0.4)
PHOTODIODE_SIZE = 0.05
PHOTODIODE_ON_FRAMES = 2
PHOTODIODE_PULSE_INTERVAL_S = 1.0
```

Trigger meaning:

| Trial condition | Active trigger |
|---|---|
| Left / 9 Hz | Left photodiode |
| Right / 14 Hz | Right photodiode |

Observed mapping in the first recording:

| TypeID | Meaning |
|---:|---|
| 15 | Left |
| 16 | Right |

For every new recording, confirm the mapping in Step 02.

---

## 7. Experiment parameters

Current validated overt/direct-gaze parameters:

| Parameter | Value |
|---|---:|
| Left frequency | 9 Hz |
| Right frequency | 14 Hz |
| Blocks | 4 |
| Trials per block | 10 |
| Total trials | 40 |
| Left trials | 20 |
| Right trials | 20 |
| Nominal refresh | 60 Hz |
| EEG sampling rate | 512 Hz |
| Analyzed stimulation duration | 30 s |
| Trigger pulse interval | 1 s |
| Trigger ON duration | 2 frames |

Always confirm `STIM_DUR` in the PsychoPy script and in the generated `*_meta.txt`.

---

## 8. Participant instructions

### Overt / direct-gaze version

```text
Please look at the center cross between trials.
At the beginning of each trial, one square will be cued.
During the flickering period, look directly at the cued square.
Try to keep your head still and avoid blinking during flicker.
After the flicker ends, return your gaze to the center cross.
```

### Covert attention version

```text
Please keep your eyes on the center cross at all times.
At the beginning of each trial, one square will be cued.
During the flickering period, attend to the cued square without moving your eyes to it.
Try to keep your head still and avoid blinking during flicker.
```

---

## 9. Running the experiment

```bat
conda activate psychopy
cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"
python Scripts\psychopy_ssvep_pilot_V4.py
```

After running, check that new files appeared in:

```text
data/
```

Expected files:

```text
*_trials.csv
*_meta.txt
*_timingSummary.txt
*_frameIntervals_ms.txt
```

---

## 10. EEG files

Place all raw HDF5 files for the subject/session in:

```text
EEG Recorded data/
```

If recording is interrupted and restarted, keep all split HDF5 files in this same folder. The analysis pipeline sorts and merges them by recording time.

---

## 11. Running the full analysis

From the root folder:

```bat
conda activate base
cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"
run_analysis_all.bat
```

`run_analysis_all.bat` executes:

```bat
python Scripts\01_inspect_hdf5_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
python Scripts\02_merge_qc_triggers_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
python Scripts\03_detailed_ssvep_analysis.py --data_dir "EEG Recorded data"
python Scripts\04_harmonic_cca_ssvep_analysis.py --data_dir "EEG Recorded data"
python Scripts\05_permutation_sanity_check.py --data_dir "EEG Recorded data"
```

---

## 12. Analysis outputs to inspect

### Step 01

```text
_analysis_report/01_hdf5_inventory_readable.txt
_analysis_report/01_psychopy_inventory_readable.txt
```

Check file structure, channel count, sampling rate, triggers, and PsychoPy logs.

### Step 02

```text
_analysis_report/step02/02_summary_report.txt
_analysis_report/step02/02_trial_event_match.csv
_analysis_report/step02/02_trigger_timeline.png
_analysis_report/step02/02_channel_quality.csv
_analysis_report/step02/02_channel_qc_robust_std.png
```

Check merged data, trigger detection, mapping, trial matching, and bad channels.

### Step 03

```text
_analysis_report/step03/03_summary_report.txt
_analysis_report/step03/03_condition_target_vs_nontarget_snr.png
_analysis_report/step03/03_selected_posterior_psd_by_condition.png
_analysis_report/step03/03_best_channels.csv
```

Check posterior SSVEP evidence and target vs non-target frequency strength.

### Step 04

```text
_analysis_report/step04/04_summary_report.txt
_analysis_report/step04/04_trial_level_cca.csv
_analysis_report/step04/04_cca_9_vs_14_scatter.png
_analysis_report/step04/04_cca_accuracy_by_condition.png
_analysis_report/step04/04_cca_trial_margin.png
```

Check CCA classification accuracy and trial-level margins.

### Step 05

```text
_analysis_report/step05/05_summary_report.txt
_analysis_report/step05/05_target_vs_nontarget_scatter.png
_analysis_report/step05/05_permutation_accuracy_hist.png
_analysis_report/step05/05_signed_margin_hist.png
```

Check permutation and sanity controls.

---

## 13. Current validated result

The first single-subject overt/direct-gaze recording showed:

```text
Trials analyzed: 40
Observed correct trials: 40/40
Observed accuracy: 100.00%

Mean target rho: 0.343332
Mean non-target rho: 0.127495
Mean signed target margin: 0.215837
Minimum signed target margin: 0.022109

Monte-Carlo shuffled-label p-value: 0.00009999
Exact label-shuffle p-value: 7.25444455192e-12
Monte-Carlo sign-flip p-value: 0.00009999
```

This validates the pilot setup, but should not be overgeneralized beyond a single subject.

---

## 14. New subject checklist

Before recording:

- [ ] Subject/session ID assigned.
- [ ] Active PsychoPy script selected.
- [ ] Trigger images available.
- [ ] Display mode checked.
- [ ] `SCREEN_INDEX` checked.
- [ ] Photodiodes aligned.
- [ ] g.TRIGbox receives triggers.
- [ ] EEG triggers appear in acquisition software.
- [ ] Impedance checked.
- [ ] Background apps closed.
- [ ] Timing test completed.

After recording:

- [ ] HDF5 files placed in `EEG Recorded data/`.
- [ ] PsychoPy files saved in `data/`.
- [ ] `run_analysis_all.bat` completed.
- [ ] All summary reports reviewed.
- [ ] Key plots inspected.
- [ ] Subject notes written.

---

## 15. Subject/session log template

```text
Subject ID:
Session ID:
Date:
Experiment version:
Overt or covert:
PsychoPy script:
Project folder:

EEG HDF5 files:
PsychoPy trial file:
PsychoPy meta file:

Monitor:
SCREEN_INDEX:
Display mode:
Nominal refresh rate:
Measured refresh rate:

Left frequency:
Right frequency:
Stim duration:
Blocks:
Trials per block:
Total trials:

Photodiode left position:
Photodiode right position:
Photodiode size:
Trigger pulse interval:
Trigger ON frames:

EEG system:
Sampling rate:
Number of channels:
Impedance quality:
Bad channels noticed:

Recording interruptions:
Dropped-frame concerns:
Participant notes:
Experimenter notes:

Step 01 completed:
Step 02 completed:
Step 03 completed:
Step 04 completed:
Step 05 completed:

Final quick conclusion:
```

---

## 16. Troubleshooting

### PsychoPy cannot find trigger images

Check:

```text
trigger_images/ScreenTrigOn.png
trigger_images/ScreenTrigOff.png
```

and confirm the script uses `project_dir` paths.

### PsychoPy opens on wrong monitor

Change:

```python
SCREEN_INDEX = 0
```

or:

```python
SCREEN_INDEX = 1
```

### Many dropped frames

Try:

- second-screen-only mode,
- close background apps,
- disable notifications,
- plug in laptop,
- use performance mode,
- avoid screen recording,
- test both monitor options.

### Trigger IDs are not 15 and 16

Use:

```text
_analysis_report/step02/02_trigger_timeline.png
_analysis_report/step02/02_trial_event_match.csv
_analysis_report/step02/02_trigger_mapping_info.json
```

to infer the correct mapping.

### Low CCA accuracy

Check:

1. participant followed instructions,
2. correct PsychoPy trial file selected,
3. triggers detected,
4. trigger mapping correct,
5. posterior channels usable,
6. `STIM_DUR` correct,
7. dropped frames acceptable,
8. impedance not too poor.

---

## 17. Minimal success criteria

A successful overt/direct-gaze recording should show:

- triggers detected and mapped,
- matched trial count close to expected,
- usable posterior channels,
- visible PSD/SNR evidence at 9 Hz and/or 14 Hz,
- CCA accuracy above chance,
- positive target vs non-target margin,
- permutation result above shuffled-label expectation.

For a balanced two-class task:

```text
Chance level ≈ 50%
```

A very strong result is:

```text
> 90% CCA accuracy
```

The current first pilot reached:

```text
100% CCA accuracy
```

---

## 18. Version-control recommendations

Suggested commit messages:

```text
Organize SSVEP pilot project structure
Patch PsychoPy scripts for trigger_images and data folders
Add full analysis batch runner
Add HDF5 inspection and trigger matching pipeline
Add SSVEP PSD/SNR analysis
Add harmonic CCA analysis
Add permutation sanity checks
Update workflow and reproducibility documentation
```

Do not commit raw EEG data to a public repository unless consent, anonymization, and institutional approval allow it.

---

## 19. Reproducibility principle

For every subject, preserve:

1. Raw HDF5 EEG files.
2. PsychoPy `*_trials.csv`.
3. PsychoPy `*_meta.txt`.
4. PsychoPy `*_timingSummary.txt`.
5. PsychoPy `*_frameIntervals_ms.txt`.
6. Analysis scripts.
7. `_analysis_report/`.
8. Impedance screenshots.
9. Experimenter notes.
10. Display mode and trigger alignment notes.
