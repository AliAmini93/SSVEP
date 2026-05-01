# SSVEP Pilot Workflow: Overt/Covert Paradigm, EEG Recording, and Analysis

**Project:** First SSVEP EEG Recording — Overt / Direct-Gaze Pilot  
**Updated after project reorganization:** 2026-05-01  
**Current local root folder:**

```text
F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt
```

This workflow documents the full process from paradigm design to EEG recording, trigger validation, SSVEP analysis, CCA classification, permutation controls, and the final reproducible folder structure.

---

## 1. Purpose of the pilot

The broader PhD project is focused on EEG/EMG-based emotion recognition and prediction in VR serious games. Before moving toward VR, EMG, emotional stimuli, or deep learning, this SSVEP pilot was designed as a technical validation step.

The main question was:

> Can the current PsychoPy + photodiode + g.USBamp setup produce measurable and condition-specific SSVEP responses?

The pilot validates:

1. PsychoPy frame-based visual flicker.
2. Screen-based photodiode triggers.
3. EEG recording with g.tec hardware.
4. Trigger recovery from HDF5 files.
5. Trial matching between PsychoPy and EEG.
6. Frequency-specific SSVEP detection.
7. CCA-based left/right frequency classification.

---

## 2. Paradigm decision: overt first, covert later

Two paradigms were considered.

### Covert attention

The participant keeps gaze fixed on the center cross and attends to a cued peripheral flickering square without looking at it. This is scientifically interesting but harder, because covert SSVEP responses can be weaker.

### Overt / direct gaze

The participant directly looks at the cued flickering square during stimulation. This produces stronger SSVEP and is the correct first technical validation step.

The current completed recording is the **overt/direct-gaze** version. It validates the pipeline but does **not** yet prove covert attention decoding.

---

## 3. Current project structure

The project has been reorganized into the following structure:

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
    ├── 01_hdf5_inventory.json
    ├── 01_hdf5_inventory_readable.txt
    ├── 01_psychopy_inventory.json
    ├── 01_psychopy_inventory_readable.txt
    ├── step02/
    ├── step03/
    ├── step04/
    └── step05/
```

The reorganization script moved files into this structure and patched PsychoPy scripts so that:

- trigger images are read from `trigger_images/`,
- PsychoPy output files are saved into `data/`,
- analysis scripts live in `Scripts/`,
- `run_analysis_all.bat` can run the full analysis from the project root.

---

## 4. Hardware and trigger setup

The setup used:

- g.tec g.USBamp amplifiers,
- g.tec g.TRIGbox,
- optical photodiode sensor,
- external Samsung monitor via HDMI,
- PsychoPy for stimulus presentation.

No serial or parallel trigger was used. The final trigger method was photodiode-based:

```text
PsychoPy draws trigger image on screen
        ↓
Photodiode detects screen brightness change
        ↓
g.TRIGbox converts optical input to trigger
        ↓
Trigger is stored in the EEG HDF5 file
```

This is preferable because the trigger corresponds to the actual visual event on the monitor.

---

## 5. PsychoPy experiment design

### Visual stimuli

The final overt/direct-gaze version used two flickering squares:

| Target side | Flicker frequency | Interpretation |
|---|---:|---|
| Left | 9 Hz | Left target condition |
| Right | 14 Hz | Right target condition |

The two squares were placed far apart to make direct gaze easy and reduce visual overlap.

### Participant instruction

During each trial:

1. Look at the center fixation cross.
2. Watch the cue.
3. If the left square is cued, look directly at the left flickering square.
4. If the right square is cued, look directly at the right flickering square.
5. Keep head still and avoid blinking during flicker.
6. Between trials, return gaze to the center cross.

### Trial sequence

| Stage | Display | Participant behavior |
|---|---|---|
| Fixation | Center cross | Look at center |
| Cue | One square highlighted | Identify target side |
| Stimulation | Both squares flicker | Look directly at cued square |
| ITI | Rest/fixation | Return gaze to center |

### Current validated parameters

| Parameter | Value |
|---|---:|
| Blocks | 4 |
| Trials per block | 10 |
| Total trials | 40 |
| Left trials | 20 |
| Right trials | 20 |
| Left frequency | 9 Hz |
| Right frequency | 14 Hz |
| EEG sampling rate | 512 Hz |
| EEG channels | 64 |
| Stimulation duration in analyzed data | 30 s |
| Trigger pulse interval | 1 s |
| Trigger ON duration | 2 frames |
| Trigger method | Two photodiode trigger images |

Earlier design iterations discussed shorter stimulation durations, but the analyzed PsychoPy/EEG data used **30.0 seconds** per trial.

---

## 6. Photodiode trigger design

The final version uses two trigger image locations:

```python
LEFT_PHOTODIODE_POS = (-0.7, -0.4)
RIGHT_PHOTODIODE_POS = (0.7, -0.4)
PHOTODIODE_SIZE = 0.05
PHOTODIODE_ON_FRAMES = 2
PHOTODIODE_PULSE_INTERVAL_S = 1.0
```

The trigger images are:

```text
trigger_images/ScreenTrigOn.png
trigger_images/ScreenTrigOff.png
```

Only the trigger corresponding to the current target side is activated. A pulse happens at stimulation onset and then once every second until the end of the stimulation period.

The EEG trigger TypeID mapping inferred from the data was:

| EEG Trigger TypeID | Interpreted condition |
|---:|---|
| 15 | Left / 9 Hz |
| 16 | Right / 14 Hz |

---

## 7. Recorded data

The EEG recording was split into two HDF5 files:

```text
EEG Recorded data/
├── Subject12026.04.30_13.59.13.hdf5
└── Subject1-12026.04.30_14.20.19.hdf5
```

Both files belong to the same subject/session and were merged during analysis.

The relevant PsychoPy run was:

```text
data/005_005_2026-04-30_13h59.55.909_simple_ssvep_direct_gaze_pilot_*
```

The `data/` folder contains:

| File type | Purpose |
|---|---|
| `*_trials.csv` | Trial-wise design and timing log |
| `*_meta.txt` | Experiment settings and metadata |
| `*_timingSummary.txt` | Display timing summary |
| `*_frameIntervals_ms.txt` | Frame intervals during stimulation |

---

## 8. Full analysis pipeline

All scripts are in `Scripts/`. Outputs are written to `_analysis_report/`.

To run everything:

```bat
cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"
conda activate base
run_analysis_all.bat
```

Manual equivalent:

```bat
python Scripts\01_inspect_hdf5_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
python Scripts\02_merge_qc_triggers_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
python Scripts\03_detailed_ssvep_analysis.py --data_dir "EEG Recorded data"
python Scripts\04_harmonic_cca_ssvep_analysis.py --data_dir "EEG Recorded data"
python Scripts\05_permutation_sanity_check.py --data_dir "EEG Recorded data"
```

---

## 9. Step 01 — HDF5 and PsychoPy inspection

Purpose:

- inspect HDF5 structure,
- list channel names,
- detect available trigger arrays,
- inspect PsychoPy logs,
- identify the likely matching PsychoPy run.

Command:

```bat
python Scripts\01_inspect_hdf5_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
```

Outputs:

```text
_analysis_report/01_hdf5_inventory.json
_analysis_report/01_hdf5_inventory_readable.txt
_analysis_report/01_psychopy_inventory.json
_analysis_report/01_psychopy_inventory_readable.txt
```

---

## 10. Step 02 — Merge EEG, detect triggers, and QC channels

Purpose:

1. Load both HDF5 files.
2. Sort by recording time.
3. Merge into one continuous dataset.
4. Detect EEG triggers.
5. Infer left/right trigger mapping.
6. Match EEG triggers to PsychoPy trials.
7. Perform channel QC.
8. Generate preliminary PSD plots.

Command:

```bat
python Scripts\02_merge_qc_triggers_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"
```

Observed key output:

```text
Merged data shape: (795660, 64)
Sampling rate: 512 Hz
Inferred mapping: {15: 'left', 16: 'right'}
```

Important outputs:

```text
_analysis_report/step02/02_summary_report.txt
_analysis_report/step02/02_trial_event_match.csv
_analysis_report/step02/02_channel_quality.csv
_analysis_report/step02/02_trigger_timeline.png
_analysis_report/step02/02_channel_qc_robust_std.png
_analysis_report/step02/02_occipital_psd_left_vs_right.png
```

---

## 11. Step 03 — Detailed PSD/SNR analysis

Purpose:

- estimate spectral SSVEP evidence,
- compare target vs non-target frequency,
- inspect posterior channels.

Posterior channels used:

```text
O1, Oz, O2, PO7, PO3, POz, PO4, PO8, P5, P2, P4, P6, P8
```

Command:

```bat
python Scripts\03_detailed_ssvep_analysis.py --data_dir "EEG Recorded data"
```

Important outputs:

```text
_analysis_report/step03/03_summary_report.txt
_analysis_report/step03/03_condition_summary.csv
_analysis_report/step03/03_best_channels.csv
_analysis_report/step03/03_trial_level_ssvep.csv
_analysis_report/step03/03_condition_target_vs_nontarget_snr.png
_analysis_report/step03/03_selected_posterior_psd_by_condition.png
```

Step 03 showed frequency-specific posterior SSVEP evidence, but CCA was needed for stronger trial-level classification.

---

## 12. Step 04 — Harmonic-aware CCA analysis

Purpose:

- classify each trial as 9 Hz or 14 Hz,
- use harmonic reference signals.

Harmonic references:

| Target | Harmonics |
|---|---|
| 9 Hz | 9, 18, 27 Hz |
| 14 Hz | 14, 28, 42 Hz |

Command:

```bat
python Scripts\04_harmonic_cca_ssvep_analysis.py --data_dir "EEG Recorded data"
```

Important outputs:

```text
_analysis_report/step04/04_summary_report.txt
_analysis_report/step04/04_trial_level_cca.csv
_analysis_report/step04/04_condition_cca_summary.csv
_analysis_report/step04/04_cca_9_vs_14_scatter.png
_analysis_report/step04/04_cca_accuracy_by_condition.png
_analysis_report/step04/04_cca_trial_margin.png
```

Main result:

```text
40/40 trials correctly classified
100% CCA accuracy
```

This is strong evidence that the overt/direct-gaze recording contains condition-specific SSVEP responses.

---

## 13. Step 05 — Permutation and sanity-check controls

Purpose:

- test whether the CCA result is non-random,
- compare target vs non-target CCA rho,
- evaluate shuffled-label and sign-flip controls.

Command:

```bat
python Scripts\05_permutation_sanity_check.py --data_dir "EEG Recorded data"
```

Important outputs:

```text
_analysis_report/step05/05_summary_report.txt
_analysis_report/step05/05_trial_sanity_check.csv
_analysis_report/step05/05_condition_sanity_summary.csv
_analysis_report/step05/05_permutation_accuracy_hist.png
_analysis_report/step05/05_signed_margin_hist.png
_analysis_report/step05/05_target_vs_nontarget_scatter.png
```

Main results:

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

The controls support that the CCA result is not a trivial label/order artifact.

---

## 14. Quality-control notes

### Impedance

Impedance screenshots are now stored in:

```text
figures/Impedance.PNG
figures/Impedance_After.PNG
```

Many channels had high impedance, but posterior channels still produced a strong SSVEP response. Future sessions should prioritize lowering impedance over occipital and parieto-occipital channels.

### Split recording

The recording was split into two files. This was handled successfully by the analysis pipeline. For future sessions, all HDF5 files belonging to one subject/session should stay together in `EEG Recorded data/`.

### Dropped frames

Dropped frames were more likely with the external HDMI monitor. Future sessions should close background programs, use performance mode, disable notifications, and check timing summaries before recording.

---

## 15. Current conclusion

The first single-subject overt/direct-gaze SSVEP pilot successfully validated the EEG pipeline.

Key conclusion:

> In this single-subject overt/direct-gaze SSVEP pilot, the EEG contained clear frequency-specific responses to 9 Hz and 14 Hz visual flicker. Harmonic-aware CCA classified all 40 trials correctly, and permutation controls showed that this result was far above shuffled-label expectation. This validates the visual stimulation, photodiode trigger, EEG acquisition, and analysis pipeline for future SSVEP and attention-based experiments.

---

## 16. Next steps

1. Repeat overt/direct-gaze recording with improved impedance.
2. Record additional subjects.
3. Compare posterior channel reliability.
4. Run the covert attention version.
5. Compare overt vs covert SSVEP strength.
6. Move gradually toward VR-compatible and emotion-related paradigms.
