"""
Non-Maximum Suppression (NMS) for merging overlapping tree detections
that arise from the tiled inference approach with overlap.

Algorithm:
1. Sort all detections by confidence descending.
2. For each detection (highest conf first), if not already suppressed:
   a. Keep it.
   b. Suppress all remaining detections with IoU > threshold.
3. Return kept detections.

This is equivalent to standard Greedy NMS used in object detection.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

@dataclass
class Detection:
    """A single tree detection in geographic space."""
    lon: float           # centre longitude
    lat: float           # centre latitude
    lon_min: float       # bbox
    lat_min: float
    lon_max: float
    lat_max: float
    confidence: float
    canopy_area_m2: float | None = None


def _bbox_area(d: Detection) -> float:
    return (d.lon_max - d.lon_min) * (d.lat_max - d.lat_min)


def _intersection_area(a: Detection, b: Detection) -> float:
    inter_lon_min = max(a.lon_min, b.lon_min)
    inter_lat_min = max(a.lat_min, b.lat_min)
    inter_lon_max = min(a.lon_max, b.lon_max)
    inter_lat_max = min(a.lat_max, b.lat_max)

    if inter_lon_max <= inter_lon_min or inter_lat_max <= inter_lat_min:
        return 0.0

    return (inter_lon_max - inter_lon_min) * (inter_lat_max - inter_lat_min)


def iou(a: Detection, b: Detection) -> float:
    """Intersection over Union of two geographic bounding boxes."""
    inter = _intersection_area(a, b)
    if inter == 0.0:
        return 0.0
    union = _bbox_area(a) + _bbox_area(b) - inter
    return inter / union if union > 0 else 0.0


def nms(
    detections: list[Detection],
    iou_threshold: float = 0.3,
) -> list[Detection]:
    """
    Greedy NMS deduplication.

    Args:
        detections: All detections from all tiles (geo-space).
        iou_threshold: Boxes with IoU > threshold are considered duplicates.
                       0.3 works well for tree canopies.

    Returns:
        Deduplicated list of Detection objects.
    """
    if not detections:
        return []

    # Sort by confidence descending
    sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)

    suppressed = [False] * len(sorted_dets)
    kept: list[Detection] = []

    for i, det in enumerate(sorted_dets):
        if suppressed[i]:
            continue
        kept.append(det)
        for j in range(i + 1, len(sorted_dets)):
            if not suppressed[j] and iou(det, sorted_dets[j]) > iou_threshold:
                suppressed[j] = True

    return kept
