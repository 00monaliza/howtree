"""
DeepForest inference wrapper for predict_tile().

Delegates to YoloDetector (deepforest_urban_trees_FULL.pt) — a model
trained specifically on aerial/satellite tree imagery that generalises
well across different geographic regions and tile sources.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.detection.yolo_detector import YoloDetector

logger = get_logger(__name__)
settings = get_settings()

_MODEL_PATH = Path(settings.yolo_model_path)
if not _MODEL_PATH.is_absolute():
    _MODEL_PATH = (Path(__file__).parents[4] / settings.yolo_model_path).resolve()

_detector = YoloDetector(_MODEL_PATH)


def _ensure_loaded() -> None:
    if not _detector.is_loaded:
        _detector.load()


def predict_tile(image_path: Path) -> pd.DataFrame:
    """
    Run DeepForest inference on a single tile image.

    Returns DataFrame with columns: xmin, ymin, xmax, ymax, label, score
    """
    _ensure_loaded()

    detections = _detector.predict(image_path, confidence=settings.detection_confidence_threshold)
    if not detections:
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    return pd.DataFrame([
        {
            "xmin": d.x1,
            "ymin": d.y1,
            "xmax": d.x2,
            "ymax": d.y2,
            "label": "Tree",
            "score": d.confidence,
        }
        for d in detections
    ])
