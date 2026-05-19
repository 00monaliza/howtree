"""
Coordinate transformation utilities.

Key operations:
- WGS-84 (lon/lat) ↔ Web Mercator (EPSG:3857) pixel coordinates
- bbox → tile grid of (center_lon, center_lat) points
- Pixel offset within tile → geographic coordinate
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TileSpec:
    """Describes a single image tile to be fetched."""
    center_lon: float
    center_lat: float
    zoom: int
    width_px: int
    height_px: int
    # Geographic extent of this tile (derived)
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float


def _tile_meters_per_pixel(lat_deg: float, zoom: int) -> float:
    """Meters per pixel at the tile centre latitude for Mercator projection."""
    earth_circumference = 2 * math.pi * 6_378_137
    return (earth_circumference * math.cos(math.radians(lat_deg))) / (256 * 2 ** zoom)


def bbox_to_tiles(
    lon1: float,
    lat1: float,
    lon2: float,
    lat2: float,
    zoom: int,
    tile_size_px: int = 400,
    overlap: float = 0.2,
) -> list[TileSpec]:
    """
    Decompose a geographic bbox into a grid of overlapping tile specs.

    Args:
        lon1, lat1: SW corner
        lon2, lat2: NE corner
        zoom: Mapbox/Yandex zoom level
        tile_size_px: pixel dimension of each tile (square)
        overlap: fractional overlap between adjacent tiles [0, 1)

    Returns:
        List of TileSpec objects, one per tile needed to cover the bbox.
    """
    # Approximate metres per pixel at bbox centre
    centre_lat = (lat1 + lat2) / 2
    mpp = _tile_meters_per_pixel(centre_lat, zoom)

    # How many meters does one tile cover?
    tile_m = tile_size_px * mpp
    stride_m = tile_m * (1 - overlap)

    # Convert bbox to metres (approximate)
    # 1 degree lat ≈ 111_111 m
    # 1 degree lon ≈ 111_111 * cos(lat) m
    lat_m = 111_111
    lon_m = 111_111 * math.cos(math.radians(centre_lat))

    bbox_width_m = (lon2 - lon1) * lon_m
    bbox_height_m = (lat2 - lat1) * lat_m

    n_cols = max(1, math.ceil((bbox_width_m - tile_m * overlap) / stride_m))
    n_rows = max(1, math.ceil((bbox_height_m - tile_m * overlap) / stride_m))

    tiles: list[TileSpec] = []
    half_tile_lon = (tile_m / 2) / lon_m
    half_tile_lat = (tile_m / 2) / lat_m

    for row in range(n_rows):
        for col in range(n_cols):
            # Centre of this tile in geographic coords
            center_lon = lon1 + (half_tile_lon + col * stride_m / lon_m)
            center_lat = lat1 + (half_tile_lat + row * stride_m / lat_m)

            # Clamp to bbox boundary
            center_lon = min(center_lon, lon2 - half_tile_lon)
            center_lat = min(center_lat, lat2 - half_tile_lat)

            tile_lon_min = center_lon - half_tile_lon
            tile_lat_min = center_lat - half_tile_lat
            tile_lon_max = center_lon + half_tile_lon
            tile_lat_max = center_lat + half_tile_lat

            tiles.append(TileSpec(
                center_lon=center_lon,
                center_lat=center_lat,
                zoom=zoom,
                width_px=tile_size_px,
                height_px=tile_size_px,
                lon_min=tile_lon_min,
                lat_min=tile_lat_min,
                lon_max=tile_lon_max,
                lat_max=tile_lat_max,
            ))

    return tiles


def pixel_to_geo(
    px: float,
    py: float,
    tile: TileSpec,
) -> tuple[float, float]:
    """
    Convert pixel (x, y) within a tile image to (lon, lat).

    Args:
        px: x pixel from left
        py: y pixel from top
        tile: TileSpec for this image

    Returns:
        (longitude, latitude)
    """
    lon = tile.lon_min + (px / tile.width_px) * (tile.lon_max - tile.lon_min)
    # Image y=0 is north (lat_max); y increases downward
    lat = tile.lat_max - (py / tile.height_px) * (tile.lat_max - tile.lat_min)
    return lon, lat
