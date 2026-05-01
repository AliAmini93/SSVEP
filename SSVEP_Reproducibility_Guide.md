# Reproducibility Guide — SSVEP Overt/Covert EEG Pilot

**Purpose of this file:**  
This document gives a complete, step-by-step protocol for reproducing the SSVEP pilot experiment and analysis pipeline when a new subject is added.

It is intended for use in a GitHub repository so that the full workflow can be repeated later with minimal ambiguity.

---

## 0. Project summary

This project validates an EEG-based SSVEP paradigm using PsychoPy, g.tec EEG hardware, g.TRIGbox, and optical/photodiode triggers.

The current validated pilot is the **Overt / Direct-Gaze SSVEP version**, where the participant directly looks at the cued flickering square.

The experiment uses two flickering visual targets:

| Target side | Frequency | Trigger side | EEG trigger TypeID observed |
|---|---:|---|---:|
| Left | 9 Hz | Left photodiode | 15 |
| Right | 14 Hz | Right photodiode | 16 |

The current analysis pipeline verifies:

1. HDF5 EEG file structure.
2. PsychoPy metadata and trial logs.
3. EEG file merging when recording is split.
4. Trigger detection and left/right mapping.
5. Channel quality control.
6. SSVEP PSD/SNR evidence.
7. Harmonic-aware CCA classification.
8. Permutation and sign-flip sanity checks.

---

## 1. Repository structure

Recommended GitHub structure:

```text
ssvep-pilot/
│
├── README.md
├── WORKFLOW.md
├── REPRODUCIBILITY_GUIDE.md
├── requirements.txt
│
├── psychopy/
│   ├── psychopy_ssvep_overt_direct_gaze.py
│   ├── psychopy_ssvep_covert_attention.py
│   ├── ScreenTrigOn.png
│   └── ScreenTrigOff.png
│
├── analysis/
│   ├── 01_inspect_hdf5_ssvep.py
│   ├── 02_merge_qc_triggers_ssvep.py
│   ├── 03_detailed_ssvep_analysis.py
│   ├── 04_harmonic_cca_ssvep_analysis_v4.py
│   └── 05_permutation_sanity_check.py
│
├── docs/
│   ├── participant_instructions_overt.md
│   ├── participant_instructions_covert.md
│   ├── hardware_setup.md
│   └── photodiode_trigger_setup.md
│
├── data/
│   ├── README.md
│   └── psychopy_logs/
│
├── raw_eeg/
│   └── README.md
│
└── reports/
    └── README.md
```

### Important note about raw EEG data

Do **not** commit raw EEG data to a public GitHub repository unless:

- participant consent allows it,
- the data are anonymized,
- institutional/supervisor approval has been obtained,
- and the repository is intended to be public.

For private lab work, raw files can be stored locally or in a secure institutional storage location. The GitHub repository can contain the code, metadata examples, and documentation.

---

## 2. Local folder structure for running the pipeline

On the acquisition/analysis computer, use a consistent folder structure.

Example Windows layout used in the pilot:

```text
F:\KTU\Lithuania\Secondment Denmark\Codes\
│
├── psychopy_ssvep_pilot.py
├── psychopy_ssvep_overt_direct_gaze.py
├── ScreenTrigOn.png
├── ScreenTrigOff.png
│
├── data\
│   ├── *_trials.csv
│   ├── *_meta.txt
│   ├── *_frameIntervals_ms.txt
│   └── *_timingSummary.txt
│
├── First SSVEP EEG Recording- Overt\
│   ├── Subject12026.04.30_13.59.13.hdf5
│   ├── Subject1-12026.04.30_14.20.19.hdf5
│   └── _analysis_report\
│
├── 01_inspect_hdf5_ssvep.py
├── 02_merge_qc_triggers_ssvep.py
├── 03_detailed_ssvep_analysis.py
├── 04_harmonic_cca_ssvep_analysis_v4.py
└── 05_permutation_sanity_check.py
```

For a new subject, create a new EEG folder, for example:

```text
F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_Subject002_Overt\
```

Put all HDF5 files for that subject/session inside that folder.

---

## 3. Software requirements

### 3.1 PsychoPy environment for running the experiment

The PsychoPy experiment should be run from the PsychoPy environment.

Example:

```bat
conda activate psychopy
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"
python psychopy_ssvep_overt_direct_gaze.py
```

### 3.2 Python environment for analysis

The analysis scripts were run from the base Anaconda environment.

Example:

```bat
conda activate base
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"
```

### 3.3 Python packages

The analysis pipeline expects common scientific Python packages:

```text
numpy
pandas
scipy
matplotlib
h5py
```

Optional but useful:

```text
mne
scikit-learn
```

Example installation:

```bat
pip install numpy pandas scipy matplotlib h5py scikit-learn mne
```

If using Anaconda:

```bat
conda install numpy pandas scipy matplotlib h5py scikit-learn
pip install mne
```

---

## 4. Hardware setup

### 4.1 EEG hardware

The pilot used:

- g.tec g.USBamp amplifiers
- g.tec g.TRIGbox
- Optical photodiode sensor
- External monitor
- Laptop running PsychoPy
- HDMI connection to the external monitor

### 4.2 Triggering method

The final working trigger method is **photodiode-based**.

No parallel port and no serial port are required.

The logic is:

```text
PsychoPy screen image change
        ↓
Photodiode detects brightness change
        ↓
g.TRIGbox converts optical signal to trigger
        ↓
Trigger is stored in the EEG HDF5 file
```

This is preferred because the trigger reflects the actual screen event.

### 4.3 Photodiode images

The experiment requires two image files in the same folder as the PsychoPy script:

```text
ScreenTrigOn.png
ScreenTrigOff.png
```

These files were copied from a previously working experiment and should not be resized manually.

In PsychoPy they are drawn with:

```python
units="height"
size=0.05
```

This matches the previously tested photodiode setup.

### 4.4 Photodiode positions

The final two-trigger version uses:

```python
LEFT_PHOTODIODE_POS = (-0.7, -0.4)
RIGHT_PHOTODIODE_POS = (0.7, -0.4)
PHOTODIODE_SIZE = 0.05
```

The physical sensors should be aligned with these locations.

If the photodiode is physically moved, update only the corresponding `LEFT_PHOTODIODE_POS` or `RIGHT_PHOTODIODE_POS`.

---

## 5. Display setup before recording

Before recording EEG:

1. Connect the external monitor using HDMI.
2. In Windows Display Settings, select the correct screen mode.
3. Prefer **Second screen only** if the external monitor is used for stimulus presentation.
4. Confirm the correct PsychoPy `SCREEN_INDEX`.

Typical values:

```python
SCREEN_INDEX = 0  # laptop screen or main display
SCREEN_INDEX = 1  # external monitor
```

In the pilot, the external monitor used:

```python
SCREEN_INDEX = 1
```

### 5.1 Reduce dropped frames

Before running the actual recording:

- Close browsers.
- Close Teams/Outlook/OneDrive sync if possible.
- Close background apps.
- Disable notifications.
- Keep the laptop plugged in.
- Use high-performance power mode.
- Avoid screen recording.
- Avoid duplicated desktop if it causes frame drops.
- Run a short timing test before recording.

### 5.2 Expected refresh behavior

The experiment is designed for nominal:

```text
60 Hz
```

The monitor may be measured as around 58.9–59.9 Hz. The final experimental code used a nominal 60 Hz design.

---

## 6. Electrode impedance and EEG preparation

Before starting the task:

1. Mount EEG cap.
2. Apply gel.
3. Check impedance.
4. Prioritize posterior electrodes because SSVEP is expected over visual cortex.

Important posterior channels:

```text
O1, Oz, O2,
PO7, PO3, POz, PO4, PO8,
P5, P2, P4, P6, P8
```

### 6.1 Impedance target

Ideal:

```text
<= 5 kOhm
```

Acceptable if needed:

```text
<= 10–20 kOhm
```

Problematic:

```text
> 20 kOhm
```

In the first pilot, many channels had poor impedance, but posterior channels still showed strong SSVEP evidence. Future recordings should improve impedance, especially over occipital and parieto-occipital sites.

---

## 7. Experiment versions

### 7.1 Overt / direct-gaze version

Participant instruction:

```text
Look at the center cross between trials.
When one square is cued, look directly at that square during the flickering period.
Try to keep your head still and avoid blinking during the flickering period.
```

This version is used to validate the basic SSVEP pipeline.

### 7.2 Covert attention version

Participant instruction:

```text
Always keep your eyes on the center cross.
When one square is cued, attend to that square without moving your eyes to it.
```

This version is harder and should be run only after the overt/direct-gaze pipeline is validated.

---

## 8. Current validated experiment parameters

The validated single-subject overt pilot used:

| Parameter | Value |
|---|---:|
| Left frequency | 9 Hz |
| Right frequency | 14 Hz |
| Nominal refresh rate | 60 Hz |
| EEG sampling rate | 512 Hz |
| Number of blocks | 4 |
| Trials per block | 10 |
| Total trials | 40 |
| Left trials | 20 |
| Right trials | 20 |
| Stimulation duration in analyzed run | 30 s |
| Trigger pulse interval | 1 s |
| Trigger ON duration | 2 frames |
| Photodiode trigger side | Same as attended/target side |

### 8.1 Important note about stimulation duration

Earlier design versions discussed 10 seconds per trial.  
However, the analyzed PsychoPy/EEG files showed:

```text
Stim duration: 30.0
```

Therefore, the analysis used 30-second trial windows.

For future experiments, confirm the intended value in the PsychoPy script:

```python
STIM_DUR = 30.0
```

or, if using shorter trials:

```python
STIM_DUR = 10.0
```

Keep the PsychoPy code, metadata, and analysis interpretation consistent.

---

## 9. Running the PsychoPy experiment

### 9.1 Before running

Confirm these files are in the same folder:

```text
psychopy_ssvep_overt_direct_gaze.py
ScreenTrigOn.png
ScreenTrigOff.png
```

Confirm key settings in the PsychoPy script:

```python
FULLSCREEN = True
SCREEN_INDEX = 1

LEFT_FREQ = 9
RIGHT_FREQ = 14

STIM_DUR = 30.0  # or the intended current duration

USE_PHOTODIODE_PATCH = True

LEFT_PHOTODIODE_POS = (-0.7, -0.4)
RIGHT_PHOTODIODE_POS = (0.7, -0.4)
PHOTODIODE_SIZE = 0.05

PHOTODIODE_ON_FRAMES = 2
PHOTODIODE_PULSE_INTERVAL_S = 1.0
```

### 9.2 Run command

```bat
conda activate psychopy
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"
python psychopy_ssvep_overt_direct_gaze.py
```

### 9.3 During the run

The participant should follow:

1. Start screen: press SPACE when ready.
2. Block screen: press SPACE to start each block.
3. Fixation: look at the center cross.
4. Cue: identify the highlighted square.
5. Stimulation:
   - Overt version: look directly at the cued square.
   - Covert version: keep eyes on the cross and attend to the cued square.
6. ITI: return gaze to the center cross.
7. Break screen: blink/rest; press SPACE to continue.
8. End screen: press SPACE to close.

---

## 10. Files generated by PsychoPy

The PsychoPy script writes files into:

```text
data\
```

Typical files:

```text
005_005_2026-04-30_13h59.55.909_simple_ssvep_direct_gaze_pilot_trials.csv
005_005_2026-04-30_13h59.55.909_simple_ssvep_direct_gaze_pilot_meta.txt
005_005_2026-04-30_13h59.55.909_simple_ssvep_direct_gaze_pilot_frameIntervals_ms.txt
005_005_2026-04-30_13h59.55.909_simple_ssvep_direct_gaze_pilot_timingSummary.txt
```

### 10.1 `*_trials.csv`

Contains trial-wise information:

- participant
- session
- date
- block
- trial number
- attended side
- target frequency
- stimulation onset
- photodiode side
- expected number of trigger pulses
- dropped frames
- frame interval statistics

### 10.2 `*_meta.txt`

Contains experiment-level metadata:

- frequencies
- screen index
- fullscreen setting
- stimulus duration
- photodiode image paths
- trigger positions
- pulse interval
- display timing information

### 10.3 `*_frameIntervals_ms.txt`

Contains frame interval values during stimulation.

Used for checking timing stability.

### 10.4 `*_timingSummary.txt`

Contains timing summary:

- expected frame duration
- refresh threshold
- mean/min/max frame interval
- dropped frames
- number of intervals over threshold

---

## 11. EEG recording files

The EEG acquisition system saves `.hdf5` files.

Example from the first pilot:

```text
Subject12026.04.30_13.59.13.hdf5
Subject1-12026.04.30_14.20.19.hdf5
```

If recording is interrupted and restarted, multiple HDF5 files may exist for one subject. The pipeline can merge them if they are placed in the same subject folder.

For a new subject, place all HDF5 files here:

```text
F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt\
```

---

## 12. Full analysis pipeline

All commands below assume:

```bat
conda activate base
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"
```

Define these paths manually:

```text
DATA_DIR = F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt
PSYCHOPY_DIR = F:\KTU\Lithuania\Secondment Denmark\Codes\data
```

Replace `SSVEP_SubjectXXX_Overt` with the real folder.

---

## 13. Step 01 — Inspect HDF5 and PsychoPy files

### 13.1 Purpose

This step checks what files exist and what they contain.

It helps identify:

- available HDF5 files,
- EEG channel names,
- sampling rate,
- trigger arrays,
- PsychoPy trial files,
- PsychoPy metadata files.

### 13.2 Command

```bat
python 01_inspect_hdf5_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"
```

### 13.3 Expected outputs

```text
_analysis_report\01_hdf5_inventory.json
_analysis_report\01_hdf5_inventory_readable.txt
_analysis_report\01_psychopy_inventory.json
_analysis_report\01_psychopy_inventory_readable.txt
```

### 13.4 What to check

Open:

```text
01_hdf5_inventory_readable.txt
01_psychopy_inventory_readable.txt
```

Check:

- number of HDF5 files,
- sampling rate,
- channel count,
- recording duration,
- whether triggers exist,
- which PsychoPy files are likely linked to this subject.

---

## 14. Step 02 — Merge EEG, QC channels, detect triggers

### 14.1 Purpose

This step:

1. Loads all HDF5 files in the subject folder.
2. Sorts them by recording time.
3. Merges them.
4. Extracts EEG and triggers.
5. Infers trigger mapping.
6. Matches EEG triggers to PsychoPy trials.
7. Performs basic channel quality control.
8. Generates preliminary PSD plots.

### 14.2 Command

```bat
python 02_merge_qc_triggers_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"
```

### 14.3 Expected outputs

```text
_analysis_report\step02\02_summary_report.txt
_analysis_report\step02\02_trial_event_match.csv
_analysis_report\step02\02_channel_quality.csv
_analysis_report\step02\02_ssvep_channel_summary.csv

_analysis_report\step02\02_trigger_timeline.png
_analysis_report\step02\02_channel_qc_robust_std.png
_analysis_report\step02\02_occipital_psd_left_vs_right.png
```

### 14.4 What to check

Open `02_summary_report.txt`.

Confirm:

- merged data shape is reasonable,
- sampling rate is 512 Hz,
- channel count is 64,
- trigger TypeIDs are detected,
- left/right trigger mapping is inferred,
- total matched trials equals expected trial count.

For the first pilot, the important result was:

```text
Inferred mapping: {15: 'left', 16: 'right'}
```

### 14.5 Trigger timeline check

Open:

```text
02_trigger_timeline.png
```

Expected:

- triggers appear in groups,
- TypeID 15 and TypeID 16 correspond to left/right conditions,
- there should be repeated 1-second trigger pulses during each stimulation period,
- large gaps correspond to instructions/breaks/ITI or recording interruption.

### 14.6 Channel QC check

Open:

```text
02_channel_qc_robust_std.png
02_channel_quality.csv
```

Look for:

- extremely noisy channels,
- flat channels,
- channels with abnormal robust standard deviation,
- posterior channels that remain usable.

---

## 15. Step 03 — Detailed PSD/SNR SSVEP analysis

### 15.1 Purpose

This step evaluates SSVEP evidence using spectral power and SNR.

It focuses on posterior channels:

```text
O1, Oz, O2, PO7, PO3, POz, PO4, PO8, P5, P2, P4, P6, P8
```

### 15.2 Command

```bat
python 03_detailed_ssvep_analysis.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"
```

### 15.3 Expected outputs

```text
_analysis_report\step03\03_summary_report.txt
_analysis_report\step03\03_condition_summary.csv
_analysis_report\step03\03_best_channels.csv
_analysis_report\step03\03_trial_level_ssvep.csv
_analysis_report\step03\03_channel_condition_summary.csv

_analysis_report\step03\03_condition_target_vs_nontarget_snr.png
_analysis_report\step03\03_trial_level_evidence.png
_analysis_report\step03\03_snr_9_vs_14_scatter.png
_analysis_report\step03\03_best_channels_evidence.png
_analysis_report\step03\03_selected_posterior_psd_by_condition.png
```

### 15.4 What to check

Open:

```text
03_summary_report.txt
03_condition_target_vs_nontarget_snr.png
03_selected_posterior_psd_by_condition.png
```

Expected:

- target frequency evidence should be stronger than non-target frequency evidence,
- posterior channels should show peaks near 9 Hz and/or 14 Hz,
- harmonics may also appear.

### 15.5 Interpretation rule

PSD/SNR evidence is useful but not final.

If Step 03 looks promising, continue to Step 04 CCA.

---

## 16. Step 04 — Harmonic-aware CCA analysis

### 16.1 Purpose

This step performs CCA classification of each trial.

It tests whether the EEG is more similar to:

- 9 Hz harmonic reference signals,
- or 14 Hz harmonic reference signals.

### 16.2 Harmonics

For 9 Hz:

```text
9, 18, 27 Hz
```

For 14 Hz:

```text
14, 28, 42 Hz
```

### 16.3 Command

```bat
python 04_harmonic_cca_ssvep_analysis_v4.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"
```

### 16.4 Expected outputs

```text
_analysis_report\step04\04_summary_report.txt
_analysis_report\step04\04_trial_level_cca.csv
_analysis_report\step04\04_condition_cca_summary.csv

_analysis_report\step04\04_cca_9_vs_14_scatter.png
_analysis_report\step04\04_cca_accuracy_by_condition.png
_analysis_report\step04\04_cca_trial_margin.png
```

### 16.5 What to check

Open:

```text
04_summary_report.txt
04_cca_accuracy_by_condition.png
04_cca_9_vs_14_scatter.png
```

Expected for a strong overt SSVEP dataset:

- high classification accuracy,
- left trials cluster toward higher 9 Hz CCA correlation,
- right trials cluster toward higher 14 Hz CCA correlation,
- positive trial-level margins for most or all trials.

### 16.6 First pilot result

The first overt/direct-gaze subject showed:

```text
40/40 trials correctly classified
100% CCA accuracy
```

This is strong pilot evidence.

---

## 17. Step 05 — Permutation and sanity-check controls

### 17.1 Purpose

This step verifies that Step 04 did not produce a trivial or misleading result.

It checks:

1. Target CCA rho vs non-target CCA rho.
2. Shuffled-label accuracy distribution.
3. Sign-flip null distribution.
4. Whether all or most trials have positive target margin.

### 17.2 Command

```bat
python 05_permutation_sanity_check.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"
```

### 17.3 Expected outputs

```text
_analysis_report\step05\05_summary_report.txt
_analysis_report\step05\05_trial_sanity_check.csv
_analysis_report\step05\05_condition_sanity_summary.csv
_analysis_report\step05\05_permutation_accuracy_distribution.csv
_analysis_report\step05\05_exact_label_shuffle_distribution.csv

_analysis_report\step05\05_permutation_accuracy_hist.png
_analysis_report\step05\05_signed_margin_hist.png
_analysis_report\step05\05_target_vs_nontarget_rho.png
_analysis_report\step05\05_target_vs_nontarget_scatter.png
```

### 17.4 What to check

Open:

```text
05_summary_report.txt
05_target_vs_nontarget_scatter.png
05_permutation_accuracy_hist.png
```

Expected for a strong result:

- observed accuracy higher than shuffled-label accuracy,
- target rho exceeds non-target rho,
- positive signed margin,
- low permutation p-value.

### 17.5 First pilot result

The first subject showed:

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

This supports a real frequency-specific SSVEP effect.

---

## 18. One-command checklist for a new subject

Replace paths as needed.

```bat
conda activate base

cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"

python 01_inspect_hdf5_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"

python 02_merge_qc_triggers_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"

python 03_detailed_ssvep_analysis.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"

python 04_harmonic_cca_ssvep_analysis_v4.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"

python 05_permutation_sanity_check.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\SSVEP_SubjectXXX_Overt"
```

---

## 19. New subject checklist

Before recording:

- [ ] Create subject folder.
- [ ] Confirm subject ID.
- [ ] Confirm session ID.
- [ ] Confirm PsychoPy script version.
- [ ] Confirm `ScreenTrigOn.png` and `ScreenTrigOff.png` exist.
- [ ] Confirm external monitor is selected.
- [ ] Confirm `SCREEN_INDEX`.
- [ ] Confirm photodiode alignment.
- [ ] Confirm g.TRIGbox is receiving optical triggers.
- [ ] Confirm EEG acquisition software is recording triggers.
- [ ] Check impedance, especially posterior electrodes.
- [ ] Close unnecessary background apps.
- [ ] Run short test.
- [ ] Inspect dropped frames after test.
- [ ] Start real recording.
- [ ] Save EEG HDF5 files.
- [ ] Save PsychoPy files.

After recording:

- [ ] Copy HDF5 files into the subject folder.
- [ ] Confirm PsychoPy files are in `data`.
- [ ] Run Step 01.
- [ ] Run Step 02.
- [ ] Confirm triggers are detected.
- [ ] Confirm trials are matched.
- [ ] Run Step 03.
- [ ] Run Step 04.
- [ ] Run Step 05.
- [ ] Save plots and summary reports.
- [ ] Write subject-specific notes.

---

## 20. Subject/session log template

Use this template for each new recording.

```text
Subject ID:
Session ID:
Date:
Experiment version:
Overt or covert:
PsychoPy script name:
EEG folder:
PsychoPy data files:
HDF5 files:

Monitor:
Screen index:
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
Bad channels noticed during recording:

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

## 21. Troubleshooting

### 21.1 PsychoPy cannot find photodiode images

Error example:

```text
FileNotFoundError: Could not find photodiode ON image
```

Fix:

- Ensure these files are in the same folder as the PsychoPy script:

```text
ScreenTrigOn.png
ScreenTrigOff.png
```

### 21.2 PsychoPy opens on the wrong screen

Fix:

Change:

```python
SCREEN_INDEX = 0
```

or:

```python
SCREEN_INDEX = 1
```

Then rerun.

### 21.3 Many dropped frames

Possible causes:

- external monitor over HDMI,
- duplicated desktop mode,
- background apps,
- GPU/driver issue,
- power-saving mode,
- Windows notifications,
- screen recording,
- browser open in background.

Fix:

- use second-screen-only mode,
- close background applications,
- plug in laptop,
- use performance mode,
- test both screen indices,
- run timing test before EEG recording.

### 21.4 Trigger IDs are not 15 and 16

The TypeIDs may depend on the g.TRIGbox setup.

Fix:

- inspect Step 02 trigger timeline,
- use `02_trial_event_match.csv`,
- infer mapping from trial order and PsychoPy `attend_side`,
- update documentation if a different mapping is used.

### 21.5 HDF5 recording is split into multiple files

This is acceptable.

Fix:

- put all subject/session HDF5 files in the same subject folder,
- Step 02 and later scripts should merge them by recording time.

### 21.6 CCA accuracy is low

Possible causes:

- participant did not look at cued square in overt version,
- wrong trigger mapping,
- wrong PsychoPy trial file selected,
- poor electrode impedance,
- noisy posterior channels,
- wrong screen timing,
- incorrect `STIM_DUR`,
- trial onset mismatch.

Check:

1. `02_trigger_timeline.png`
2. `02_trial_event_match.csv`
3. `03_selected_posterior_psd_by_condition.png`
4. `04_trial_level_cca.csv`
5. `05_target_vs_nontarget_scatter.png`

---

## 22. Minimal criteria for a successful overt SSVEP pilot

A new overt/direct-gaze subject should ideally show:

- triggers detected and mapped to left/right,
- matched trial count close to expected,
- usable posterior channels,
- visible PSD peaks near 9 Hz and/or 14 Hz,
- target SNR higher than non-target SNR,
- CCA accuracy clearly above chance,
- permutation p-value indicating non-random classification.

For a 2-class balanced 40-trial task, chance is about:

```text
50%
```

A very strong result is:

```text
> 90% CCA accuracy
```

The first pilot reached:

```text
100% CCA accuracy
```

---

## 23. Minimal criteria for moving to covert attention

Before moving to covert attention, confirm overt/direct-gaze results across more than one subject if possible.

Recommended:

- at least 2–3 overt recordings,
- stable trigger detection,
- acceptable posterior channel quality,
- strong CCA classification,
- consistent trial timing.

Then run covert attention as a harder version.

---

## 24. How to describe the current result

Use careful wording:

```text
This single-subject overt/direct-gaze SSVEP pilot showed a clear frequency-specific EEG response. Harmonic-aware CCA classified all 40 trials correctly, and permutation controls showed that this performance was far above shuffled-label expectation. This validates the visual stimulation, photodiode trigger, EEG recording, and analysis pipeline for future SSVEP experiments.
```

Avoid overclaiming:

```text
This does not yet prove covert attention decoding.
This does not yet prove generalizable performance across subjects.
This does not yet address emotion recognition directly.
This does not yet involve VR or EMG.
```

---

## 25. Version-control recommendations

For each major change:

1. Commit the PsychoPy script.
2. Commit analysis scripts.
3. Commit this reproducibility guide.
4. Do not commit raw EEG unless approved.
5. Commit summary CSVs and plots if anonymized and allowed.
6. Tag stable versions.

Example commit messages:

```text
Add overt SSVEP PsychoPy paradigm with photodiode triggers
Add HDF5 inspection and trigger matching pipeline
Add harmonic CCA analysis for 9 Hz vs 14 Hz SSVEP
Add permutation sanity checks for CCA results
Add reproducibility guide for new subjects
```

---

## 26. Recommended report-generation workflow

After running all analysis steps for a subject:

1. Read `02_summary_report.txt`.
2. Read `03_summary_report.txt`.
3. Read `04_summary_report.txt`.
4. Read `05_summary_report.txt`.
5. Inspect key plots:
   - `02_trigger_timeline.png`
   - `02_channel_qc_robust_std.png`
   - `03_selected_posterior_psd_by_condition.png`
   - `04_cca_9_vs_14_scatter.png`
   - `04_cca_accuracy_by_condition.png`
   - `05_target_vs_nontarget_scatter.png`
   - `05_permutation_accuracy_hist.png`
6. Write final report using:
   - experimental design,
   - hardware setup,
   - data quality,
   - trigger validation,
   - PSD/SNR results,
   - CCA results,
   - permutation controls,
   - limitations,
   - next steps.

---

## 27. Final reproducibility principle

For every new subject, always preserve:

1. Raw HDF5 files.
2. PsychoPy trial CSV.
3. PsychoPy metadata TXT.
4. Frame interval log.
5. Timing summary.
6. Analysis scripts used.
7. Generated `_analysis_report` folder.
8. Notes about impedance, display setup, participant behavior, and recording interruptions.

Without these, the result may be hard to interpret later.

