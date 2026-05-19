"""Tests for analytics statistics calculations."""
import pytest

from app.modules.analytics.statistics import (
    compute_bbox_area_km2,
    compute_canopy_coverage_pct,
    compute_density,
    confidence_distribution,
)


class TestBboxArea:
    def test_approximately_correct_for_astana(self):
        # ~1 km square near Astana
        area = compute_bbox_area_km2(71.40, 51.10, 71.42, 51.11)
        # Should be roughly 1-2 km²
        assert 0.5 < area < 5.0

    def test_larger_bbox_has_larger_area(self):
        small = compute_bbox_area_km2(71.40, 51.10, 71.42, 51.11)
        large = compute_bbox_area_km2(71.40, 51.10, 71.50, 51.20)
        assert large > small


class TestDensity:
    def test_zero_area_returns_zero(self):
        assert compute_density(100, 0) == 0.0

    def test_correct_density(self):
        assert compute_density(1000, 2.0) == 500.0


class TestCanopyCoverage:
    def test_zero_area_returns_zero(self):
        assert compute_canopy_coverage_pct(1000, 0) == 0.0

    def test_caps_at_100(self):
        # More canopy than area — should clamp
        assert compute_canopy_coverage_pct(2_000_000, 1.0) == 100.0

    def test_reasonable_coverage(self):
        # 100,000 m² canopy in 1 km² area = 10%
        coverage = compute_canopy_coverage_pct(100_000, 1.0)
        assert abs(coverage - 10.0) < 0.1


class TestConfidenceDistribution:
    def test_empty_list(self):
        result = confidence_distribution([])
        assert result == {"high": 0, "medium_high": 0, "medium": 0, "low": 0}

    def test_correct_binning(self):
        confs = [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35]
        result = confidence_distribution(confs)
        assert result["high"] == 1        # 0.95
        assert result["medium_high"] == 2  # 0.85, 0.75
        assert result["medium"] == 2       # 0.65, 0.55
        assert result["low"] == 2          # 0.45, 0.35
