"""
Simple SSVEP pilot for PsychoPy Coder
-------------------------------------
What this script does:
- Presents two flickering targets (left and right)
- Uses a cue to tell the participant which target to attend
- Can run as a pure SSVEP setup test or with an optional dimming task
- Saves trial-wise behavioral and timing data to CSV
- Logs refresh-rate information and stimulus-only frame intervals
- Uses on-screen photodiode trigger images for EEG timing

Recommended first use:
1) Run with ENABLE_CATCH_TASK = False
2) Check that the measured refresh rate is stable
3) Inspect the timing summary and stimulus-only frame-interval log
4) Verify that the photodiode image is correctly aligned with the real sensor

Tested design assumptions:
- Best with a 60 Hz display
- Default frequencies: 10 Hz (left) and 15 Hz (right)
- Uses frame-based flicker, not time-based core.wait() flicker
"""

from psychopy import visual, core, event, gui, data, logging
import random
import os
import csv

# =========================
# USER SETTINGS
# =========================
FULLSCREEN = True
SCREEN_INDEX = 1
WINDOW_SIZE = [1280, 800]    # used only when FULLSCREEN = False
BACKGROUND = [-1, -1, -1]    # black in PsychoPy rgb space

LEFT_FREQ = 10               # Hz
RIGHT_FREQ = 15              # Hz
FIXATION_DUR = 1.0           # seconds
CUE_DUR = 0.8                # seconds
STIM_DUR = 3.0               # seconds
ITI_DUR = 1.2                # seconds

N_BLOCKS = 4
TRIALS_PER_BLOCK = 10

ENABLE_CATCH_TASK = False
CATCH_PROB = 0.30
DIM_DUR = 0.30
DIM_WINDOW_START = 0.80
DIM_WINDOW_END = 2.30
MIN_RESPONSE_RT = 0.15

LEFT_POS = (-320, 0)
RIGHT_POS = (320, 0)
STIM_SIZE = (220, 220)
TARGET_LINE_WIDTH = 4
CUE_LINE_WIDTH = 8
FIXATION_SIZE = 30
TEXT_HEIGHT = 28

ON_COLOR = [1, 1, 1]
OFF_COLOR = [-1, -1, -1]
DIM_COLOR = [-0.35, -0.35, -0.35]
NEUTRAL_OUTLINE = [0.3, 0.3, 0.3]
CUE_OUTLINE = [1, 1, -1]
FIXATION_COLOR = [1, 1, 1]
TEXT_COLOR = [1, 1, 1]

ESCAPE_KEY = 'escape'
DETECT_KEY = 'space'

# =========================
# PHOTODIODE IMAGE TRIGGER
# =========================
USE_PHOTODIODE_PATCH = True
PHOTODIODE_POS = (0.7, -0.4)   # exactly like the other experiment
PHOTODIODE_SIZE = 0.05         # exactly like the other experiment
PHOTODIODE_ON_FRAMES = 2       # image stays in ON state for first 2 frames of stimulation

# =========================
# HELPER FUNCTIONS
# =========================
def abort_experiment(win=None):
    """Gracefully close the experiment."""
    if win is not None:
        try:
            win.close()
        except Exception:
            pass
    core.quit()


def check_for_escape(win=None):
    keys = event.getKeys([ESCAPE_KEY])
    if ESCAPE_KEY in keys:
        abort_experiment(win)


def snap_refresh_rate(measured_hz):
    """Snap measured refresh to a common nominal refresh rate."""
    common_refresh_rates = [60, 75, 90, 100, 120, 144, 165, 240]
    for nominal in common_refresh_rates:
        if abs(measured_hz - nominal) <= 1.0:
            return nominal
    return int(round(measured_hz))


def compute_flicker_params(freq_hz, refresh_hz):
    """Return cycle length and ON frames for square-wave flicker.

    Requires refresh_hz / freq_hz to be an even integer so we can do
    symmetric ON/OFF periods.
    """
    cycle_frames = refresh_hz / float(freq_hz)
    rounded = round(cycle_frames)
    if abs(cycle_frames - rounded) > 1e-6:
        raise ValueError(
            f"Frequency {freq_hz} Hz is not frame-locked at {refresh_hz} Hz refresh."
        )
    cycle_frames = int(rounded)
    if cycle_frames % 2 != 0:
        raise ValueError(
            f"Frequency {freq_hz} Hz gives {cycle_frames} frames/cycle at {refresh_hz} Hz, "
            f"which cannot be split into equal ON/OFF halves."
        )
    on_frames = cycle_frames // 2
    return cycle_frames, on_frames


def draw_photodiode(trigger_state="off"):
    if USE_PHOTODIODE_PATCH:
        if trigger_state == "on":
            trigger_on.draw()
        else:
            trigger_off.draw()


def draw_with_trigger_single(stim, trigger_state="off"):
    stim.draw()
    draw_photodiode(trigger_state)


def draw_fixation(fixation):
    fixation.draw()
    draw_photodiode("off")


def draw_static_trial(left_rect, right_rect, fixation, left_outline, right_outline):
    left_rect.fillColor = OFF_COLOR
    right_rect.fillColor = OFF_COLOR
    left_rect.lineColor = left_outline
    right_rect.lineColor = right_outline
    left_rect.lineWidth = CUE_LINE_WIDTH if left_outline == CUE_OUTLINE else TARGET_LINE_WIDTH
    right_rect.lineWidth = CUE_LINE_WIDTH if right_outline == CUE_OUTLINE else TARGET_LINE_WIDTH
    left_rect.draw()
    right_rect.draw()
    fixation.draw()
    draw_photodiode("off")


def run_static_screen(win, duration_s, draw_callable):
    timer = core.Clock()
    while timer.getTime() < duration_s:
        check_for_escape(win)
        draw_callable()
        win.flip()


def make_block_trials(block_num):
    sides = ['left'] * (TRIALS_PER_BLOCK // 2) + ['right'] * (TRIALS_PER_BLOCK // 2)
    if len(sides) < TRIALS_PER_BLOCK:
        sides.append(random.choice(['left', 'right']))
    random.shuffle(sides)

    if ENABLE_CATCH_TASK:
        n_catch = max(1, int(round(TRIALS_PER_BLOCK * CATCH_PROB)))
        catch_flags = [True] * n_catch + [False] * (TRIALS_PER_BLOCK - n_catch)
        random.shuffle(catch_flags)
    else:
        catch_flags = [False] * TRIALS_PER_BLOCK

    trials = []
    for t in range(TRIALS_PER_BLOCK):
        attend_side = sides[t]
        catch_trial = catch_flags[t]
        dim_time = None
        if catch_trial:
            latest = min(DIM_WINDOW_END, STIM_DUR - DIM_DUR - 0.05)
            earliest = max(0.10, DIM_WINDOW_START)
            dim_time = random.uniform(earliest, latest)

        trials.append({
            'block': block_num,
            'trial_in_block': t + 1,
            'attend_side': attend_side,
            'target_freq': LEFT_FREQ if attend_side == 'left' else RIGHT_FREQ,
            'catch_trial': catch_trial,
            'dim_time_s': dim_time,
        })
    return trials


# =========================
# EXPERIMENT INFO
# =========================
exp_info = {
    'participant': '001',
    'session': '001',
}

dlg = gui.DlgFromDict(exp_info, title='Simple SSVEP Pilot')
if not dlg.OK:
    core.quit()

exp_info['date'] = data.getDateStr()
exp_name = 'simple_ssvep_pilot'

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
save_dir = os.path.join(project_dir, 'data')
os.makedirs(save_dir, exist_ok=True)

base_filename = os.path.join(
    save_dir,
    f"{exp_info['participant']}_{exp_info['session']}_{exp_info['date']}_{exp_name}"
)

trigger_on_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOn.png")
trigger_off_path = os.path.join(project_dir, "trigger_images", "ScreenTrigOff.png")

if USE_PHOTODIODE_PATCH:
    if not os.path.exists(trigger_on_path):
        raise FileNotFoundError(f"Could not find photodiode ON image: {trigger_on_path}")
    if not os.path.exists(trigger_off_path):
        raise FileNotFoundError(f"Could not find photodiode OFF image: {trigger_off_path}")

# =========================
# WINDOW AND TIMING SETUP
# =========================
logging.console.setLevel(logging.WARNING)

window_kwargs = {
    'fullscr': FULLSCREEN,
    'screen': SCREEN_INDEX,
    'color': BACKGROUND,
    'units': 'pix',
    'allowGUI': False,
}
if not FULLSCREEN:
    window_kwargs['size'] = WINDOW_SIZE

win = visual.Window(**window_kwargs)

measured_hz = win.getActualFrameRate(
    nIdentical=20,
    nMaxFrames=240,
    nWarmUpFrames=30,
    threshold=1,
)

if measured_hz is None:
    measured_hz = 60.0
    print('Warning: PsychoPy could not measure refresh rate reliably; assuming 60 Hz.')

# For this experiment, use a nominal 60 Hz design.
# The monitor may be measured as ~58.9–59.9 Hz, but the stimulus is designed for 60 Hz.
refresh_hz = 60

frame_duration = 1.0 / refresh_hz
win.recordFrameIntervals = False
win.refreshThreshold = frame_duration * 1.2

try:
    left_cycle_frames, left_on_frames = compute_flicker_params(LEFT_FREQ, refresh_hz)
    right_cycle_frames, right_on_frames = compute_flicker_params(RIGHT_FREQ, refresh_hz)
except ValueError as exc:
    win.close()
    raise SystemExit(
        f"Timing configuration error: {exc}\n"
        f"Tip: keep frequencies that divide the monitor refresh cleanly, e.g. 10 and 15 Hz on 60 Hz."
    )

# =========================
# TRIGGER STIMULI (PHOTODIODE)
# =========================
trigger_on = visual.ImageStim(
    win,
    image=trigger_on_path,
    pos=PHOTODIODE_POS,
    size=PHOTODIODE_SIZE,
    units="height"
)

trigger_off = visual.ImageStim(
    win,
    image=trigger_off_path,
    pos=PHOTODIODE_POS,
    size=PHOTODIODE_SIZE,
    units="height"
)

# =========================
# STIMULI
# =========================
fixation = visual.TextStim(
    win,
    text='+',
    color=FIXATION_COLOR,
    height=FIXATION_SIZE,
)

left_rect = visual.Rect(
    win,
    width=STIM_SIZE[0],
    height=STIM_SIZE[1],
    pos=LEFT_POS,
    fillColor=OFF_COLOR,
    lineColor=NEUTRAL_OUTLINE,
    lineWidth=TARGET_LINE_WIDTH,
)

right_rect = visual.Rect(
    win,
    width=STIM_SIZE[0],
    height=STIM_SIZE[1],
    pos=RIGHT_POS,
    fillColor=OFF_COLOR,
    lineColor=NEUTRAL_OUTLINE,
    lineWidth=TARGET_LINE_WIDTH,
)

instruction_lines = [
    'Simple SSVEP pilot',
    '',
    'Keep your eyes on the center cross.',
    'At the start of each trial, one side will be cued.',
    'During the flicker, attend to the cued side.',
]
if ENABLE_CATCH_TASK:
    instruction_lines.extend([
        'If that cued target briefly becomes dimmer, press SPACE.',
        'Do not press unless you really see the dimming.',
    ])
else:
    instruction_lines.extend([
        'No button press is needed in this version.',
        'Just attend to the cued side and stay still.',
    ])
instruction_lines.extend(['', 'Press SPACE to begin.'])

instruction_text = visual.TextStim(
    win,
    color=TEXT_COLOR,
    height=TEXT_HEIGHT,
    wrapWidth=1000,
    text='\n'.join(instruction_lines),
)

block_text = visual.TextStim(
    win,
    color=TEXT_COLOR,
    height=TEXT_HEIGHT,
    wrapWidth=1000,
)

status_text = visual.TextStim(
    win,
    color=TEXT_COLOR,
    height=22,
    pos=(0, -320),
)

end_text = visual.TextStim(
    win,
    color=TEXT_COLOR,
    height=TEXT_HEIGHT,
    wrapWidth=1000,
)

# =========================
# SAVE HEADER INFO
# =========================
meta_path = base_filename + '_meta.txt'
with open(meta_path, 'w', encoding='utf-8') as meta_file:
    meta_file.write(f"Experiment: {exp_name}\n")
    meta_file.write(f"Participant: {exp_info['participant']}\n")
    meta_file.write(f"Session: {exp_info['session']}\n")
    meta_file.write(f"Date: {exp_info['date']}\n")
    meta_file.write(f"Measured refresh rate: {measured_hz:.3f} Hz\n")
    meta_file.write(f"Rounded refresh rate used for flicker: {refresh_hz} Hz\n")
    meta_file.write(f"Expected frame duration: {frame_duration * 1000.0:.4f} ms\n")
    meta_file.write(f"Left frequency: {LEFT_FREQ} Hz ({left_cycle_frames} frames/cycle)\n")
    meta_file.write(f"Right frequency: {RIGHT_FREQ} Hz ({right_cycle_frames} frames/cycle)\n")
    meta_file.write(f"Fullscreen: {FULLSCREEN}\n")
    meta_file.write(f"Catch task enabled: {ENABLE_CATCH_TASK}\n")
    meta_file.write(f"Photodiode patch enabled: {USE_PHOTODIODE_PATCH}\n")
    meta_file.write(f"Photodiode ON image: {trigger_on_path}\n")
    meta_file.write(f"Photodiode OFF image: {trigger_off_path}\n")
    meta_file.write(f"Photodiode position: {PHOTODIODE_POS}\n")
    meta_file.write(f"Photodiode size: {PHOTODIODE_SIZE}\n")
    meta_file.write(f"Photodiode on frames: {PHOTODIODE_ON_FRAMES}\n")

# =========================
# BEHAVIOR DATA FILE
# =========================
behav_path = base_filename + '_trials.csv'
fieldnames = [
    'participant', 'session', 'date',
    'block', 'trial_in_block',
    'attend_side', 'target_freq',
    'catch_trial', 'dim_time_s',
    'response_key', 'response_rt_s',
    'hit', 'miss', 'false_alarm', 'anticipatory_response',
    'stim_onset_global_s',
    'photodiode_used',
    'photodiode_on_frames',
    'dropped_frames_trial',
    'n_frame_intervals_trial',
    'max_frame_interval_ms_trial',
    'mean_frame_interval_ms_trial',
    'measured_refresh_hz',
]

behav_file = open(behav_path, 'w', newline='', encoding='utf-8')
writer = csv.DictWriter(behav_file, fieldnames=fieldnames)
writer.writeheader()

# =========================
# START SCREEN
# =========================
instruction_text.draw()
draw_photodiode("off")
status_text.text = f"Measured refresh rate: {measured_hz:.2f} Hz (using {refresh_hz} Hz)"
status_text.draw()
win.flip()

event.clearEvents()
while True:
    keys = event.getKeys([DETECT_KEY, ESCAPE_KEY])
    if ESCAPE_KEY in keys:
        behav_file.close()
        abort_experiment(win)
    if DETECT_KEY in keys:
        break

# =========================
# MAIN EXPERIMENT
# =========================
global_clock = core.Clock()
stim_frame_intervals_ms = []
stim_dropped_frames_total = 0
stim_trials_with_drops = 0

all_trials = []
for block_num in range(1, N_BLOCKS + 1):
    all_trials.extend(make_block_trials(block_num))

for block_num in range(1, N_BLOCKS + 1):
    block_trials = [t for t in all_trials if t['block'] == block_num]

    if ENABLE_CATCH_TASK:
        block_text.text = (
            f"Block {block_num} / {N_BLOCKS}\n\n"
            f"Attend to the cued target.\n"
            f"Press SPACE only if the cued target briefly dims.\n\n"
            f"Press SPACE to start this block."
        )
    else:
        block_text.text = (
            f"Block {block_num} / {N_BLOCKS}\n\n"
            f"Attend to the cued target and keep still.\n"
            f"No button press is needed in this version.\n\n"
            f"Press SPACE to start this block."
        )
    block_text.draw()
    draw_photodiode("off")
    win.flip()

    event.clearEvents()
    while True:
        keys = event.getKeys([DETECT_KEY, ESCAPE_KEY])
        if ESCAPE_KEY in keys:
            behav_file.close()
            abort_experiment(win)
        if DETECT_KEY in keys:
            break

    draw_with_trigger_single(fixation, "off")
    win.flip()

    draw_with_trigger_single(fixation, "off")
    win.flip()

    for trial in block_trials:
        attend_side = trial['attend_side']
        catch_trial = trial['catch_trial'] if ENABLE_CATCH_TASK else False
        dim_time_s = trial['dim_time_s'] if ENABLE_CATCH_TASK else None

        dim_start_frame = None
        dim_end_frame = None
        if catch_trial and dim_time_s is not None:
            dim_start_frame = int(round(dim_time_s * refresh_hz))
            dim_end_frame = dim_start_frame + int(round(DIM_DUR * refresh_hz))

        # Fixation screen
        run_static_screen(win, FIXATION_DUR, lambda: draw_fixation(fixation))

        # Cue screen
        if attend_side == 'left':
            run_static_screen(
                win,
                CUE_DUR,
                lambda: draw_static_trial(
                    left_rect, right_rect, fixation,
                    CUE_OUTLINE, NEUTRAL_OUTLINE,
                ),
            )
        else:
            run_static_screen(
                win,
                CUE_DUR,
                lambda: draw_static_trial(
                    left_rect, right_rect, fixation,
                    NEUTRAL_OUTLINE, CUE_OUTLINE,
                ),
            )

        # Stimulation period
        total_frames = int(round(STIM_DUR * refresh_hz))
        response_key = ''
        response_rt = ''
        hit = 0
        miss = 0
        false_alarm = 0
        anticipatory_response = 0
        response_recorded = False
        event.clearEvents()
        stim_clock = core.Clock()
        dropped_before = win.nDroppedFrames
        stim_onset_global_s = ''

        win.frameIntervals = []
        win.recordFrameIntervals = True

        for frameN in range(total_frames):
            check_for_escape(win)

            left_on = (frameN % left_cycle_frames) < left_on_frames
            right_on = (frameN % right_cycle_frames) < right_on_frames

            left_fill = ON_COLOR if left_on else OFF_COLOR
            right_fill = ON_COLOR if right_on else OFF_COLOR

            if catch_trial and dim_start_frame is not None and dim_end_frame is not None:
                if dim_start_frame <= frameN < dim_end_frame:
                    if attend_side == 'left' and left_on:
                        left_fill = DIM_COLOR
                    elif attend_side == 'right' and right_on:
                        right_fill = DIM_COLOR

            left_rect.fillColor = left_fill
            right_rect.fillColor = right_fill
            left_rect.lineColor = NEUTRAL_OUTLINE
            right_rect.lineColor = NEUTRAL_OUTLINE
            left_rect.lineWidth = TARGET_LINE_WIDTH
            right_rect.lineWidth = TARGET_LINE_WIDTH

            left_rect.draw()
            right_rect.draw()
            fixation.draw()

            if USE_PHOTODIODE_PATCH and frameN < PHOTODIODE_ON_FRAMES:
                draw_photodiode("on")
            else:
                draw_photodiode("off")

            win.flip()

            if frameN == 0:
                stim_clock.reset()
                stim_onset_global_s = f"{global_clock.getTime():.6f}"

            if ENABLE_CATCH_TASK:
                keys = event.getKeys([DETECT_KEY, ESCAPE_KEY], timeStamped=stim_clock)
            else:
                keys = event.getKeys([ESCAPE_KEY], timeStamped=stim_clock)

            for key, rt in keys:
                if key == ESCAPE_KEY:
                    behav_file.close()
                    abort_experiment(win)
                if ENABLE_CATCH_TASK and key == DETECT_KEY and not response_recorded:
                    response_key = key
                    response_rt = f"{rt:.6f}"
                    response_recorded = True

                    if rt < MIN_RESPONSE_RT:
                        anticipatory_response = 1
                    elif catch_trial and dim_time_s is not None and rt >= dim_time_s:
                        hit = 1
                    else:
                        false_alarm = 1

        win.recordFrameIntervals = False
        dropped_after = win.nDroppedFrames
        dropped_this_trial = dropped_after - dropped_before
        if dropped_this_trial > 0:
            stim_trials_with_drops += 1
        stim_dropped_frames_total += dropped_this_trial

        trial_intervals_ms = [interval * 1000.0 for interval in win.frameIntervals]
        stim_frame_intervals_ms.extend(trial_intervals_ms)
        n_frame_intervals_trial = len(trial_intervals_ms)
        max_frame_interval_ms_trial = max(trial_intervals_ms) if trial_intervals_ms else 0.0
        mean_frame_interval_ms_trial = (
            sum(trial_intervals_ms) / len(trial_intervals_ms)
            if trial_intervals_ms else 0.0
        )

        if ENABLE_CATCH_TASK and catch_trial and not response_recorded:
            miss = 1

        # ITI
        run_static_screen(
            win,
            ITI_DUR,
            lambda: draw_static_trial(
                left_rect, right_rect, fixation,
                NEUTRAL_OUTLINE, NEUTRAL_OUTLINE,
            ),
        )

        writer.writerow({
            'participant': exp_info['participant'],
            'session': exp_info['session'],
            'date': exp_info['date'],
            'block': block_num,
            'trial_in_block': trial['trial_in_block'],
            'attend_side': attend_side,
            'target_freq': trial['target_freq'],
            'catch_trial': int(catch_trial),
            'dim_time_s': '' if dim_time_s is None else f"{dim_time_s:.6f}",
            'response_key': response_key,
            'response_rt_s': response_rt,
            'hit': hit,
            'miss': miss,
            'false_alarm': false_alarm,
            'anticipatory_response': anticipatory_response,
            'stim_onset_global_s': stim_onset_global_s,
            'photodiode_used': int(USE_PHOTODIODE_PATCH),
            'photodiode_on_frames': PHOTODIODE_ON_FRAMES,
            'dropped_frames_trial': dropped_this_trial,
            'n_frame_intervals_trial': n_frame_intervals_trial,
            'max_frame_interval_ms_trial': f"{max_frame_interval_ms_trial:.6f}",
            'mean_frame_interval_ms_trial': f"{mean_frame_interval_ms_trial:.6f}",
            'measured_refresh_hz': f"{measured_hz:.3f}",
        })
        behav_file.flush()

    if block_num < N_BLOCKS:
        if ENABLE_CATCH_TASK:
            break_msg = (
                'Take a short break.\n\n'
                'Try to blink and rest your eyes now.\n'
                'Remember: only press SPACE when you really see dimming.\n\n'
                'Press SPACE when you are ready for the next block.'
            )
        else:
            break_msg = (
                'Take a short break.\n\n'
                'Try to blink and rest your eyes now.\n\n'
                'Press SPACE when you are ready for the next block.'
            )
        block_text.text = break_msg
        block_text.draw()
        draw_photodiode("off")
        win.flip()

        event.clearEvents()
        while True:
            keys = event.getKeys([DETECT_KEY, ESCAPE_KEY])
            if ESCAPE_KEY in keys:
                behav_file.close()
                abort_experiment(win)
            if DETECT_KEY in keys:
                break

# =========================
# END OF EXPERIMENT
# =========================
frame_log_path = base_filename + '_frameIntervals_ms.txt'
with open(frame_log_path, 'w', encoding='utf-8') as frame_file:
    frame_file.write('frame_interval_ms\n')
    for interval_ms in stim_frame_intervals_ms:
        frame_file.write(f"{interval_ms:.6f}\n")

threshold_ms = win.refreshThreshold * 1000.0
if stim_frame_intervals_ms:
    mean_interval_ms = sum(stim_frame_intervals_ms) / len(stim_frame_intervals_ms)
    min_interval_ms = min(stim_frame_intervals_ms)
    max_interval_ms = max(stim_frame_intervals_ms)
    n_over_threshold = sum(1 for x in stim_frame_intervals_ms if x > threshold_ms)
else:
    mean_interval_ms = 0.0
    min_interval_ms = 0.0
    max_interval_ms = 0.0
    n_over_threshold = 0

timing_summary_path = base_filename + '_timingSummary.txt'
with open(timing_summary_path, 'w', encoding='utf-8') as summary_file:
    summary_file.write(f"Stim-only frame intervals collected: {len(stim_frame_intervals_ms)}\n")
    summary_file.write(f"Expected frame duration: {frame_duration * 1000.0:.6f} ms\n")
    summary_file.write(f"Refresh threshold used by PsychoPy: {threshold_ms:.6f} ms\n")
    summary_file.write(f"Mean frame interval: {mean_interval_ms:.6f} ms\n")
    summary_file.write(f"Min frame interval: {min_interval_ms:.6f} ms\n")
    summary_file.write(f"Max frame interval: {max_interval_ms:.6f} ms\n")
    summary_file.write(f"Stim-only dropped frames total: {stim_dropped_frames_total}\n")
    summary_file.write(f"Trials with dropped frames: {stim_trials_with_drops}\n")
    summary_file.write(f"Intervals over threshold: {n_over_threshold}\n")

end_text.text = (
    'Finished.\n\n'
    f'Stim-only dropped frames: {stim_dropped_frames_total}\n'
    f'Trials with dropped frames: {stim_trials_with_drops}\n'
    f'Total PsychoPy dropped frames (whole run): {win.nDroppedFrames}\n\n'
    'Press SPACE to close.'
)
end_text.draw()
draw_photodiode("off")
win.flip()

while True:
    keys = event.getKeys([DETECT_KEY, ESCAPE_KEY])
    if ESCAPE_KEY in keys or DETECT_KEY in keys:
        break

behav_file.close()
win.close()
core.quit()