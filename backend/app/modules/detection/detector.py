"""
DeepForest inference wrapper.

Design decisions:
- Model loaded ONCE at module import time when running in Celery worker context.
  This is triggered by worker.py which imports this module on startup.
- CPU-only: torch.device("cpu") forced regardless of environment.
- Thread-safe: single model instance, GIL protects Python-level state.
  For true parallelism, use separate Celery workers (separate processes).
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)
settings = get_settings()

_model = None
_model_lock = threading.Lock()


def load_model():
    """
    Load DeepForest pretrained model (idempotent).
    Called once at worker startup; subsequent calls return immediately.
    """
    global _model

    if _model is not None:
        return _model

    with _model_lock:
        if _model is not None:
            return _model

        logger.info("deepforest_loading_model")
        try:
            import torch
            torch.set_num_threads(4)  # Limit CPU thread explosion

            from deepforest import main as deepforest_main

            # Автоматически определяем путь к файлу модели
            model_path = Path(__file__).parent / "deepforest_urban_trees_FULL.pt"

            if not model_path.exists():
                logger.error("model_file_not_found", path=str(model_path))
                raise FileNotFoundError(f"Кастомная модель не найдена по пути: {model_path}")

            # ПРАВИЛЬНЫЙ ВЫЗОВ: через класс "deepforest", а не через экземпляр "deepforest()"
            model = deepforest_main.deepforest.load_from_checkpoint(
                checkpoint_path=str(model_path)
            )

            # Force CPU evaluation mode
            model.model.eval()
            if hasattr(model.model, "cpu"):
                model.model = model.model.cpu()

            _model = model
            logger.info("deepforest_model_loaded")
        except Exception as exc:
            logger.error("deepforest_load_failed", error=str(exc))
            raise

    return _model


def predict_tile(image_path: Path) -> pd.DataFrame:
    """
    Run DeepForest inference on a single tile image.

    Args:
        image_path: Path to a PNG image tile.

    Returns:
        DataFrame with columns: xmin, ymin, xmax, ymax, label, score
        Empty DataFrame if no trees detected.
    """
    model = load_model()

    try:
        result = model.predict_image(
            path=str(image_path),
            return_plot=False,
        )
    except Exception as exc:
        logger.error(
            "deepforest_inference_failed", path=str(image_path), error=str(exc)
        )
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    if result is None or result.empty:
        return pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])

    # Filter by confidence threshold
    threshold = settings.detection_confidence_threshold
    return result[result["score"] >= threshold].reset_index(drop=True)
