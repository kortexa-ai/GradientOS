## RTOS/EtherCAT bring-up (RevPi appliance)

This is the practical bring-up checklist for the RTOS/EtherCAT path described in:
- `RTOS-ETHERCAT-PLAN/RTOS-ETHERCAT-plan.md` (authoritative)

### CPU / RT assumptions (RevPi Connect 5)

- 4 physical cores
- Target partitioning:
  - **CPU0–CPU1**: housekeeping + non-RT helper work
  - **CPU2–CPU3**: RT cyclic loop + EtherCAT IRQ threads

### Phase A/B: Host prerequisites (scripts in-repo)

From the repo root:

```bash
cd systemd/ethercat-host
./install.sh
```

Optional but recommended (adds CPU isolation parameters to `/boot/firmware/cmdline.txt`):

```bash
cd systemd/ethercat-host
sudo ./rtos-apply-cmdline.sh
sudo reboot
```

After reboot, verify:

```bash
./scripts/ethercat/diagnose_host.sh
```

### Kernel headers (required to build IgH modules)

IgH includes kernel modules, so you need headers for the **running** RT kernel:

```bash
uname -r
ls -l "/lib/modules/$(uname -r)/build"
```

If missing, install the matching headers package (distro/vendor specific). Common attempts:

```bash
sudo apt-get update
sudo apt-get install -y "linux-headers-$(uname -r)"
```

On RevPi images, the header package name may differ; use `apt-cache search` on your configured repos.

### Phase C: Install IgH (EtherLab) master

IgH deliverables needed:
- kernel modules: `ec_master`, `ec_generic` (generic NIC binding)
- user-space: `libecrt` + `ethercat` CLI

Bind the master to the EtherCAT port by MAC in `/etc/ethercat.conf`:

```bash
sudo cat /etc/ethercat.conf
```

Expected:
- `MASTER0_DEVICE="c8:3e:a7:14:1c:76"`
- `DEVICE_MODULES="generic"`

After installation, verify:

```bash
ethercat slaves -v
ethercat pdos
ethercat dc
```

### Phase D+: RTCore + Python integration

- RTCore source: `src/gradient_rt_motion/` (binary: `gradient-rt-motion`)
- Python backend proxy: `src/gradient_os/arm_controller/backends/ethercat_rtcore/`

For the current **two-drive bring-up** (J3/J4 test), run RTCore with 2 axes:

```bash
cd src/gradient_rt_motion
make
sudo /usr/local/bin/gradient-rt-motion --num-axes 2
```

Axis scaling defaults (v1):
- `--counts-per-rev 131072`
- `--gear-ratio 1.0`
- `--sign +1`

Override as needed during commissioning, e.g.:

```bash
sudo /usr/local/bin/gradient-rt-motion --num-axes 2 --gear-ratio 100
```

The Python backend defaults to mapping those 2 RT axes to **joint 3 and joint 4**
(`GRADIENT_RTCORE_CONTROL_JOINTS="3,4"` is the explicit override).

