"""
YOLOv8 inference wrapper.

Singleton per process — loaded once at FastAPI startup, reused per request.
Thread-safe: double-checked locking on load(); predict() reads only.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

_WARMUP_PX = 64  # blank image side for warmup forward pass


@dataclass
class RawDetection:
    """Pixel-space detection from a single tile image."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


class YoloDetector:
    """Thread-safe YOLOv8 wrapper. Call load() once; predict() many times."""

    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        self._model = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load model weights and run a warmup pass. Idempotent."""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not self._model_path.exists():
                raise FileNotFoundError(f"YOLO model not found: {self._model_path}")

            logger.info("yolo_loading", path=str(self._model_path))
            t0 = time.perf_counter()

            from ultralytics import YOLO

            model = YOLO(str(self._model_path))
            model.model.eval()

            try:
                blank = np.zeros((_WARMUP_PX, _WARMUP_PX, 3), dtype=np.uint8)
                model.predict(source=blank, verbose=False, conf=0.25)
            except Exception as warmup_exc:
                logger.warning("yolo_warmup_failed", error=str(warmup_exc))

            self._model = model
            logger.info(
                "yolo_loaded",
                load_time_ms=round((time.perf_counter() - t0) * 1000),
            )

    def predict(
        self,
        image_path: Path,
        confidence: float = 0.25,
    ) -> list[RawDetection]:
        """
        Run inference on one tile PNG.

        Returns empty list on inference error (logged).
        Raises RuntimeError if model was never loaded.
        """
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        try:
            results = self._model.predict(
                source=str(image_path),
                conf=confidence,
                verbose=False,
            )
        except Exception as exc:
            logger.error(
                "yolo_inference_failed",
                path=str(image_path),
                error=str(exc),
            )
            return []

        detections: list[RawDetection] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0]
                detections.append(
                    RawDetection(
                        x1=float(x1),
                        y1=float(y1),
                        x2=float(x2),
                        y2=float(y2),
                        confidence=float(box.conf[0]),
                    )
                )
        return detections
