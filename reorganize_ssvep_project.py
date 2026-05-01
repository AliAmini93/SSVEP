from pathlib import Path
import shutil
import re

PROJECT_DIR = Path.cwd()

FOLDERS = {
    "eeg": PROJECT_DIR / "EEG Recorded data",
    "data": PROJECT_DIR / "data",
    "scripts": PROJECT_DIR / "Scripts",
    "trigger_images": PROJECT_DIR / "trigger_images",
    "figures": PROJECT_DIR / "figures",
    "analysis": PROJECT_DIR / "_analysis_report",
}

THIS_SCRIPT = Path(__file__).resolve()


def make_folders():
    for folder in FOLDERS.values():
        folder.mkdir(exist_ok=True)


def safe_move(src: Path, dst_dir: Path):
    if not src.exists():
        return

    dst = dst_dir / src.name

    if src.resolve() == dst.resolve():
        return

    if dst.exists():
        print(f"[SKIP] Destination already exists: {dst}")
        return

    print(f"[MOVE] {src.name} -> {dst_dir.name}/")
    shutil.move(str(src), str(dst))


def move_files():
    # Move raw EEG HDF5 files
    for f in PROJECT_DIR.glob("*.hdf5"):
        safe_move(f, FOLDERS["eeg"])

    # Move Python scripts, except this reorganizer
    for f in PROJECT_DIR.glob("*.py"):
        if f.resolve() == THIS_SCRIPT:
            continue
        safe_move(f, FOLDERS["scripts"])

    # Move photodiode trigger images
    for name in ["ScreenTrigOn.png", "ScreenTrigOff.png"]:
        safe_move(PROJECT_DIR / name, FOLDERS["trigger_images"])

    # Move impedance figures
    for pattern in ["Impedance*.png", "impedance*.png"]:
        for f in PROJECT_DIR.glob(pattern):
            safe_move(f, FOLDERS["figures"])


def patch_psychopy_scripts():
    scripts_dir = FOLDERS["scripts"]

    for py_file in scripts_dir.glob("psychopy_ssvep*.py"):
        text = py_file.read_text(encoding="utf-8")

        original_text = text

        # Make sure project_dir exists after script_dir.
        if "project_dir = os.path.dirname(script_dir)" not in text:
            text = text.replace(
                "script_dir = os.path.dirname(os.path.abspath(__file__))",
                (
                    "script_dir = os.path.dirname(os.path.abspath(__file__))\n"
                    "project_dir = os.path.dirname(script_dir)"
                ),
            )

        # Redirect PsychoPy output data to ../data when script is inside Scripts/
        text = text.replace(
            "save_dir = os.path.join(os.getcwd(), 'data')",
            "save_dir = os.path.join(project_dir, 'data')",
        )

        # Redirect photodiode images to ../trigger_images/
        text = re.sub(
            r'trigger_on_path\s*=\s*os\.path\.join\(script_dir,\s*["\']ScreenTrigOn\.png["\']\)',
            'trigger_on_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOn.png")',
            text,
        )

        text = re.sub(
            r'trigger_off_path\s*=\s*os\.path\.join\(script_dir,\s*["\']ScreenTrigOff\.png["\']\)',
            'trigger_off_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOff.png")',
            text,
        )

        if text != original_text:
            py_file.write_text(text, encoding="utf-8")
            print(f"[PATCHED] {py_file.name}")
        else:
            print(f"[OK] No patch needed: {py_file.name}")


def write_run_analysis_bat():
    bat_path = PROJECT_DIR / "run_analysis_all.bat"

    content = r"""@echo off
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
"""

    if not bat_path.exists():
        bat_path.write_text(content, encoding="utf-8")
        print("[CREATED] run_analysis_all.bat")
    else:
        print("[SKIP] run_analysis_all.bat already exists")


def print_final_tree_hint():
    print("\nFinished reorganizing project.")
    print("\nRecommended commands:")
    print(r'cd /d "F:\KTU\Lithuania\Secondment Denmark\First SSVEP EEG Recording- Overt"')
    print(r'tree /F')
    print("\nTo run PsychoPy:")
    print(r'conda activate psychopy')
    print(r'python Scripts\psychopy_ssvep_pilot_V4.py')
    print("\nTo run the full analysis later:")
    print(r'conda activate base')
    print(r'run_analysis_all.bat')


def main():
    print(f"Project folder: {PROJECT_DIR}")
    make_folders()
    move_files()
    patch_psychopy_scripts()
    write_run_analysis_bat()
    print_final_tree_hint()


if __name__ == "__main__":
    main()