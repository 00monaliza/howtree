"""Tests for bbox validation and security checks."""
import pytest

from app.core.security import validate_bbox


class TestBboxValidation:
    def test_valid_bbox(self):
        # ~1 km² near Astana — well within the 50 km² limit
        result = validate_bbox([71.40, 51.10, 71.42, 51.11])
        assert result == (71.40, 51.10, 71.42, 51.11)

    def test_rejects_wrong_length(self):
        with pytest.raises(ValueError, match="exactly 4"):
            validate_bbox([71.40, 51.10, 71.50])

    def test_rejects_inverted_longitudes(self):
        with pytest.raises(ValueError, match="longitude"):
            validate_bbox([71.50, 51.10, 71.40, 51.20])

    def test_rejects_inverted_latitudes(self):
        with pytest.raises(ValueError, match="latitude"):
            validate_bbox([71.40, 51.20, 71.50, 51.10])

    def test_rejects_out_of_range_longitude(self):
        with pytest.raises(ValueError):
            validate_bbox([-200.0, 51.10, 71.50, 51.20])

    def test_rejects_out_of_range_latitude(self):
        with pytest.raises(ValueError):
            validate_bbox([71.40, -95.0, 71.50, 51.20])

    def test_rejects_bbox_too_large(self):
        # ~1500 km² bbox — exceeds 50 km² limit
        with pytest.raises(ValueError, match="exceeds maximum"):
            validate_bbox([70.0, 50.0, 75.0, 53.0])

    def test_accepts_small_bbox(self):
        # ~1 km² — should pass
        result = validate_bbox([71.40, 51.10, 71.42, 51.11])
        assert len(result) == 4
