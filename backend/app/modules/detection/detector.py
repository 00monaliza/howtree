"""
Detectron2 Mask R-CNN inference wrapper.

Uses the fine-tuned model_best.pth checkpoint with train_config.yaml.
Exposes the same predict_tile() interface as the previous DeepForest wrapper.
"""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_WEIGHTS_PATH = Path(__file__).parents[4] / "model_best.pth"
_CONFIG_PATH = Path(__file__).parents[4] / "train_config.yaml"

_model = None
_model_lock = threading.Lock()


def load_model():
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        logger.info("detectron2_loading_model")
        try:
            import torch
            torch.set_num_threads(4)

            from detectron2.config import get_cfg
            from detectron2.engine import DefaultPredictor

            if not _WEIGHTS_PATH.exists():
                raise FileNotFoundError(f"Веса модели не найдены: {_WEIGHTS_PATH}")
            if not _CONFIG_PATH.exists():
                raise FileNotFoundError(f"Конфиг модели не найден: {_CONFIG_PATH}")

            cfg = get_cfg()
            cfg.merge_from_file(str(_CONFIG_PATH))
            cfg.MODEL.WEIGHTS = str(_WEIGHTS_PATH)
            cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = settings.detection_confidence_threshold
            cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
            cfg.MODEL.DEVICE = "cpu"

            _model = DefaultPredictor(cfg)
            logger.info("detectron2_model_loaded")
        except Exception as exc:
            logger.error("detectron2_load_failed", error=str(exc))
            raise

    return _model


def predict_tile(image_path: Path) -> pd.DataFrame:
    """
    Run Detectron2 inference on a single tile image.

    Returns DataFrame with columns: xmin, ymin, xmax, ymax, label, score
    """
    predictor = load_model()

    img = cv2.imread(str(image_path))
    if img is None:
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    try:
        outputs = predictor(img)
    except Exception as exc:
        logger.error("detectron2_inference_failed", path=str(image_path), error=str(exc))
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    instances = outputs["instances"].to("cpu")
    if len(instances) == 0:
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    boxes = instances.pred_boxes.tensor.numpy()
    scores = instances.scores.numpy()

    rows = []
    for (x1, y1, x2, y2), score in zip(boxes, scores):
        rows.append({
            "xmin": float(x1),
            "ymin": float(y1),
            "xmax": float(x2),
            "ymax": float(y2),
            "label": "Tree",
            "score": float(score),
        })

    return pd.DataFrame(rows)
