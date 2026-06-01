"""Unit tests for CountRequest and CountResponse schemas."""
import pytest
from app.schemas.trees_count import CountRequest, CountResponse, DetectionOut


def test_valid_bbox():
    req = CountRequest(bbox=[71.4, 51.1, 71.5, 51.2])
    assert req.bbox == [71.4, 51.1, 71.5, 51.2]
    assert req.zoom == 18
    assert req.confidence == 0.25


def test_custom_zoom_and_confidence():
    req = CountRequest(bbox=[71.4, 51.1, 71.5, 51.2], zoom=16, confidence=0.5)
    assert req.zoom == 16
    assert req.confidence == 0.5


def test_geojson_polygon_converted_to_bbox():
    geojson = {
        "type": "Polygon",
        "coordinates": [
            [[71.4, 51.1], [71.5, 51.1], [71.5, 51.2], [71.4, 51.2], [71.4, 51.1]]
        ],
    }
    req = CountRequest(geojson=geojson)
    assert req.bbox == [71.4, 51.1, 71.5, 51.2]


def test_neither_bbox_nor_geojson_raises():
    with pytest.raises(ValueError, match="bbox.*geojson"):
        CountRequest()


def test_both_bbox_and_geojson_raises():
    geojson = {"type": "Polygon", "coordinates": [[[71.4, 51.1], [71.5, 51.1], [71.5, 51.2], [71.4, 51.1]]]}
    with pytest.raises(ValueError, match="not both"):
        CountRequest(bbox=[71.4, 51.1, 71.5, 51.2], geojson=geojson)


def test_geojson_non_polygon_raises():
    with pytest.raises(ValueError, match="Polygon"):
        CountRequest(geojson={"type": "LineString", "coordinates": [[71.4, 51.1], [71.5, 51.2]]})


def test_bbox_wrong_length_raises():
    with pytest.raises(ValueError):
        CountRequest(bbox=[71.4, 51.1, 71.5])


def test_invalid_longitude_raises():
    with pytest.raises(ValueError, match="longitude"):
        CountRequest(bbox=[200.0, 51.1, 71.5, 51.2])


def test_invalid_latitude_raises():
    with pytest.raises(ValueError, match="latitude"):
        CountRequest(bbox=[71.4, -100.0, 71.5, 51.2])


def test_min_gte_max_lon_raises():
    with pytest.raises(ValueError):
        CountRequest(bbox=[71.5, 51.1, 71.4, 51.2])


def test_valid_count_response():
    resp = CountResponse(
        tree_count=5,
        detections=[
            DetectionOut(
                bbox_pixels=[0.0, 0.0, 10.0, 10.0],
                bbox_geo=[71.4, 51.1, 71.5, 51.2],
                confidence=0.9,
            )
        ],
        area_km2=0.5,
        inference_time_ms=120,
        image_resolution=[400, 400],
    )
    assert resp.tree_count == 5
    assert len(resp.detections) == 1


def test_detection_out_confidence_range():
    with pytest.raises(ValueError):
        DetectionOut(bbox_pixels=[0.0, 0.0, 10.0, 10.0], bbox_geo=[71.4, 51.1, 71.5, 51.2], confidence=1.5)
