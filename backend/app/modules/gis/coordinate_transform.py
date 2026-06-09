"""
Coordinate transformation utilities.

Key operations:
- bbox → tile grid (geographic coverage, controlled tile count)
- Pixel offset within Mercator-projected tile → WGS84 (lon/lat)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


# WGS84 semi-major axis (metres)
_EARTH_R = 6_378_137.0


def _lon_to_merc_x(lon_deg: float) -> float:
    return math.radians(lon_deg) * _EARTH_R


def _lat_to_merc_y(lat_deg: float) -> float:
    return math.log(math.tan(math.pi / 4 + math.radians(lat_deg) / 2)) * _EARTH_R


def _merc_x_to_lon(x: float) -> float:
    return math.degrees(x / _EARTH_R)


def _merc_y_to_lat(y: float) -> float:
    return math.degrees(2.0 * math.atan(math.exp(y / _EARTH_R)) - math.pi / 2.0)


@dataclass(frozen=True)
class TileSpec:
    """Describes a single image tile to be fetched."""
    center_lon: float
    center_lat: float
    zoom: int
    width_px: int
    height_px: int
    # WGS84 bounds
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float
    # Web Mercator bounds (EPSG:3857, metres)
    # Used for correct pixel→WGS84 mapping when image is in Mercator projection
    merc_xmin: float = field(default=0.0)
    merc_ymin: float = field(default=0.0)
    merc_xmax: float = field(default=0.0)
    merc_ymax: float = field(default=0.0)


def _tile_meters_per_pixel(lat_deg: float, zoom: int) -> float:
    earth_circumference = 2 * math.pi * _EARTH_R
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

    Each TileSpec carries both WGS84 and Web Mercator bounds so that
    pixel_to_geo() can correctly map Mercator-projected images to WGS84.
    """
    centre_lat = (lat1 + lat2) / 2
    mpp = _tile_meters_per_pixel(centre_lat, zoom)

    tile_m = tile_size_px * mpp
    stride_m = tile_m * (1 - overlap)

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
            center_lon = lon1 + (half_tile_lon + col * stride_m / lon_m)
            center_lat = lat1 + (half_tile_lat + row * stride_m / lat_m)

            center_lon = min(center_lon, lon2 - half_tile_lon)
            center_lat = min(center_lat, lat2 - half_tile_lat)

            wgs_lon_min = center_lon - half_tile_lon
            wgs_lat_min = center_lat - half_tile_lat
            wgs_lon_max = center_lon + half_tile_lon
            wgs_lat_max = center_lat + half_tile_lat

            tiles.append(TileSpec(
                center_lon=center_lon,
                center_lat=center_lat,
                zoom=zoom,
                width_px=tile_size_px,
                height_px=tile_size_px,
                lon_min=wgs_lon_min,
                lat_min=wgs_lat_min,
                lon_max=wgs_lon_max,
                lat_max=wgs_lat_max,
                merc_xmin=_lon_to_merc_x(wgs_lon_min),
                merc_ymin=_lat_to_merc_y(wgs_lat_min),
                merc_xmax=_lon_to_merc_x(wgs_lon_max),
                merc_ymax=_lat_to_merc_y(wgs_lat_max),
            ))

    return tiles


def pixel_to_geo(
    px: float,
    py: float,
    tile: TileSpec,
) -> tuple[float, float]:
    """
    Convert pixel (x, y) in a Web Mercator tile image to WGS84 (lon, lat).

    The image is assumed to be rendered in Web Mercator (imageSR=102100),
    so pixels are linearly distributed in Mercator space.

    Args:
        px: x pixel from left (east direction)
        py: y pixel from top (y=0 = north = merc_ymax)

    Returns:
        (longitude, latitude) in WGS84 degrees
    """
    merc_x = tile.merc_xmin + (px / tile.width_px) * (tile.merc_xmax - tile.merc_xmin)
    merc_y = tile.merc_ymax - (py / tile.height_px) * (tile.merc_ymax - tile.merc_ymin)
    return _merc_x_to_lon(merc_x), _merc_y_to_lat(merc_y)
