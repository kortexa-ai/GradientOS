# UI Setup and Running Guide for mini-arm Project

This guide explains how to set up and run the UI (`ui_start.py`) on a Raspberry Pi 5. The UI uses PySide6 for the interface and pyqtgraph for 3D simulation.

## Prerequisites
- Raspberry Pi 5 with Raspberry Pi OS (64-bit recommended).
- Python 3.11+ installed.
- Virtual environment (.venv) in the project root.

## Installation
1. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```

2. Install GradientOS (installs the required Python packages):
   ```bash
   pip install -e .
   ```

3. For OpenGL support (required for simulation page):
   ```bash
   sudo apt-get update && sudo apt-get install -y libgl1-mesa-glx libgl1-mesa-dri mesa-utils
   ```
   - After installation, reboot: `sudo reboot`.
   - Verify OpenGL: `glxinfo | grep 'OpenGL renderer'` (should show hardware renderer like 'VC4 V3D').

## Running the UI
1. Ensure venv is activated.
2. Run the script:
   ```bash
   python ui_start.py
   ```

## Troubleshooting
- **UI hangs or OpenGL warnings**: Increase GPU memory in `sudo raspi-config` > Performance Options > GPU Memory (set to 128MB or higher). Reboot.
- **QOpenGLWidget not supported**: Ensure Mesa packages are installed and system is rebooted.
- **Deprecation warnings**: The code uses app.exec() to avoid issues.
- If simulation page causes issues, comment out pyqtgraph.opengl usage in the code.

### No window appears (Jetson / SSH / headless)
- **Check display environment** (run these inside your activated venv):
  ```bash
  echo "DISPLAY=${DISPLAY}"
  echo "XDG_SESSION_TYPE=${XDG_SESSION_TYPE}"
  echo "QT_QPA_PLATFORM=${QT_QPA_PLATFORM}"
  ```
- **If you are SSH’d in without X forwarding**, a GUI will not be shown. Either:
  - Log into the device’s desktop session and run the UI locally, or
  - Use X forwarding:
    ```bash
    ssh -Y username@DEVICE_HOSTNAME
    ```
    Then run the UI:
    ```bash
    gradient-ui --debug-ui
    ```
- **Enable detailed Qt plugin logs** to diagnose platform plugin issues:
  ```bash
  export QT_DEBUG_PLUGINS=1
  gradient-ui --debug-ui
  ```
- **Enable Gradient UI diagnostics** without changing your command:
  ```bash
  export GRADIENT_UI_DEBUG=1
  gradient-ui
  ```
- **Verify a screen is available to Qt**. If logs show "Screens detected: 0", there is no display for Qt to render to.
- **Wayland vs X11**: If on Wayland and issues persist, try forcing XCB:
  ```bash
  export QT_QPA_PLATFORM=xcb
  gradient-ui --debug-ui
  ```
- **Jetson-specific**: Ensure desktop packages and OpenGL are installed and a compositor is running. You can test GUI forwarding with a simple app like:
  ```bash
  xclock
  ```

### Qt xcb platform dependencies (Ubuntu/Jetson)
If logs say "Could not load the Qt platform plugin xcb" or complain about `libxcb-cursor.so.0`, install these system packages:
```bash
sudo apt-get update
sudo apt-get install -y \
  libxcb-cursor0 \
  libxkbcommon-x11-0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-xinerama0 \
  libxcb-randr0 \
  libxcb-shape0 \
  libxcb-xfixes0 \
  libxcb-glx0 \
  libxcb-util1 \
  libxrender1 \
  libxi6
```
Then re-run:
```bash
unset QT_QPA_PLATFORM
export GRADIENT_UI_DEBUG=1
gradient-ui --debug-ui
```

### Stopping the UI from a terminal
- If started in the foreground, press:
  - `Ctrl+C` (now handled to quit gracefully), or
  - `Alt+F4` in the window.
- If Ctrl+C does not work for any reason:
  ```bash
  pkill -f "gradient-ui"
  # or, if needed, find the PID and terminate:
  pgrep -f "ui_start.py|gradient-ui"
  kill -TERM <PID>
  # as a last resort:
  kill -KILL <PID>
  ```

This setup provides a functional UI for robot control. Report issues in the repo. 

## Performance notes (Raspberry Pi)
- The UI no longer imports OpenGL on startup. The `pyqtgraph.opengl` import was removed from `src/gradient_os/ui_start.py` to avoid slow and fragile OpenGL initialization on headless or low-power systems. If a future simulation view is added, load OpenGL lazily within that feature only.
- Trajectory list refresh is now asynchronous. `RealControlPage.refresh_trajectory_list` sends `GET_TRAJECTORIES` and relies on the UI dispatcher to populate the list when the response arrives. This avoids blocking the UI thread for up to 3 seconds while waiting for UDP responses.