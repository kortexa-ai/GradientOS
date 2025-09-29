from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import cv2
import numpy as np
from datetime import datetime
import shutil
import argparse
import pandas as pd
from gradient_os.telemetry.verify_lerobot import verify as verify_lerobot_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert recorded episodes to a LeRobot dataset.")
    parser.add_argument("--episodes-dir", default="recorded_episodes", help="Directory containing recorded episodes")
    # Dataset name for the output folder. If omitted, derived from episodes-dir name.
    parser.add_argument("--dataset-name", default=None, help="Name for the output dataset folder (default: basename of episodes-dir)")
    # Deprecated alias for dataset-name, kept for compatibility
    parser.add_argument("--repo-id", default=None, help="[Deprecated] Alias of --dataset-name; no Hugging Face is used")
    parser.add_argument("--fps", type=int, default=10, help="Target frames per second in the dataset")
    parser.add_argument("--image-size", type=int, default=None, help="Optional square resize. If omitted, keep native size.")
    parser.add_argument("--output-dir", default="converted_le_robot_datasets", help="Root folder (relative or absolute) to write the timestamped dataset into")
    parser.add_argument("--no-videos", action="store_true", help="Skip writing MP4 preview videos in the local builder")
    return parser.parse_args()


def _read_rgb(path: Optional[Path], target_size: Optional[int]) -> np.ndarray:
    if not path or not path.exists():
        # No image available: return a minimal placeholder when no resize is requested
        if target_size and target_size > 0:
            return np.zeros((target_size, target_size, 3), dtype=np.uint8)
        return np.zeros((1, 1, 3), dtype=np.uint8)
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        if target_size and target_size > 0:
            return np.zeros((target_size, target_size, 3), dtype=np.uint8)
        return np.zeros((1, 1, 3), dtype=np.uint8)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if target_size and target_size > 0 and rgb.shape[:2] != (target_size, target_size):
        rgb = cv2.resize(rgb, (target_size, target_size), interpolation=cv2.INTER_AREA)
    return rgb


def _write_video_opencv(
    output_path: Path,
    frame_paths: List[Path],
    fps: int,
    progress_prefix: Optional[str] = None,
    target_size: Optional[int] = None,
) -> tuple:
    valid_frames: List[np.ndarray] = []
    for p in frame_paths:
        if not p or not p.exists():
            continue
        bgr = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if bgr is None:
            continue
        valid_frames.append(bgr)
    if not valid_frames:
        valid_frames = [np.zeros((1, 1, 3), dtype=np.uint8)]
    height, width = valid_frames[0].shape[:2]
    if target_size and target_size > 0:
        height = width = int(target_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, float(fps), (width, height))
    if not writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"avc1")
        writer = cv2.VideoWriter(str(output_path), fourcc, float(fps), (width, height))
    total = len(valid_frames)
    step = max(1, total // 50)  # at most ~50 updates
    for i, frame in enumerate(valid_frames, start=1):
        if frame.shape[0] != height or frame.shape[1] != width:
            frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
        writer.write(frame)
        if progress_prefix is not None and (i % step == 0 or i == total):
            _print_progress(i, total, prefix=progress_prefix)
    writer.release()
    return (height, width)


def _pad_or_trim(arr: np.ndarray, size: int) -> np.ndarray:
    if arr.ndim == 0:
        arr = arr[None]
    if arr.shape[0] < size:
        arr = np.pad(arr, (0, size - arr.shape[0]))
    if arr.shape[0] > size:
        arr = arr[:size]
    return arr


def _print_progress(current: int, total: int, prefix: str = "") -> None:
    try:
        total = max(1, int(total))
        current = min(max(0, int(current)), total)
        width = 30
        filled = int(width * current // total)
        bar = "#" * filled + "-" * (width - filled)
        pct = (100.0 * current) / float(total)
        msg = f"\r{prefix} [{bar}] {current}/{total} ({pct:5.1f}%)"
        print(msg, end="", flush=True)
        if current >= total:
            print("")
    except Exception:
        # Fallback to simple line if terminal does not support carriage return
        print(f"{prefix} {current}/{total}")


def _build_v21_locally(
    episodes_root: Path,
    export_root: Path,
    dataset_name: str,
    fps: int,
    target_size: Optional[int],
    no_videos: bool,
) -> Path:
    """Build a minimal LeRobot v2.1 dataset layout without importing lerobot.

    Writes:
      - data/chunk-000/episode_XXXXXX.parquet
      - videos/chunk-000/observation.images.main/episode_XXXXXX.mp4
      - videos/chunk-000/observation.images.secondary_0/episode_XXXXXX.mp4
      - meta/info.json, meta/episodes.jsonl, meta/tasks.jsonl, meta/episodes_stats.jsonl
    """
    try:
        import pyarrow  # noqa: F401  # ensure parquet engine available
    except Exception as e:
        raise RuntimeError("Local builder requires 'pyarrow' to write Parquet. Please install pyarrow or install lerobot.") from e

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Resolve dataset directory and ensure we can create it. Fall back to home if needed.
    try:
        dataset_dir = (export_root if export_root.is_absolute() else Path.cwd() / export_root) / timestamp / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        home_root = Path.cwd() / "converted_le_robot_datasets"
        dataset_dir = home_root / timestamp / dataset_name
        dataset_dir.mkdir(parents=True, exist_ok=True)
        print(f"Permission denied at '{export_root}'. Falling back to: {dataset_dir}")
    data_dir = dataset_dir / "data" / "chunk-000"
    video_main_dir = dataset_dir / "videos" / "chunk-000" / "observation.images.main"
    video_wrist_dir = dataset_dir / "videos" / "chunk-000" / "observation.images.secondary_0"
    meta_dir = dataset_dir / "meta"
    for d in [data_dir, video_main_dir, video_wrist_dir, meta_dir]:
        d.mkdir(parents=True, exist_ok=True)

    tasks_to_index: Dict[str, int] = {}
    next_task_index = 0
    episodes_meta: List[Dict[str, Any]] = []
    episodes_stats_lines: List[Dict[str, Any]] = []

    # Gather eligible episode directories
    episode_dirs: List[Path] = []
    for p in sorted(episodes_root.iterdir()):
        if not p.is_dir():
            continue
        meta_ok = (p / "metadata.json").exists()
        steps_ok = (p / "steps.jsonl").exists()
        if not (meta_ok and steps_ok):
            missing = []
            if not meta_ok: missing.append("metadata.json")
            if not steps_ok: missing.append("steps.jsonl")
            print(f"Skipping '{p.name}': missing {', '.join(missing)}")
            continue
        episode_dirs.append(p)
    total_episodes = len(episode_dirs)
    print(f"Found {total_episodes} episode(s) in '{episodes_root}'.")

    episode_index = 0
    for ep_i, ep_dir in enumerate(episode_dirs, start=1):
        _print_progress(ep_i, total_episodes, prefix="Episodes")
        meta_path = ep_dir / "metadata.json"
        steps_path = ep_dir / "steps.jsonl"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        rows: List[Dict[str, Any]] = []
        base_frame_paths: List[Path] = []
        wrist_frame_paths: List[Path] = []
        first_t: Optional[float] = None
        with open(steps_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total_frames = len(lines)
        if total_frames == 0:
            print(f"Warning: episode '{ep_dir.name}' has 0 frames; skipping.")
            continue
        for i, line in enumerate(lines, start=1):
                row = json.loads(line)
                t = row.get("t")
                if t is None:
                    st = (row.get("state") or {}).get("t")
                    t = float(st) if st is not None else None
                if first_t is None and t is not None:
                    first_t = float(t)
                rel_t = float(t - first_t) if (t is not None and first_t is not None) else 0.0

                state_dict = row.get("state") or {}
                if "state" in state_dict:
                    state = np.array(state_dict["state"], dtype=np.float32)
                elif "joints" in state_dict:
                    state = np.array(state_dict["joints"], dtype=np.float32)
                else:
                    state = np.zeros((8,), dtype=np.float32)
                state = _pad_or_trim(state, 8)

                action = row.get("action")
                if action is None:
                    action = np.zeros((7,), dtype=np.float32)
                else:
                    action = np.array(action, dtype=np.float32)
                action = _pad_or_trim(action, 7)

                base_name = row.get("base")
                wrist_name = row.get("wrist")
                base_path = (ep_dir / "base" / base_name) if base_name else None
                wrist_path = (ep_dir / "wrist" / wrist_name) if wrist_name else None
                if base_path is not None:
                    base_frame_paths.append(base_path)
                if wrist_path is not None:
                    wrist_frame_paths.append(wrist_path)

                rows.append({
                    "episode_index": episode_index,
                    "frame_index": len(rows),
                    "timestamp": rel_t,
                    "observation.state": state.tolist(),
                    "action": action.tolist(),
                })
                if total_frames > 0:
                    _print_progress(i, total_frames, prefix=f"Frames (ep {episode_index})")

        if not rows:
            continue

        df = pd.DataFrame(rows)
        parquet_path = data_dir / f"episode_{episode_index:06d}.parquet"
        print(f"Writing parquet for episode {episode_index} ({len(rows)} frames)...")
        df.to_parquet(parquet_path, engine="pyarrow", index=False)

        if not no_videos:
            if base_frame_paths:
                print(f"Writing base video for episode {episode_index} ({len(base_frame_paths)} frames)...")
                _write_video_opencv(
                    video_main_dir / f"episode_{episode_index:06d}.mp4",
                    base_frame_paths,
                    fps,
                    progress_prefix=f"Video main (ep {episode_index})",
                    target_size=target_size,
                )
            if wrist_frame_paths:
                print(f"Writing wrist video for episode {episode_index} ({len(wrist_frame_paths)} frames)...")
                _write_video_opencv(
                    video_wrist_dir / f"episode_{episode_index:06d}.mp4",
                    wrist_frame_paths,
                    fps,
                    progress_prefix=f"Video wrist (ep {episode_index})",
                    target_size=target_size,
                )

        task_text = meta.get("prompt", "")
        if task_text not in tasks_to_index:
            tasks_to_index[task_text] = next_task_index
            next_task_index += 1
        episodes_meta.append({
            "episode_index": episode_index,
            "length": len(rows),
            "tasks": [tasks_to_index[task_text]],
        })

        # Simple stats per episode in LeRobot-compatible nested schema
        state_mat = np.vstack(df["observation.state"].to_numpy())
        action_mat = np.vstack(df["action"].to_numpy())
        episodes_stats_lines.append({
            "episode_index": episode_index,
            "length": int(len(rows)),
            "stats": {
                "observation.state": {
                    # LeRobot expects 'count' to have shape (1)
                    "count": [int(len(rows))],
                    "mean": np.mean(state_mat, axis=0).tolist(),
                    "std": (np.std(state_mat, axis=0) + 1e-8).tolist(),
                    "min": np.min(state_mat, axis=0).tolist(),
                    "max": np.max(state_mat, axis=0).tolist(),
                },
                "action": {
                    # LeRobot expects 'count' to have shape (1)
                    "count": [int(len(rows))],
                    "mean": np.mean(action_mat, axis=0).tolist(),
                    "std": (np.std(action_mat, axis=0) + 1e-8).tolist(),
                    "min": np.min(action_mat, axis=0).tolist(),
                    "max": np.max(action_mat, axis=0).tolist(),
                },
            },
        })

        episode_index += 1

    # Write meta files
    meta_dir.joinpath("episodes.jsonl").write_text(
        "\n".join(json.dumps(x) for x in episodes_meta) + ("\n" if episodes_meta else ""), encoding="utf-8"
    )
    tasks_lines = [
        {"task_index": idx, "task": task}
        for task, idx in sorted(tasks_to_index.items(), key=lambda kv: kv[1])
    ]
    meta_dir.joinpath("tasks.jsonl").write_text(
        "\n".join(json.dumps(x) for x in tasks_lines) + ("\n" if tasks_lines else ""), encoding="utf-8"
    )
    meta_dir.joinpath("episodes_stats.jsonl").write_text(
        "\n".join(json.dumps(x) for x in episodes_stats_lines) + ("\n" if episodes_stats_lines else ""), encoding="utf-8"
    )
    # Build features with required shapes for OpenPI/LeRobot loaders
    features: Dict[str, Any] = {
        "observation.state": {"dtype": "float32", "shape": [8]},
        "action": {"dtype": "float32", "shape": [7]},
    }
    # Derive image shapes: if target_size set, use square; else infer from first written video or frames
    main_shape = None
    wrist_shape = None
    # If videos were written, we can infer shape from one mp4 (fallback to reading a first frame)
    try:
        main_mp4 = next(iter(sorted((video_main_dir.glob("episode_*.mp4")))))
    except StopIteration:
        main_mp4 = None
    try:
        wrist_mp4 = next(iter(sorted((video_wrist_dir.glob("episode_*.mp4")))))
    except StopIteration:
        wrist_mp4 = None
    def _probe_video_shape(path: Optional[Path]) -> Optional[List[int]]:
        if not path or not path.exists():
            return None
        cap = cv2.VideoCapture(str(path))
        ok, frame = cap.read(); cap.release()
        if ok and frame is not None:
            h, w = frame.shape[:2]
            return [int(h), int(w), 3]
        return None
    if target_size and target_size > 0:
        main_shape = [int(target_size), int(target_size), 3]
        wrist_shape = [int(target_size), int(target_size), 3]
    else:
        main_shape = _probe_video_shape(main_mp4)
        wrist_shape = _probe_video_shape(wrist_mp4)
        # As a last resort, try probing a first image from episodes
        if main_shape is None:
            for p in sorted(episodes_root.iterdir()):
                if (p / "base").exists():
                    imgs = sorted((p / "base").glob("*.jpg"))
                    if imgs:
                        img = cv2.imread(str(imgs[0]), cv2.IMREAD_COLOR)
                        if img is not None:
                            h, w = img.shape[:2]; main_shape = [int(h), int(w), 3]
                            break
        if wrist_shape is None:
            for p in sorted(episodes_root.iterdir()):
                if (p / "wrist").exists():
                    imgs = sorted((p / "wrist").glob("*.jpg"))
                    if imgs:
                        img = cv2.imread(str(imgs[0]), cv2.IMREAD_COLOR)
                        if img is not None:
                            h, w = img.shape[:2]; wrist_shape = [int(h), int(w), 3]
                            break
    # If still unknown, default to [1,1,3]
    if main_shape is None:
        main_shape = [1, 1, 3]
    if wrist_shape is None:
        wrist_shape = [1, 1, 3]
    features["observation.images.main"] = {"dtype": "video", "shape": main_shape}
    features["observation.images.secondary_0"] = {"dtype": "video", "shape": wrist_shape}

    total_episodes = len(episodes_meta)
    total_frames = int(sum(ep.get("length", 0) for ep in episodes_meta))
    info: Dict[str, Any] = {
        "codebase_version": "v2.1",
        "fps": int(fps),
        "features": features,
        "total_episodes": int(total_episodes),
        "total_frames": int(total_frames),
        # Provide simple path templates used by some loaders
        "data_path": "data/chunk-000/episode_{episode_index:06d}.parquet",
        "video_paths": {
            "observation.images.main": "videos/chunk-000/observation.images.main/episode_{episode_index:06d}.mp4",
            "observation.images.secondary_0": "videos/chunk-000/observation.images.secondary_0/episode_{episode_index:06d}.mp4",
        },
    }
    meta_dir.joinpath("info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print(f"Dataset built at: {dataset_dir}")
    return dataset_dir


def main() -> None:
    args = parse_args()
    root = Path(args.episodes_dir)
    # Determine dataset folder name
    dataset_name = (args.dataset_name or args.repo_id or Path(args.episodes_dir).resolve().name or "dataset")
    # Local builder that replicates LeRobot v2.1 layout directly into the export path
    export_root = Path(args.output_dir)
    _build_v21_locally(
        episodes_root=root,
        export_root=export_root,
        dataset_name=dataset_name,
        fps=int(args.fps),
        target_size=args.image_size if (args.image_size and args.image_size > 0) else None,
        no_videos=bool(args.no_videos),
    )
    # Run verification on the produced dataset directory
    try:
        # Recompute path in the same way _build_v21_locally does
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        # We cannot recompute reliably after time advances; instead, locate the latest subdir
        root_out = (export_root if export_root.is_absolute() else Path.cwd() / export_root)
        latest = sorted((p for p in root_out.glob("*/")), key=lambda p: p.name)[-1]
        dataset_dir = latest / dataset_name
        verify_lerobot_dataset(dataset_dir)
    except Exception as e:
        print(f"Warning: verification step failed: {e}")


if __name__ == "__main__":
    main()


