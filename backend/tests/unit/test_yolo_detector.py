"""Unit tests for YoloDetector — ultralytics is mocked throughout."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.modules.detection.yolo_detector import RawDetection, YoloDetector


@pytest.fixture
def fake_pt(tmp_path) -> Path:
    p = tmp_path / "model.pt"
    p.write_bytes(b"\x00" * 16)
    return p


def _mock_yolo_with_detections(dets: list[tuple[float, float, float, float, float]]):
    """Build a mock YOLO instance that returns given (x1,y1,x2,y2,conf) detections."""
    mock_result = MagicMock()
    boxes = []
    for x1, y1, x2, y2, conf in dets:
        b = MagicMock()
        b.xyxy = [[x1, y1, x2, y2]]
        b.conf = [conf]
        boxes.append(b)
    mock_result.boxes = boxes
    mock_instance = MagicMock()
    mock_instance.model = MagicMock()
    mock_instance.predict.return_value = [mock_result]
    return mock_instance


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
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
    assert d.is_loaded


def test_load_is_idempotent(fake_pt):
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo) as MockYOLO:
        d = YoloDetector(fake_pt)
        d.load()
        d.load()
    MockYOLO.assert_called_once()


def test_predict_returns_raw_detections(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_yolo = _mock_yolo_with_detections([(10.0, 20.0, 50.0, 60.0, 0.85)])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
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
    mock_yolo = _mock_yolo_with_detections([])
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []


def test_predict_inference_error_returns_empty(fake_pt, tmp_path):
    img = tmp_path / "tile.png"
    img.write_bytes(b"x")
    mock_yolo = MagicMock()
    mock_yolo.model = MagicMock()
    mock_yolo.predict.side_effect = RuntimeError("cuda error")
    with patch("ultralytics.YOLO", return_value=mock_yolo):
        d = YoloDetector(fake_pt)
        d.load()
        results = d.predict(img)
    assert results == []
