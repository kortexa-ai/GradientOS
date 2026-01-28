# Systemd Units

GradientOS ships helper units and scripts for running core services under systemd.
Both subdirectories include a `.service` file plus convenience scripts for
installing, removing, and managing the units.

- `controller/` – wraps `gradient-controller` via `run.sh`, intended for the
  robotic arm host (Raspberry Pi). Use:
  ```bash
  cd systemd/controller
  ./install.sh        # copies arm-controller.service into /etc/systemd/system
  ./status.sh         # inspect current state
  ./restart.sh        # restart the controller service
  ./stop.sh
  ./uninstall.sh
  ```
  Adjust the unit if you need custom environment variables (e.g. `SERIAL_PORT`).

- `api/` – runs `gradient-api` to expose the FastAPI REST/SSE proxy. Scripts are
  analogous:
  ```bash
  cd systemd/api
  ./install.sh
  ./status.sh
  ./restart.sh
  ./stop.sh
  ./uninstall.sh
  ```
  The service binds to `0.0.0.0:4000` by default and uses the project virtualenv.
  Override environment variables inside the unit if you host the controller on a
  different machine.

- `rt-motion/` – runs the **RTCore** (`gradient-rt-motion`) daemon that will own
  EtherCAT + the 1kHz cyclic loop (RTOS/EtherCAT architecture work). Use:
  ```bash
  cd systemd/rt-motion
  ./install.sh
  ./status.sh
  ./restart.sh
  ./stop.sh
  ./uninstall.sh
  ```
  Note: the unit is wired to `Requires=ethercat.service` (IgH master). Until
  IgH is installed/configured on the host, this service will not start.

- `ethercat-host/` – host-level EtherCAT prerequisites (NIC renaming, unmanaged
  `ethercat0`, NIC tuning + IRQ pinning templates). Use:
  ```bash
  cd systemd/ethercat-host
  ./install.sh
  ```
  This installs templates into `/etc` and enables the tuning units. A reboot is
  required for NIC renaming (`eth0/eth1` → `uplink0/ethercat0`).

After editing any service file, remember to re-run `sudo systemctl daemon-reload`
before restarting the unit.
