"""Tests for IoU-based NMS deduplication."""
import pytest

from app.modules.detection.deduplication import Detection, iou, nms


def make_det(lon, lat, size=0.001, confidence=0.9):
    """Helper: square detection centred at (lon, lat)."""
    half = size / 2
    return Detection(
        lon=lon,
        lat=lat,
        lon_min=lon - half,
        lat_min=lat - half,
        lon_max=lon + half,
        lat_max=lat + half,
        confidence=confidence,
        canopy_area_m2=100.0,
    )


class TestIoU:
    def test_identical_boxes_have_iou_one(self):
        a = make_det(71.45, 51.15)
        assert abs(iou(a, a) - 1.0) < 1e-9

    def test_non_overlapping_boxes_have_iou_zero(self):
        a = make_det(71.40, 51.10)
        b = make_det(71.50, 51.20)
        assert iou(a, b) == 0.0

    def test_half_overlapping_boxes(self):
        a = make_det(71.45, 51.15, size=0.002)
        # b shifted by half the size
        b = make_det(71.451, 51.15, size=0.002)
        score = iou(a, b)
        assert 0 < score < 1


class TestNMS:
    def test_single_detection_returned(self):
        dets = [make_det(71.45, 51.15)]
        result = nms(dets)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        assert nms([]) == []

    def test_duplicate_detections_deduplicated(self):
        # Same location, slightly different confidence
        dets = [
            make_det(71.45, 51.15, confidence=0.95),
            make_det(71.45, 51.15, confidence=0.80),  # exact overlap
        ]
        result = nms(dets, iou_threshold=0.3)
        assert len(result) == 1
        assert result[0].confidence == 0.95  # Highest kept

    def test_non_overlapping_all_kept(self):
        dets = [
            make_det(71.40, 51.10, confidence=0.9),
            make_det(71.45, 51.15, confidence=0.8),
            make_det(71.50, 51.20, confidence=0.7),
        ]
        result = nms(dets)
        assert len(result) == 3

    def test_threshold_controls_suppression(self):
        a = make_det(71.45, 51.15, size=0.002, confidence=0.9)
        b = make_det(71.451, 51.15, size=0.002, confidence=0.7)  # partial overlap

        # Strict threshold: both kept
        result_strict = nms([a, b], iou_threshold=0.9)
        assert len(result_strict) == 2

        # Loose threshold: b suppressed
        result_loose = nms([a, b], iou_threshold=0.1)
        assert len(result_loose) == 1
