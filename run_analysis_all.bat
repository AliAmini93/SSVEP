@echo off
cd /d "%~dp0"

echo Running Step 01...
python Scripts\01_inspect_hdf5_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"

echo.
echo Running Step 02...
python Scripts\02_merge_qc_triggers_ssvep.py --data_dir "EEG Recorded data" --psychopy_dir "data"

echo.
echo Running Step 03...
python Scripts\03_detailed_ssvep_analysis.py --data_dir "EEG Recorded data"

echo.
echo Running Step 04...
python Scripts\04_harmonic_cca_ssvep_analysis.py --data_dir "EEG Recorded data"

echo.
echo Running Step 05...
python Scripts\05_permutation_sanity_check.py --data_dir "EEG Recorded data"

echo.
echo Done.
pause
