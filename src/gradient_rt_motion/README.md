# gradient-rt-motion (RTCore skeleton)

This directory contains the **RTCore** daemon for the RTOS/EtherCAT architecture:

- **Binary**: `gradient-rt-motion` (C++17, user-space)
- **EtherCAT master API** (planned): IgH `libecrt`
- **IPC**: Unix domain socket handshake + shared memory (see `RTOS-ETHERCAT-PLAN/RTOS-ETHERCAT-plan.md` §15.4)

This is the starting point for **Phase D/E** of `RTOS-ETHERCAT-PLAN/Plan overview & to-do.md`.

## Build (local)

### Option A: `make` (fastest)

```bash
cd src/gradient_rt_motion
make
```

### Option B: CMake

```bash
cd src/gradient_rt_motion
mkdir -p build
cd build
cmake ..
cmake --build . -j
```

The resulting binary will be at:

```bash
./build/gradient-rt-motion
```

## Run (dev)

During development you can override the IPC socket path:

```bash
./gradient-rt-motion --socket-path /tmp/gradient-rt-motion.sock
```

or (CMake build):

```bash
./build/gradient-rt-motion --socket-path /tmp/gradient-rt-motion.sock
```

Production default is `/run/gradient-rt-motion/ipc.sock` per the spec.

