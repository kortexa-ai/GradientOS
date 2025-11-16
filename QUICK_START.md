# Quick start

### Initial setup

Run the setup script and select what modules you want to install.

```bash
./setup.sh
```

This will install the required system packages and create a virtual environment.
It targets Python 3.14 (preferred). If 3.14 is unavailable on your system, the setup
will fall back to 3.11 automatically. You can force-create the venv with 3.14:

```bash
uv venv .venv --python python3.14
source ./.venv/bin/activate
uv pip install -e .[core]
```

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
uv run gradient-ui

# Run the web ui
./run-web.sh

```

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
