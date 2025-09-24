from pathlib import Path
from typing import Optional
import json
import cv2
import numpy as np
import tyro
from lerobot.common.datasets.lerobot_dataset import HF_LEROBOT_HOME, LeRobotDataset


class Args(tyro.conf.FlagConversionOff):
    episodes_dir: str = "data/episodes"
    repo_id: str = "yourname/miniarm"
    fps: int = 10
    image_size: int = 256
    push_to_hub: bool = False


def _read_rgb(path: Optional[Path], size: int) -> np.ndarray:
    if not path or not path.exists():
        return np.zeros((size, size, 3), dtype=np.uint8)
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        return np.zeros((size, size, 3), dtype=np.uint8)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if rgb.shape[:2] != (size, size):
        rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_AREA)
    return rgb


def main(args: Args) -> None:
    root = Path(args.episodes_dir)
    ds = LeRobotDataset.create(
        repo_id=args.repo_id, robot_type="custom", fps=int(args.fps),
        features={
            "image": {"dtype": "image", "shape": (args.image_size, args.image_size, 3), "names": ["h","w","c"]},
            "wrist_image": {"dtype": "image", "shape": (args.image_size, args.image_size, 3), "names": ["h","w","c"]},
            "state": {"dtype": "float32", "shape": (8,), "names": ["state"]},
            "actions": {"dtype": "float32", "shape": (7,), "names": ["actions"]},
        },
    )
    for ep_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        meta = json.loads((ep_dir / "metadata.json").read_text(encoding="utf-8"))
        with open(ep_dir / "steps.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                img = _read_rgb((ep_dir / "base" / row["base"]) if row.get("base") else None, args.image_size)
                wimg = _read_rgb((ep_dir / "wrist" / row["wrist"]) if row.get("wrist") else None, args.image_size)
                state_dict = row.get("state") or {}
                if "state" in state_dict:
                    state = np.array(state_dict["state"], dtype=np.float32)
                elif "joints" in state_dict:
                    state = np.array(state_dict["joints"], dtype=np.float32)
                else:
                    state = np.zeros((8,), dtype=np.float32)
                if state.ndim == 0: state = state[None]
                if state.shape[0] < 8: state = np.pad(state, (0, 8 - state.shape[0]))
                if state.shape[0] > 8: state = state[:8]
                action = row.get("action")
                if action is None:
                    action = np.zeros((7,), dtype=np.float32)
                else:
                    action = np.array(action, dtype=np.float32)
                    if action.ndim == 0: action = action[None]
                    if action.shape[0] < 7: action = np.pad(action, (0, 7 - action.shape[0]))
                    if action.shape[0] > 7: action = action[:7]
                ds.add_frame({"image": img, "wrist_image": wimg, "state": state, "actions": action, "task": meta.get("prompt", "")})
        ds.save_episode()
    if args.push_to_hub:
        ds.push_to_hub(tags=["miniarm","custom"], private=False, push_videos=True, license="apache-2.0")


if __name__ == "__main__":
    tyro.cli(main)


