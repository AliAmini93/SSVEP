# SSVEP Pilot Workflow: Overt/Covert Paradigm, EEG Recording, and Analysis

**Project context:** EEG-based SSVEP pilot as a technical stepping stone toward emotion recognition and prediction in VR serious games using EEG/EMG and deep learning.  
**Current dataset:** First single-subject SSVEP EEG recording, **Overt / Direct-Gaze** version.  
**Main goal:** Verify that the setup can produce a measurable, frequency-specific SSVEP response before moving to more complex covert attention, VR, or emotional-stimulus paradigms.

---

## 1. Why this pilot was designed

The original PhD project is focused on:

> Using EEG-EMG methods and deep learning techniques for emotion recognition and prediction in VR serious games.

Before moving to VR, emotional stimuli, or multimodal EEG-EMG experiments, the immediate technical objective was to test whether the EEG setup, PsychoPy timing, visual flicker generation, photodiode trigger system, and analysis pipeline could reliably capture a basic visual-evoked EEG response.

SSVEP was selected because it is a relatively clean and well-established EEG response. If the setup can detect SSVEP, then the next stages become more realistic:

1. Confirm visual stimulus timing.
2. Confirm EEG trigger alignment.
3. Confirm usable EEG acquisition.
4. Confirm that the recorded EEG contains condition-specific visual responses.
5. Move gradually toward covert attention, VR, and eventually emotion-related paradigms.

---

## 2. Paradigm decision: Covert attention vs Overt/direct gaze

Two versions of the paradigm were considered.

### 2.1 Covert attention version

In the **covert attention** version, the participant keeps their gaze fixed on the central fixation cross while attending to either the left or the right flickering square.

The logic is:

- The participant does **not** directly look at the flickering square.
- The participant keeps gaze on the center cross.
- One square is cued.
- The participant shifts attention toward the cued square while maintaining fixation.
- EEG is analyzed to see whether the attended flicker frequency can be detected.

This version is closer to an attention experiment, but it is more difficult because the SSVEP can be weaker than direct gaze.

### 2.2 Overt / direct-gaze version

In the **overt/direct-gaze** version, the participant directly looks at the cued flickering square during the stimulation period.

The logic is:

- A cue indicates the target side.
- If the left square is cued, the participant looks directly at the left flickering square.
- If the right square is cued, the participant looks directly at the right flickering square.
- Between trials, the participant returns to the fixation cross.
- This should generate a stronger and cleaner SSVEP response.

### 2.3 Why overt was used first

The overt version was selected as the first EEG recording because it is the better technical validation step.

It answers this basic question:

> Can this setup detect a frequency-specific SSVEP response at all?

If overt/direct-gaze SSVEP is not detectable, then covert attention would likely be too difficult to interpret. Therefore, overt/direct-gaze was used first as a setup-validation experiment.

---

## 3. Experimental setup

### 3.1 Hardware

The available EEG setup included:

- **g.tec g.USBamp** EEG amplifiers.
- **g.tec g.TRIGbox** for trigger acquisition.
- **Photodiode / optical sensor** attached to the monitor.
- External monitor connected to the laptop by HDMI.
- PsychoPy running the visual paradigm.

### 3.2 Trigger strategy

The laptop did not have a native parallel port or serial port suitable for low-latency EEG triggers. Therefore, hardware serial/parallel triggers were not used.

Instead, the final trigger strategy used **on-screen photodiode triggers**:

- PsychoPy draws a small trigger image on the monitor.
- A physical photodiode detects the image change.
- g.TRIGbox converts this optical signal into EEG triggers.
- Trigger events are stored in the EEG recording.

This has an important advantage:

> The trigger corresponds to the actual visual event on the screen, not just the time when software attempted to send a command.

---

## 4. PsychoPy experiment design

### 4.1 Visual stimuli

The experiment presents two flickering squares:

| Target | Frequency | Meaning |
|---|---:|---|
| Left square | 9 Hz | Left target condition |
| Right square | 14 Hz | Right target condition |

The square locations were pushed far apart to reduce visual overlap and make direct gaze easier.

The participant sees:

1. A fixation cross.
2. Two square locations.
3. A cue indicating which square is the target.
4. A stimulation period where both squares flicker.
5. A rest/ITI period.

### 4.2 Trial structure

The general trial sequence is:

1. **Fixation period**  
   Participant looks at the center cross.

2. **Cue period**  
   The cued square is highlighted.  
   In the overt version, this tells the participant which square to look at during the next stimulation period.

3. **Stimulation period**  
   Both squares flicker.  
   The participant directly looks at the cued square.

4. **Inter-trial interval (ITI)**  
   Participant returns to the center cross and rests briefly.

### 4.3 Actual recording parameters

The analyzed recording used:

| Parameter | Value |
|---|---:|
| Number of blocks | 4 |
| Trials per block | 10 |
| Total trials | 40 |
| Left trials | 20 |
| Right trials | 20 |
| Left frequency | 9 Hz |
| Right frequency | 14 Hz |
| EEG sampling rate | 512 Hz |
| Channels | 64 |
| Actual stimulation duration used in analyzed files | 30 s per trial |

> Note: Earlier design discussions included shorter stimulation durations. The actual analyzed PsychoPy/EEG data showed a stimulation duration of **30.0 seconds**, which was used by the analysis pipeline.

---

## 5. Photodiode trigger design

### 5.1 Trigger images

The experiment uses the same photodiode images that were used in a previous working experiment:

- `ScreenTrigOn.png`
- `ScreenTrigOff.png`

These images are placed in the same directory as the PsychoPy script.

### 5.2 Two-trigger design

The final version uses two photodiode trigger locations:

| Trigger location | Meaning |
|---|---|
| Left photodiode image | Left target / 9 Hz condition |
| Right photodiode image | Right target / 14 Hz condition |

Only the trigger corresponding to the current target side is activated during a trial.

### 5.3 Trigger timing

For each stimulation period:

- Trigger pulse occurs at stimulation onset.
- Then another trigger pulse occurs every 1 second.
- Each pulse stays ON for 2 frames.
- The trigger side indicates the current target side.

This allows EEG analysis to identify:

1. Trial onset.
2. Target side.
3. Repeated timing markers within each trial.

### 5.4 Trigger IDs found in the EEG

The analysis inferred the following mapping from the EEG HDF5 trigger stream:

| EEG Trigger TypeID | Interpreted side |
|---:|---|
| 15 | Left |
| 16 | Right |

The exact numerical TypeIDs come from the acquisition system and trigger box. The analysis pipeline inferred the mapping by matching the trigger sequence to the PsychoPy trial structure.

---

## 6. Data files

### 6.1 EEG files

The EEG recording was split into two HDF5 files because acquisition stopped before the end and had to be restarted.

The two files were:

```text
Subject12026.04.30_13.59.13.hdf5
Subject1-12026.04.30_14.20.19.hdf5
```

Both belong to the same subject and the same overt/direct-gaze pilot session.

### 6.2 PsychoPy files

The PsychoPy `data` folder contains files such as:

```text
*_trials.csv
*_meta.txt
*_frameIntervals_ms.txt
*_timingSummary.txt
```

Their roles are:

| File | Purpose |
|---|---|
| `*_trials.csv` | Trial-wise behavioral/design log: block, trial number, target side, frequency, timing, photodiode settings |
| `*_meta.txt` | Experiment settings: frequencies, timing, screen, photodiode image paths, stimulus duration |
| `*_frameIntervals_ms.txt` | Frame interval log during stimulation |
| `*_timingSummary.txt` | Summary of dropped frames and display timing |

---

## 7. Analysis workflow overview

The analysis pipeline was organized into five steps:

| Step | Script | Main purpose |
|---:|---|---|
| 01 | `01_inspect_hdf5_ssvep.py` | Inspect HDF5 and PsychoPy files |
| 02 | `02_merge_qc_triggers_ssvep.py` | Merge EEG files, detect triggers, QC channels, preliminary PSD |
| 03 | `03_detailed_ssvep_analysis.py` | Trial-level SSVEP PSD/SNR analysis |
| 04 | `04_harmonic_cca_ssvep_analysis_v4.py` | Harmonic-aware CCA classification |
| 05 | `05_permutation_sanity_check.py` | Permutation and sanity-check controls |

Each step writes its outputs into:

```text
_analysis_report/
```

---

## 8. Step 01 — HDF5 and PsychoPy inspection

### 8.1 Goal

The goal of Step 01 is to answer:

- Which HDF5 files are present?
- What datasets and metadata do they contain?
- What PsychoPy files are available?
- Which PsychoPy file likely belongs to the current EEG recording?

### 8.2 Command

```bat
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"

python 01_inspect_hdf5_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"
```

### 8.3 Output files

```text
_analysis_report\01_hdf5_inventory.json
_analysis_report\01_hdf5_inventory_readable.txt
_analysis_report\01_psychopy_inventory.json
_analysis_report\01_psychopy_inventory_readable.txt
```

### 8.4 What this step checks

This step does not perform SSVEP analysis yet. It is a file-discovery and structure-inspection step.

It is useful because the recording folder may contain multiple EEG files and the PsychoPy data folder may contain several previous runs.

---

## 9. Step 02 — Merge EEG, detect triggers, channel QC, preliminary SSVEP

### 9.1 Goal

Step 02 is the first real EEG-processing step.

It:

1. Loads both HDF5 files.
2. Sorts them by recording time.
3. Merges them into one continuous dataset.
4. Extracts channel names and EEG samples.
5. Detects triggers.
6. Matches triggers to PsychoPy trials.
7. Performs channel quality checks.
8. Generates preliminary PSD plots.

### 9.2 Command

```bat
python 02_merge_qc_triggers_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"
```

### 9.3 Important observed output

The merged EEG data had:

```text
Merged data shape: (795660, 64)
Sampling rate: 512 Hz
Channels: 64
```

The script inferred:

```text
Trigger mapping: {15: "left", 16: "right"}
```

### 9.4 Output folder

```text
_analysis_report\step02
```

### 9.5 Key output files

| File | Meaning |
|---|---|
| `02_summary_report.txt` | Human-readable Step 02 summary |
| `02_trial_event_match.csv` | Matched trials and EEG trigger onsets |
| `02_channel_quality.csv` | Channel-level QC metrics |
| `02_ssvep_channel_summary.csv` | Preliminary SSVEP channel metrics |
| `02_trigger_timeline.png` | Trigger timing plot |
| `02_channel_qc_robust_std.png` | Channel robust standard deviation plot |
| `02_occipital_psd_left_vs_right.png` | Preliminary occipital PSD comparison |

### 9.6 Why this step matters

This step verifies that:

- The two EEG files can be merged.
- Trigger events are present.
- Trigger timing is interpretable.
- Left and right trials can be identified.
- Some posterior EEG channels are usable for SSVEP analysis.

---

## 10. Step 03 — Detailed SSVEP PSD/SNR analysis

### 10.1 Goal

Step 03 checks whether the target frequency has stronger spectral evidence than the non-target frequency.

It uses posterior channels, especially channels around occipital/parieto-occipital regions, where visual responses are expected.

### 10.2 Command

```bat
python 03_detailed_ssvep_analysis.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"
```

### 10.3 Selected posterior channels

The analysis selected:

```text
O1, Oz, O2, PO7, PO3, POz, PO4, PO8, P5, P2, P4, P6, P8
```

These channels are appropriate because SSVEP responses are expected to be strongest over posterior visual cortex.

### 10.4 Output folder

```text
_analysis_report\step03
```

### 10.5 Key output files

| File | Meaning |
|---|---|
| `03_summary_report.txt` | Step 03 summary |
| `03_condition_summary.csv` | Mean SNR by condition |
| `03_best_channels.csv` | Channels ranked by SSVEP evidence |
| `03_trial_level_ssvep.csv` | Trial-level SSVEP metrics |
| `03_channel_condition_summary.csv` | Channel-by-condition summary |
| `03_condition_target_vs_nontarget_snr.png` | Target vs non-target SNR by condition |
| `03_trial_level_evidence.png` | Trial-level SSVEP evidence |
| `03_snr_9_vs_14_scatter.png` | 9 Hz vs 14 Hz trial-level SNR scatter |
| `03_best_channels_evidence.png` | Best posterior channels |
| `03_selected_posterior_psd_by_condition.png` | Posterior PSD by condition |

### 10.6 Interpretation

Step 03 showed visible frequency-specific SSVEP structure, especially over posterior channels.

However, PSD/SNR analysis alone is descriptive. Therefore, Step 04 used CCA for stronger classification-style evidence.

---

## 11. Step 04 — Harmonic-aware CCA analysis

### 11.1 Goal

CCA was used to classify each trial as either:

- 9 Hz / left
- 14 Hz / right

The CCA reference signals included harmonics:

| Target frequency | Harmonics used |
|---:|---|
| 9 Hz | 9, 18, 27 Hz |
| 14 Hz | 14, 28, 42 Hz |

Including harmonics is important because SSVEP responses often appear not only at the fundamental frequency but also at harmonic frequencies.

### 11.2 Command

```bat
python 04_harmonic_cca_ssvep_analysis_v4.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"
```

### 11.3 Important implementation note

Earlier versions of Step 04 produced errors because helper functions from Step 03 returned more values than expected and because onset-column names differed. The working version was:

```text
04_harmonic_cca_ssvep_analysis_v4.py
```

This version correctly used:

```text
stim_start_sample
```

as the trial onset column.

### 11.4 Output folder

```text
_analysis_report\step04
```

### 11.5 Key output files

| File | Meaning |
|---|---|
| `04_summary_report.txt` | CCA result summary |
| `04_trial_level_cca.csv` | Trial-wise CCA correlations and predicted labels |
| `04_condition_cca_summary.csv` | Accuracy and CCA summary by condition |
| `04_cca_9_vs_14_scatter.png` | Trial-level 9 Hz vs 14 Hz CCA scatter |
| `04_cca_accuracy_by_condition.png` | Classification accuracy by condition |
| `04_cca_trial_margin.png` | Trial-wise CCA margin |

### 11.6 Main result

Step 04 showed:

```text
CCA accuracy: 40/40 trials correct
Observed accuracy: 100%
```

This means the CCA classifier correctly identified the target frequency for every analyzed trial.

### 11.7 Interpretation

This is strong evidence that the overt/direct-gaze recording contained a robust frequency-specific SSVEP response.

However, because this was only one subject, the result should be framed as a successful pilot validation, not as a generalizable group-level result.

---

## 12. Step 05 — Permutation and sanity-check controls

### 12.1 Goal

Step 05 checks whether the 100% CCA result could be explained by:

- Random label structure.
- Trial ordering artifacts.
- A trivial classification bias.
- Target/non-target ambiguity.

### 12.2 Command

```bat
python 05_permutation_sanity_check.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"
```

### 12.3 Output folder

```text
_analysis_report\step05
```

### 12.4 Key output files

| File | Meaning |
|---|---|
| `05_summary_report.txt` | Main permutation/sanity-check summary |
| `05_trial_sanity_check.csv` | Trial-wise target vs non-target CCA rho |
| `05_condition_sanity_summary.csv` | Condition-level sanity summary |
| `05_permutation_accuracy_distribution.csv` | Monte-Carlo shuffled-label distribution |
| `05_exact_label_shuffle_distribution.csv` | Exact label-shuffle distribution |
| `05_permutation_accuracy_hist.png` | Shuffled-label accuracy distribution |
| `05_signed_margin_hist.png` | Sign-flip null distribution for target margin |
| `05_target_vs_nontarget_rho.png` | Target vs non-target CCA rho per trial |
| `05_target_vs_nontarget_scatter.png` | Target rho should exceed non-target rho |

### 12.5 Main observed results

The Step 05 report showed:

```text
Trials analyzed: 40
True labels: left=20, right=20
Predicted labels: left=20, right=20

Observed correct trials: 40/40
Observed accuracy: 100.00%

Mean target rho: 0.343332
Mean non-target rho: 0.127495
Mean signed target margin: 0.215837
Minimum signed target margin: 0.022109
```

### 12.6 Condition-level results

```text
Left condition:
n = 20
accuracy = 100.0%
mean target rho = 0.399265
mean non-target rho = 0.074247
mean margin = 0.325017
minimum margin = 0.128872

Right condition:
n = 20
accuracy = 100.0%
mean target rho = 0.287399
mean non-target rho = 0.180742
mean margin = 0.106657
minimum margin = 0.022109
```

The left/9 Hz condition was stronger than the right/14 Hz condition, but both were classified perfectly.

### 12.7 Permutation results

```text
Monte-Carlo shuffled-label p-value: 0.00009999
Exact label-shuffle p-value: 7.25444455192e-12
Monte-Carlo sign-flip p-value: 0.00009999
```

### 12.8 Interpretation

The observed 100% accuracy is far above what would be expected from shuffled labels.

Every trial had:

```text
target CCA rho > non-target CCA rho
```

This is a strong trial-level sanity check.

The result supports the conclusion that the Step 04 CCA classification reflects real condition-specific SSVEP structure rather than a simple label/order artifact.

---

## 13. Complete command sequence

From the project code folder:

```bat
cd /d "F:\KTU\Lithuania\Secondment Denmark\Codes"
```

Then run:

```bat
python 01_inspect_hdf5_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"

python 02_merge_qc_triggers_ssvep.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt" ^
  --psychopy_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\data"

python 03_detailed_ssvep_analysis.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"

python 04_harmonic_cca_ssvep_analysis_v4.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"

python 05_permutation_sanity_check.py ^
  --data_dir "F:\KTU\Lithuania\Secondment Denmark\Codes\First SSVEP EEG Recording- Overt"
```

---

## 14. Recommended GitHub repository structure

A clean repository could be structured like this:

```text
ssvep-pilot/
│
├── README.md
├── WORKFLOW.md
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
│   └── trigger_setup_notes.md
│
├── data/
│   └── README.md
│
└── reports/
    └── README.md
```

### Data privacy note

Raw EEG files should usually not be committed to GitHub unless:

- the participant consent allows it,
- the dataset is anonymized,
- the repository is private,
- and the institution/supervisor approves.

Instead, use a `data/README.md` explaining where the raw data should be placed locally.

---

## 15. Quality-control issues observed

### 15.1 Electrode impedance

The impedance screenshots showed that many channels had high impedance. This is not ideal and should be improved in future recordings.

Despite this, posterior channels still produced a strong SSVEP response.

### 15.2 Split recording

The recording was split into two HDF5 files:

```text
Subject12026.04.30_13.59.13.hdf5
Subject1-12026.04.30_14.20.19.hdf5
```

This was handled by sorting and merging the files by recording time.

### 15.3 Dropped frames and external monitor

The external monitor was connected through HDMI. Earlier tests showed that dropped frames increased on the external screen compared with the laptop screen.

For future recordings:

- Use second-screen-only mode if possible.
- Close all unnecessary background applications.
- Disable notifications.
- Avoid browser/video/background updates.
- Confirm stable frame timing before recording.
- Save frame intervals for every run.

### 15.4 Overt is not covert

The current result validates direct visual SSVEP recording.

It does **not** yet prove that covert attention can be decoded. Covert attention should be treated as a later, harder experiment.

---

## 16. Current conclusion

The first single-subject overt/direct-gaze SSVEP recording successfully demonstrated a clear SSVEP response.

Main conclusions:

1. The photodiode-based trigger setup worked.
2. The two split HDF5 files could be merged.
3. Trigger IDs could be mapped to left/right target conditions.
4. Posterior EEG channels showed frequency-specific responses.
5. Harmonic-aware CCA classified 40/40 trials correctly.
6. Permutation and sign-flip controls supported that this was not a trivial label artifact.

A careful statement for reporting is:

> In this single-subject overt/direct-gaze SSVEP pilot, the EEG contained clear frequency-specific responses to 9 Hz and 14 Hz flickering targets. Harmonic-aware CCA classified all 40 trials correctly, and permutation controls confirmed that the result was far above shuffled-label expectation. This validates the basic visual stimulation, photodiode triggering, EEG acquisition, and analysis pipeline for future SSVEP and attention-based experiments.

---

## 17. Next steps

Recommended next steps:

1. Repeat overt/direct-gaze recording with better electrode impedance.
2. Run at least a few more subjects to test robustness.
3. Compare results across posterior channels.
4. Then run the covert attention version.
5. Compare overt vs covert SSVEP strength.
6. Eventually adapt the paradigm toward VR or emotion-related visual stimuli.
7. Use the validated pipeline as a foundation for future EEG/EMG and deep-learning work.

---

## 18. Short glossary

| Term | Meaning |
|---|---|
| SSVEP | Steady-State Visual Evoked Potential |
| Overt/direct gaze | Participant directly looks at the flickering target |
| Covert attention | Participant keeps gaze fixed but attends to a peripheral target |
| Photodiode trigger | Optical trigger created by screen brightness change |
| g.TRIGbox | g.tec trigger interface |
| g.USBamp | g.tec EEG amplifier |
| PSD | Power Spectral Density |
| SNR | Signal-to-Noise Ratio |
| CCA | Canonical Correlation Analysis |
| Harmonics | Multiples of the stimulation frequency, e.g., 9, 18, 27 Hz |

---

## 19. Minimal reproducible interpretation

If only one sentence is needed:

> The overt SSVEP pilot successfully produced a robust frequency-specific EEG response, with perfect harmonic-aware CCA classification across 40 trials and statistically strong permutation-control evidence.

