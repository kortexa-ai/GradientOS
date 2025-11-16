## GradientOS Telemetry Module

The telemetry module records synchronized robot state/actions and camera frames into episode folders designed for downstream training (e.g., LeRobot / OpenPI). It also provides utilities to publish state over UDP and to convert recorded episodes into a standardized dataset.

### Components

- **Recorder**: `record_episode.py`
  - Reads MJPEG frames from the vision server and saves images to `base/` and `wrist/` subfolders
  - Logs per-step metadata to `steps.jsonl` and run metadata to `metadata.json`
  - Writes a `recorder.log` with startup/connect/write diagnostics
- **MJPEG client**: `mjpeg.py`
  - Robust HTTP MJPEG reader with OpenCV/requests backends and automatic reconnect
- **UDP publisher**: `publisher.py`
  - Helper for streaming state/actions over UDP as JSON (used by the controller during recording)
- **Dataset converter**: `convert_to_lerobot.py`
  - Packs recorded episodes into a LeRobot-compatible dataset (optionally pushes to Hugging Face Hub)

#### Servo telemetry streamer: `servo_telemetry_stream.py`

Continuously reads servo telemetry via SYNC READ and writes a CSV, optionally publishing a JSON frame via UDP.

Usage:

```bash
python -m gradient_os.telemetry.servo_telemetry_stream --fps 10 --out servo_telemetry.csv --stdout
```

Options:
- `--ids 10,20,21,...`: Comma-separated servo IDs. Default: all configured and present (gripper excluded).
- `--include-gripper`: Include gripper (ID 100).
- `--fps N`: Sampling rate in Hz (default 10).
- `--out PATH`: Output CSV file (default `servo_telemetry.csv`).
- `--duration S`: Run for S seconds then exit (default: run until Ctrl-C).
- `--udp HOST:PORT`: Also publish per-frame JSON over UDP.
- `--stdout`: Print a compact summary to the console each frame.

CSV columns:
- `t`: timestamp (seconds, float)
- `id`: servo ID
- `pos_raw`: Current position (signed, steps)
- `speed_raw`: Current speed (signed, steps/s)
- `drive_duty_per_mille`: Current drive duty (0–1000)
- `voltage_v`: Input voltage (volts)
- `temp_c`: Internal temperature (°C)
- `status`: Hardware status flags (bitfield)
- `moving`: Moving status (0/1)
- `current_a`: Current (amps)
- `unloading_condition`: EEPROM bitfield at 0x13 (overload/overheat unload conditions)
- `led_alarm_condition`: EEPROM bitfield at 0x14 (LED-alarm trigger conditions)
- `unloading_hex`: Hex string form of 0x13
- `unloading_bits`: Comma list of set bits (e.g., `b0,b3`)
- `led_alarm_hex`: Hex string form of 0x14
- `led_alarm_bits`: Comma list of set bits (e.g., `b2,b5`)

Note: Bit names vary by firmware/datasheet revision. We expose which bits are set so you can post-map to specific meanings (e.g., overload, overheat, under/over-voltage). If you want named flags, we can add a mapping layer once you confirm the exact bit semantics for your STS firmware.

### How recording works (end-to-end)

1. The Controller starts the camera server via the Vision package:
   - `python -m gradient_os.vision mjpeg --both --width 640 --height 320 --fps 30 --no-overlay`
   - Dual endpoints are served at `/cam0.mjpg` and `/cam1.mjpg` when two cameras are present
2. The Controller launches the Recorder with cameras ON by default and without auto-start:
   - `python -m gradient_os.telemetry.record_episode --no-mjpeg-autostart --episodes-dir recorded_episodes --fps 10 --state-udp 0.0.0.0:5555`
3. The Recorder connects to MJPEG endpoints (defaults to `http://127.0.0.1:8080/cam0.mjpg` and `/cam1.mjpg`) and writes frames + JSONL rows at the requested FPS.

### Episode folder structure

Each episode is stored under `recorded_episodes/YYYYMMDD_HHMMSS/`:

- `base/` and `wrist/`: JPEG frames named `000000.jpg`, `000001.jpg`, ...
- `steps.jsonl`: one JSON object per step with timestamps and file references
- `metadata.json`: global recording metadata (fps, sizing, URLs, etc.)
- `recorder.log`: diagnostics (frame start, fallback decisions, write warnings)

Example `steps.jsonl` row:

```json
{
  "t": 1737730462.412,
  "base": "000123.jpg",
  "wrist": "000123.jpg",
  "state": {"t": 1737730462.411, "joints": [0.01, -1.40, 1.50, 0.00, 0.02, 0.00], "gripper": 25.8},
  "action": [0.0, 0.0, 0.05, 1.0, 1.0, 0.0, 0.0],
  "prompt": "pick up the pen and place it in the box"
}
```

### Defaults and sizing

- By default, the Recorder preserves the native frame size from the Vision server (no post-resize, no squish)
- Controller starts Vision at `640x320` (2:1) which is training-friendly; adjust in the controller if needed
- Optional Recorder resizing (disabled by default):
  - `--out-width W --out-height H` for aspect-preserving center-crop + resize
  - `--resize S` legacy square resize (avoid unless required)

### Dual-camera behavior

- When two cameras are available, Vision exposes `/cam0.mjpg` and `/cam1.mjpg` and Recorder writes `base/` and `wrist/`
- If only one camera is available, `base/` is populated and `wrist/` entries are `null` in `steps.jsonl`

### Overlays

- The Controller starts Vision with `--no-overlay`, so frames contain no AI/status text
- If you run Vision manually and see overlays, pass `--no-overlay` to suppress them

### Running from the UI (recommended)

- In the Control UI, leave Camera URL fields blank (auto)
- Ensure “Record Cameras” is checked (default ON)
- “Resize (0=native)” should be 0 to preserve camera output
- Click “Start Recorder” to create a new episode folder

### Running from the terminal

Start Vision (dual, 640x320, no overlays):

```bash
python -m gradient_os.vision mjpeg --both --width 640 --height 320 --fps 30 --no-overlay
```

Start Recorder (reads from localhost MJPEG by default):

```bash
python -m gradient_os.telemetry.record_episode --episodes-dir recorded_episodes --fps 10 --no-mjpeg-autostart
```

Provide explicit URLs if streaming from another host:

```bash
python -m gradient_os.telemetry.record_episode \
  --episodes-dir recorded_episodes \
  --base-cam http://mini-arm.local:8080/cam0.mjpg \
  --wrist-cam http://mini-arm.local:8080/cam1.mjpg \
  --fps 10 --no-mjpeg-autostart
```

Disable cameras (state-only):

```bash
python -m gradient_os.telemetry.record_episode --no-cameras --fps 10
```

### Converting to LeRobot

Install optional dependency once:

```bash
pip install lerobot
```

Convert recorded episodes. By default, images are NOT resized; pass `--image-size S` to enforce a square resize. The converter now also copies the dataset into a timestamped folder automatically (default root: `/converted_le_robot_datasets`, with a fallback to `~/converted_le_robot_datasets` if permissions fail):

```bash
python -m gradient_os.telemetry.convert_to_lerobot \
  --episodes-dir recorded_episodes \
  --repo-id yourname/miniarm \
  --fps 10 \
  # --image-size 256  # optional, only if you want square resize
```

This uses LeRobot’s dataset APIs to pack episodes. The local source dataset lives under `${HF_LEROBOT_HOME}/${repo_id}`. A copy is made to `/converted_le_robot_datasets/YYYY-MM-DD_HH-MM-SS/${repo_id}` (or `~/converted_le_robot_datasets/...` if root is not writable) and the final path is printed. See LeRobot for details and dataset tooling.

How to push privately to the Hub:

```bash
huggingface-cli login  # once

python -m gradient_os.telemetry.convert_to_lerobot \
  --episodes-dir recorded_episodes \
  --repo-id yourname/miniarm \
  --fps 10 \
  --push-to-hub  # uploads as private by default
```

### Troubleshooting

- **No images saved**: Check `recorder.log` for “camera frames started”; ensure Vision is running and URLs are correct
- **Squished images**: Set UI “Resize” to 0; rely on Vision `--width/--height` for sizing
- **“AI: OFF” overlay**: Ensure Vision is started with `--no-overlay`
- **Only base images**: Only one camera active; wrist will be `null`
- **Slow writes**: Use faster SD or reduce FPS or resolution in Vision

### Notes and references

- Designed for compatibility with LeRobot datasets (see `convert_to_lerobot.py`)
- Resolution/aspect choices influenced by recent training pipelines such as OpenPI (2:1 commonly used)


