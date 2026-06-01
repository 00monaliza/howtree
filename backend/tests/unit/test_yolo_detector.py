"""Unit tests for YoloDetector — deepforest is mocked throughout."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.modules.detection.yolo_detector import RawDetection, YoloDetector


@pytest.fixture
def fake_pt(tmp_path) -> Path:
    p = tmp_path / "model.pt"
    p.write_bytes(b"\x00" * 16)
    return p


def _mock_model_with_detections(
    dets: list[tuple[float, float, float, float, float]],
) -> MagicMock:
    """Build a mock deepforest model that returns given (xmin,ymin,xmax,ymax,score) rows."""
    mock_model = MagicMock()
    if dets:
        df = pd.DataFrame(
            dets, columns=["xmin", "ymin", "xmax", "ymax", "score"]
        )
        df["label"] = "Tree"
    else:
        df = pd.DataFrame(columns=["xmin", "ymin", "xmax", "ymax", "label", "score"])
    mock_model.predict_image.return_value = df
    mock_model.model = MagicMock()
    return mock_model


def test_not_loaded_initially(fake_pt):
    assert not YoloDetector(fake_pt).is_loaded


def test_predict_before_load_raises(fake_pt, tmp_path):
    d = YoloDetector(fake_pt)
    img = tmp_path / "t.png"
    img.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="not loaded"):
        d.predict(img)


def test_load_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        YoloDetector("/no/such/file.pt").load()


def test_load_sets_is_loaded(fake_pt):
    mock_model = _mock_model_with_detections([])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
    assert d.is_loaded


def test_load_is_idempotent(fake_pt):
    mock_model = _mock_model_with_detections([])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model) as mock_load:
        d = YoloDetector(fake_pt)
        d.load()
        d.load()
    mock_load.assert_called_once()


def test_predict_returns_raw_detections(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = _mock_model_with_detections([(10.0, 20.0, 50.0, 60.0, 0.85)])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img, confidence=0.5)
    assert len(results) == 1
    r = results[0]
    assert isinstance(r, RawDetection)
    assert r.x1 == 10.0 and r.y1 == 20.0
    assert r.x2 == 50.0 and r.y2 == 60.0
    assert r.confidence == 0.85


def test_predict_empty_result(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = _mock_model_with_detections([])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []


def test_predict_none_result_returns_empty(fake_pt, tmp_path):
    """predict_image returning None yields empty list."""
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = MagicMock()
    mock_model.model = MagicMock()
    mock_model.predict_image.return_value = None
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []


def test_predict_inference_error_returns_empty(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = MagicMock()
    mock_model.model = MagicMock()
    mock_model.predict_image.side_effect = RuntimeError("cuda error")
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []


def test_predict_filters_by_confidence(fake_pt, tmp_path):
    """Only detections with score >= confidence are returned."""
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = _mock_model_with_detections([
        (10.0, 20.0, 50.0, 60.0, 0.9),
        (5.0, 5.0, 15.0, 15.0, 0.3),  # below threshold
    ])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img, confidence=0.5)
    assert len(results) == 1
    assert results[0].confidence == 0.9


def test_predict_forwards_confidence(fake_pt, tmp_path):
    """Detections below confidence threshold are filtered out."""
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_model = _mock_model_with_detections([(10.0, 20.0, 50.0, 60.0, 0.4)])
    with patch("deepforest.main.deepforest.load_from_checkpoint", return_value=mock_model):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img, confidence=0.7)
    assert results == []


def test_load_constructor_raises_leaves_unloaded(fake_pt):
    """If load_from_checkpoint raises, is_loaded stays False."""
    with patch(
        "deepforest.main.deepforest.load_from_checkpoint",
        side_effect=RuntimeError("bad weights"),
    ):
        d = YoloDetector(fake_pt)
        with pytest.raises(RuntimeError):
            d.load()
    assert not d.is_loaded
