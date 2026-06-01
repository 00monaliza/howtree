"""
DeepForest inference wrapper.

Singleton per process — loaded once at FastAPI startup, reused per request.
Thread-safe: double-checked locking on load(); predict() reads only.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RawDetection:
    """Pixel-space detection from a single tile image."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float


class YoloDetector:
    """Thread-safe DeepForest wrapper. Call load() once; predict() many times."""

    def __init__(self, model_path: str | Path) -> None:
        self._model_path = Path(model_path)
        self._model = None
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        """Load model weights from a DeepForest checkpoint. Idempotent."""
        if self._model is not None:
            return
        with self._lock:
            if self._model is not None:
                return
            if not self._model_path.exists():
                raise FileNotFoundError(f"Model not found: {self._model_path}")

            logger.info("yolo_loading", path=str(self._model_path))
            t0 = time.perf_counter()

            import torch
            torch.set_num_threads(4)

            from deepforest import main as deepforest_main

            model = deepforest_main.deepforest.load_from_checkpoint(
                str(self._model_path)
            )
            model.model.eval()
            if hasattr(model.model, "cpu"):
                model.model = model.model.cpu()

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
            result = self._model.predict_image(
                path=str(image_path),
                return_plot=False,
            )
            if result is None or result.empty:
                return []

            detections: list[RawDetection] = []
            for _, row in result[result["score"] >= confidence].iterrows():
                detections.append(
                    RawDetection(
                        x1=float(row["xmin"]),
                        y1=float(row["ymin"]),
                        x2=float(row["xmax"]),
                        y2=float(row["ymax"]),
                        confidence=float(row["score"]),
                    )
                )
            return detections
        except Exception as exc:
            logger.error(
                "yolo_inference_failed",
                path=str(image_path),
                error=str(exc),
            )
            return []
