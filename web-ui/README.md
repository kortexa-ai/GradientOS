# GradientOS Web UI

Production-facing React/TypeScript operator interface for GradientOS.

The app provides:

- live arm visualization in a 3D scene
- telemetry and controller alerts
- trajectory preview and execution controls
- STEP topology loading and weld planning tools
- Program Tree inspection/editing for planned motion

## Prerequisites

- Node.js 18+ and npm
- `gradient-api` running and reachable (default `http://localhost:4000`)
- controller/simulator running if you want live execution

## Install

```bash
cd web-ui
npm install
```

## Scripts

- `npm run dev` - start Vite dev server (default port `8000`)
- `npm run build` - production build
- `npm run preview` - serve the production build locally

## Run (Local)

1. Start backend services from repo root:
   - `./run-sim.sh` and `./run-api.sh` (or PowerShell `.ps1` variants)
2. Start UI:

```bash
cd web-ui
npm run dev
```

3. Open `http://localhost:8000`
4. Confirm API host, then click **Connect**

## Feature Overview

### Scene + Telemetry

- 3D arm, workcell overlays, and path rendering
- SSE telemetry via `/monitor`
- weld-active and alert overlays

### Trajectory Planning

- point-based preview planning
- execute planned preview
- recorded trajectory load/run flows

### Weld Planning

- STEP topology edge selection
- per-segment weld configuration
- work/travel angles and transition clearance
- post-actions (`none`, `lift`, `return_to_start`)

### Program Tree

- exact execution path sample inspection (no low-resolution trim view)
- control-point editing from Program Tree context
- apply edits back into planner flow

## Operational Notes

- Weld run flow refreshes preview planning before execution to capture current pre-run robot state.
- `return_to_start` targets the trajectory start pose captured at run time.
- Runtime execution uses stability guards to avoid sub-step state races during weld playback.

## Build Check

Before merging UI changes, run:

```bash
npm run build
```
