---
description: "Hard rules for NIC naming, EtherCAT port behavior, and IgH master binding/order."
alwaysApply: false
---

## NIC naming + binding (must follow)

- Use `systemd.link` files to rename by MAC:
  - `ethercat0` MUST match `c8:3e:a7:14:1c:76`
  - `uplink0` MUST match `c8:3e:a7:14:1c:75`

## EtherCAT port (ethercat0) constraints

- `ethercat0` must be **unmanaged** by NetworkManager.
- `ethercat0` must have **no IP address**, no DHCP, no routes/firewall/NAT/bridge/VLAN.
- `ethercat0` must be brought UP at boot (link up).

## IgH master constraints

- IgH includes kernel modules; build/install it **against the running RT kernel headers**.
- Bind IgH master by MAC in `/etc/ethercat.conf`:
  - `MASTER0_DEVICE="c8:3e:a7:14:1c:76"`
  - `DEVICE_MODULES="generic"`

## Service ordering (systemd)

Boot order must be:
1. NIC renaming (`ethercat0/uplink0`)
2. NIC tuning + link up (`ethercat0`)
3. IgH master modules loaded/bound (`ethercat.service`)
4. RTCore starts (`gradient-rt-motion.service`) and **Requires/After** `ethercat.service`

If `ethercat.service` fails, RTCore must not start.
