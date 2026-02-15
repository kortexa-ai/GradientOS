# Quick start

### Agent workflow pointers

To keep implementation quality and session continuity high, maintain these repo-local files:

- `DEVLOG.md` - chronological engineering timeline (what changed, validation, risks).
- `AGENT_SCRATCHPAD.md` - persistent execution memory (mistakes, preferences, guardrails).
- `.cursor/skills/` - local skills and reference templates used during implementation.

### Initial setup

Run the setup script and select what modules you want to install.

```bash
./setup.sh
```

This will install the required system packages and create a virtual environment.
It targets Python 3.12 (preferred) for broad wheel compatibility.
If 3.12 is unavailable, setup falls back to 3.11, then 3.14.
Use a single repo-local virtualenv at `.venv` (the same one used by `start.sh`).
You can force-create the venv with 3.12:

```bash
uv venv .venv --python python3.12
source ./.venv/bin/activate
uv pip install -e .[core]
```

### EtherCAT on RevPi Connect 5 (important port note)

If you're bringing up the **RTOS/EtherCAT** path on a **RevPi Connect 5**, pay attention to which RJ45
port you use for the EtherCAT drive chain.

- **Both ports are “gigabit”, but they are different NICs/drivers**:
  - **`eth0`**: Linux driver **`macb`** (SoC MAC) → **use this for EtherCAT** (stable with IgH `ec_generic` in our bring-up)
  - **`eth1`**: Linux driver **`lan743x`** (PCI NIC) → use this for LAN/uplink
- **Why**: during bring-up we consistently saw slave discovery work on `macb` (`eth0`) and fail on `lan743x` (`eth1`)
  (Tx-only, Rx=0, 100% loss) despite Link=UP and tuning.

How to verify on the RevPi:

```bash
sudo ethtool -i eth0
sudo ethtool -i eth1
sudo ethercat master  # check Rx frames > 0 and Slaves > 0
```

Example output (shows SoC vs PCI NIC):

```bash
$ sudo ethtool -i eth0
driver: macb
bus-info: 1f00100000.ethernet

$ sudo ethtool -i eth1
driver: lan743x
bus-info: 0001:03:00.0
```

More details + IgH notes: `docs/ethercat/bringup.md` and `docs/ethercat/igh.md`.

### Run the components

All commands below automatically activate the venv
You can also activate manually if you want to run other scripts or tests

```bash
# Run controller, wait to confirm it connected to the arm
./run.sh

# Alternatively, if your servo burned out, you can use the built-in servo sim
./run-sim.sh

# Run the api
./run-api.sh

# Optionally, run the vision
./run-vision.sh

# Run the control UI (will be superseded by the web ui soon)
# to control the robot arm
gradient-ui

# Run the web ui
./run-web.sh

```

On Windows PowerShell, use the `.ps1` launcher variants (same behavior):

```powershell
# From repository root
.\.venv\Scripts\Activate.ps1

# Terminal 1: controller in simulator mode
.\run-sim.ps1

# Terminal 2: API service
.\run-api.ps1
```

If you want to invoke the existing bash launchers directly on Windows,
run them through a bash shell (`bash ./run-sim.sh` / `bash ./run-api.sh`) or use WSL/Git Bash.

The web UI should be available at http://localhost:8000

#### Controller alerts in the Web UI

- When the controller detects servo communication issues or status errors (for example: no SyncRead reply from certain servo IDs, or a servo status byte like 32), these are now forwarded to the API telemetry stream and shown in the web UI as alerts on the right side.
- Typical messages include a human-readable cause, e.g. “Servo 30 reported: Position Fault” or “No feedback from servos 30, 31 (SyncRead). Check power/wiring/baud.”
- If you do not see alerts but the terminal shows errors, ensure the API is running and the UI is connected to `/monitor`.

### Performance profiling

The loop benchmarking utilities now live under `scripts/`:

```bash
python scripts/performance_tester.py     # creates scripts/performance_log.csv
python scripts/chart_generator.py        # reads the CSV and saves scripts/performance_charts.png
```

### Distributed setup

Clone the repo on the different machines and run the setup script.
Then run only the specific components you want. Don't forget to use the command line arguments to point to the right ports and addresses for their dependencies.

# Manual setup

A quick checklist to bring up the development environment manually on Raspberry Pi or any Debian-based host. For detailed guides, see the documentation links at the end.

1. Install system packages (camera + OpenGL + libcap):

2. Create a dedicated Python virtual environment with `uv`:

    ```bash
    uv venv .venv
    ```

3. Activate the environment (required for the next steps and CLI aliases):

    ```bash
    source .venv/bin/activate
    # or: source ./start.sh  # adds project-specific PYTHONPATH/aliases
    ```

4. Install GradientOS (builds the IK solver extension and Python deps):
    ```bash
    uv pip install -e .
    ```

Optional extras:

-   Vision AI stack (YOLO + Torch): `uv pip install -e '.[ai]'`
-   Dataset tooling (LeRobot export helpers): `uv pip install -e '.[datasets]'`
-   Dev/test utilities (pytest, pre-commit): `uv pip install -e '.[dev]'`

Next steps:

-   UI setup & troubleshooting: `docs/UI_readme.md`
-   Vision module usage: `src/gradient_os/vision/README.md`
-   Full project docs & command references: `docs/README.md`
