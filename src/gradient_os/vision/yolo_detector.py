"""
YOLO-based object detection wrapper for GradientOS Vision.

This module wraps the Ultralytics YOLO interface to provide a simple API
for loading a model and running inference on OpenCV BGR frames.

Optional dependency: `ultralytics` (and its runtime, typically `torch`).
We deliberately do not require it at install time; instead, we attempt to
import at runtime and degrade gracefully if unavailable.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Tuple


class YOLODetector:
    """
    Thin wrapper around Ultralytics YOLO for easier integration with our CLI.
    """

    def __init__(
        self,
        weights: str = "yolo11n.pt",
        confidence_threshold: float = 0.25,
        image_size: int = 640,
        device: str = "cpu",
        classes: Optional[List[int]] = None,
        max_detections: int = 300,
    ) -> None:
        # Public status fields for diagnostics
        self.available: bool = False
        self.last_error: Optional[str] = None
        self.available: bool = False
        self.model = None
        self.weights = weights
        self.confidence_threshold = float(confidence_threshold)
        self.image_size = int(image_size)
        self.device = device
        self.classes = classes
        self.max_detections = int(max_detections)

        try:
            # Prefer importing both so we can fall back if needed
            from ultralytics import YOLO  # type: ignore
            try:
                from ultralytics import RTDETR  # type: ignore
            except Exception:
                RTDETR = None  # type: ignore
        except Exception as e:  # pragma: no cover - optional dependency path
            # Ultralytics/torch not installed
            self.last_error = f"ultralytics import failed: {e}"
            return

        # Try to construct a detector. Many weights (incl. seg/pose) work with YOLO();
        # RT-DETR weights require RTDETR(). We'll try YOLO first, then RTDETR.
        load_errors = []
        for ctor_name in ("YOLO", "RTDETR"):
            try:
                if ctor_name == "YOLO":
                    self.model = YOLO(self.weights)
                else:
                    if RTDETR is None:
                        raise RuntimeError("RTDETR class not available")
                    self.model = RTDETR(self.weights)
                self.available = True
                self.last_error = None
                break
            except Exception as e:  # pragma: no cover - device/weights issues
                load_errors.append(f"{ctor_name}:{e}")
                self.available = False
                self.model = None

        if not self.available:
            self.last_error = f"load failed for '{self.weights}': {'; '.join(load_errors)}"

    def detect(self, frame_bgr: "numpy.ndarray") -> Dict[str, Any]:
        """Run inference on a single BGR frame and return parsed results.

        Returns a dict:
        {
          'boxes': [ {x1,y1,x2,y2,conf,cls_id,cls_name}, ...],
          'masks': Optional[List[ndarray_bool_HxW]],
          'keypoints': Optional[List[List[Tuple[int,int]]]]
        }
        """
        if not self.available or self.model is None:
            return {"boxes": [], "masks": None, "keypoints": None}

        try:
            # Ultralytics accepts BGR numpy arrays directly.
            results = self.model.predict(
                source=frame_bgr,
                imgsz=self.image_size,
                conf=self.confidence_threshold,
                device=self.device,
                classes=self.classes,
                max_det=self.max_detections,
                retina_masks=True,
                verbose=False,
            )
            if not results:
                return {"boxes": [], "masks": None, "keypoints": None}

            boxes: List[Dict[str, Any]] = []
            masks_out: Optional[List["numpy.ndarray"]] = None
            keypoints_out: Optional[List[List[Tuple[int, int]]]] = None
            res0 = results[0]
            # Access boxes and names safely
            try:
                names = res0.names if hasattr(res0, "names") else {}
            except Exception:
                names = {}

            try:
                for b in res0.boxes:  # type: ignore[attr-defined]
                    # xyxy is torch tensor; convert to list
                    xyxy = b.xyxy[0].tolist()
                    conf = float(b.conf[0].item())
                    cls_id = int(b.cls[0].item())
                    cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
                    boxes.append(
                        {
                            "x1": int(xyxy[0]),
                            "y1": int(xyxy[1]),
                            "x2": int(xyxy[2]),
                            "y2": int(xyxy[3]),
                            "conf": conf,
                            "cls_id": cls_id,
                            "cls_name": cls_name,
                        }
                    )
            except Exception:
                boxes = []

            # Masks (for -seg models)
            try:
                masks = getattr(res0, "masks", None)
                if masks is not None:
                    # Prefer polygons if available to reduce memory
                    polys = getattr(masks, "xy", None)
                    if polys is not None:
                        # polys is List[List[np.ndarray]] (instances → polygons). Flatten to a simple list.
                        import numpy as np  # type: ignore
                        flattened: list = []
                        for inst_polys in polys:
                            try:
                                for poly in inst_polys:
                                    flattened.append(np.asarray(poly, dtype=np.int32))
                            except Exception:
                                continue
                        if flattened:
                            masks_out = flattened
                    else:
                        data = getattr(masks, "data", None)
                        if data is not None:
                            import numpy as np  # type: ignore
                            data_cpu = data.detach().cpu().numpy()
                            # Threshold to boolean masks
                            masks_np = (data_cpu > 0.5).astype(bool)  # N x H x W
                            masks_out = [m for m in masks_np]
            except Exception:
                masks_out = None

            # Keypoints (for -pose models)
            try:
                kps = getattr(res0, "keypoints", None)
                if kps is not None:
                    import numpy as np  # type: ignore
                    xy = getattr(kps, "xy", None)
                    if xy is not None:
                        arr = xy.cpu().numpy().astype(int)  # N x K x 2
                        keypoints_out = [ [(int(x), int(y)) for (x, y) in sample] for sample in arr ]
            except Exception:
                keypoints_out = None

            return {"boxes": boxes, "masks": masks_out, "keypoints": keypoints_out}
        except Exception:
            return {"boxes": [], "masks": None, "keypoints": None}

    @staticmethod
    def draw_detections(
        frame_bgr: "numpy.ndarray",
        detections: List[Dict[str, Any]],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> "numpy.ndarray":
        """Draw bounding boxes and labels on frame and return the modified frame."""
        try:
            import cv2  # local import to avoid hard dep on OpenCV at import time
        except Exception:  # pragma: no cover
            return frame_bgr

        output = frame_bgr.copy()
        for det in detections:
            x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
            label = f"{det['cls_name']} {det['conf']:.2f}"
            try:
                cv2.rectangle(output, (x1, y1), (x2, y2), color, thickness)
                cv2.putText(
                    output,
                    label,
                    (x1, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    4,
                )
                cv2.putText(
                    output,
                    label,
                    (x1, max(0, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                )
            except Exception:
                continue

        return output

    @staticmethod
    def draw_masks(
        frame_bgr: "numpy.ndarray",
        masks: List["numpy.ndarray"],
        color: Tuple[int, int, int] = (0, 255, 255),
        alpha: float = 0.3,
    ) -> "numpy.ndarray":
        """Overlay segmentation masks (either polygons or boolean masks)."""
        try:
            import cv2
            import numpy as np
        except Exception:
            return frame_bgr

        out = frame_bgr.copy()
        overlay = out.copy()
        for m in masks:
            try:
                if m.ndim == 2:  # boolean mask HxW
                    poly_mask = np.zeros_like(out, dtype=np.uint8)
                    poly_mask[m] = color
                    overlay = cv2.add(overlay, poly_mask)
                else:
                    # polygon points (N x 2)
                    pts = np.asarray(m, dtype=np.int32)
                    if pts.ndim == 2:
                        pts = pts.reshape((-1, 1, 2))
                    cv2.fillPoly(overlay, [pts], color)
            except Exception:
                continue
        return cv2.addWeighted(overlay, alpha, out, 1 - alpha, 0)

    @staticmethod
    def draw_keypoints(
        frame_bgr: "numpy.ndarray",
        keypoints: List[List[Tuple[int, int]]],
        point_color: Tuple[int, int, int] = (0, 255, 255),
        line_color: Tuple[int, int, int] = (255, 0, 0),
    ) -> "numpy.ndarray":
        """Draw keypoints (and simple skeleton if possible)."""
        try:
            import cv2
        except Exception:
            return frame_bgr

        out = frame_bgr.copy()
        # COCO skeleton (indices depend on model; we draw points only for safety)
        for sample in keypoints:
            for (x, y) in sample:
                try:
                    cv2.circle(out, (x, y), 3, point_color, -1)
                except Exception:
                    continue
        return out


