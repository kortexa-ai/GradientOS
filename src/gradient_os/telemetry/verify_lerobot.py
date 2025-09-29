import argparse
import json
from pathlib import Path
from typing import List

import cv2
import pandas as pd


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    lines: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                lines.append(json.loads(line))
            except Exception:
                pass
    return lines


def verify(dataset_dir: Path) -> int:
    ok = True
    # Core dirs
    data_dir = dataset_dir / "data" / "chunk-000"
    videos_main_dir = dataset_dir / "videos" / "chunk-000" / "observation.images.main"
    videos_wrist_dir = dataset_dir / "videos" / "chunk-000" / "observation.images.secondary_0"
    meta_dir = dataset_dir / "meta"

    print(f"Checking structure under: {dataset_dir}")
    for d in [data_dir, meta_dir]:
        if not d.exists():
            print(f"ERROR: Missing directory: {d}")
            ok = False

    # Meta files
    info_path = meta_dir / "info.json"
    episodes_path = meta_dir / "episodes.jsonl"
    tasks_path = meta_dir / "tasks.jsonl"
    stats_path = meta_dir / "episodes_stats.jsonl"

    if info_path.exists():
        try:
            info = json.loads(info_path.read_text(encoding="utf-8"))
            print(f"info.json found. codebase_version={info.get('codebase_version')} fps={info.get('fps')}")
        except Exception as e:
            print(f"ERROR: Failed to parse info.json: {e}")
            ok = False
    else:
        print("WARNING: info.json missing")

    episodes = _read_jsonl(episodes_path)
    print(f"episodes.jsonl: {len(episodes)} entries")
    tasks = _read_jsonl(tasks_path)
    print(f"tasks.jsonl: {len(tasks)} entries")
    stats = _read_jsonl(stats_path)
    print(f"episodes_stats.jsonl: {len(stats)} entries")

    # Parquet files
    parquet_files = sorted(data_dir.glob("episode_*.parquet"))
    print(f"Found {len(parquet_files)} parquet file(s)")
    if not parquet_files:
        print("ERROR: No parquet files found")
        ok = False

    # Basic per-episode checks
    for pq in parquet_files:
        try:
            df = pd.read_parquet(pq, engine="pyarrow")
        except Exception as e:
            print(f"ERROR: Failed to read {pq.name}: {e}")
            ok = False
            continue
        required_cols = {"episode_index", "frame_index", "timestamp", "observation.state", "action"}
        missing = sorted(list(required_cols.difference(df.columns)))
        if missing:
            print(f"ERROR: {pq.name} missing columns: {', '.join(missing)}")
            ok = False
        if len(df) == 0:
            print(f"ERROR: {pq.name} has 0 rows")
            ok = False
        else:
            # Check frame_index sequence
            if not (df["frame_index"].iloc[0] == 0 and df["frame_index"].iloc[-1] == len(df) - 1):
                print(f"WARNING: {pq.name} frame_index not sequential 0..N-1")

    # Stats presence and required keys (from episodes_stats.jsonl)
    for ep_stats in stats:
        stats_obj = ep_stats.get("stats")
        if not isinstance(stats_obj, dict):
            print(f"ERROR: episode_index {ep_stats.get('episode_index')} missing 'stats'")
            ok = False
            continue
        for key in ("observation.state", "action"):
            ft = stats_obj.get(key)
            if not isinstance(ft, dict):
                print(f"ERROR: stats.{key} missing for episode_index {ep_stats.get('episode_index')}")
                ok = False
                continue
            for req in ("count", "mean", "std", "min", "max"):
                if req not in ft:
                    print(f"ERROR: stats.{key}.{req} missing for episode_index {ep_stats.get('episode_index')}")
                    ok = False
            # Ensure vector shapes are non-empty
            for vec_key in ("mean", "std", "min", "max"):
                v = ft.get(vec_key)
                if isinstance(v, list) and len(v) == 0:
                    print(f"ERROR: stats.{key}.{vec_key} is empty for episode_index {ep_stats.get('episode_index')}")
                    ok = False
            # Ensure count is shape (1)
            c = ft.get("count")
            if not (isinstance(c, list) and len(c) == 1):
                print(f"ERROR: stats.{key}.count must be length-1 list for episode_index {ep_stats.get('episode_index')} (got {type(c).__name__} len={len(c) if isinstance(c, list) else 'n/a'})")
                ok = False

    # Videos (optional): test readability of the first frame if present
    for vids_dir, label in [(videos_main_dir, "main"), (videos_wrist_dir, "wrist")]:
        if vids_dir.exists():
            mp4s = sorted(vids_dir.glob("episode_*.mp4"))
            print(f"Found {len(mp4s)} {label} video(s)")
            for mp in mp4s[:2]:  # test at most two
                cap = cv2.VideoCapture(str(mp))
                ok_opened = cap.isOpened()
                ok_read, _ = cap.read()
                cap.release()
                if not (ok_opened and ok_read):
                    print(f"WARNING: Could not read first frame of {label} video {mp.name}")
        else:
            print(f"Note: {label} video directory missing (videos optional); skipping video checks")

    print("Verification: {}".format("OK" if ok else "FAILED"))
    return 0 if ok else 2


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify a locally built LeRobot v2.1-style dataset")
    ap.add_argument("--dataset-dir", required=True, help="Path to the dataset directory to verify")
    args = ap.parse_args()
    exit(verify(Path(args.dataset_dir).expanduser().resolve()))


if __name__ == "__main__":
    main()


