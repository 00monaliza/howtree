"""Tests for tile grid generation and coordinate transforms."""
import math

import pytest

from app.modules.gis.coordinate_transform import (
    TileSpec,
    bbox_to_tiles,
    pixel_to_geo,
)


class TestBboxToTiles:
    def test_small_bbox_returns_at_least_one_tile(self):
        tiles = bbox_to_tiles(71.40, 51.10, 71.41, 51.11, zoom=18)
        assert len(tiles) >= 1

    def test_all_tiles_are_within_bbox(self):
        lon1, lat1, lon2, lat2 = 71.40, 51.10, 71.50, 51.20
        tiles = bbox_to_tiles(lon1, lat1, lon2, lat2, zoom=18)
        for tile in tiles:
            # Tile centre must be within bbox (with tolerance)
            assert lon1 - 0.01 <= tile.center_lon <= lon2 + 0.01
            assert lat1 - 0.01 <= tile.center_lat <= lat2 + 0.01

    def test_tiles_cover_bbox(self):
        lon1, lat1, lon2, lat2 = 71.40, 51.10, 71.50, 51.20
        tiles = bbox_to_tiles(lon1, lat1, lon2, lat2, zoom=18)

        all_lon_min = min(t.lon_min for t in tiles)
        all_lat_min = min(t.lat_min for t in tiles)
        all_lon_max = max(t.lon_max for t in tiles)
        all_lat_max = max(t.lat_max for t in tiles)

        assert all_lon_min <= lon1
        assert all_lat_min <= lat1
        assert all_lon_max >= lon2
        assert all_lat_max >= lat2

    def test_tile_spec_fields(self):
        tiles = bbox_to_tiles(71.40, 51.10, 71.41, 51.11, zoom=18, tile_size_px=400)
        tile = tiles[0]
        assert tile.zoom == 18
        assert tile.width_px == 400
        assert tile.height_px == 400
        assert tile.lon_min < tile.lon_max
        assert tile.lat_min < tile.lat_max


class TestPixelToGeo:
    def setup_method(self):
        self.tile = TileSpec(
            center_lon=71.45,
            center_lat=51.15,
            zoom=18,
            width_px=400,
            height_px=400,
            lon_min=71.44,
            lat_min=51.14,
            lon_max=71.46,
            lat_max=51.16,
        )

    def test_top_left_pixel_maps_to_nw_corner(self):
        lon, lat = pixel_to_geo(0, 0, self.tile)
        assert abs(lon - self.tile.lon_min) < 0.0001
        assert abs(lat - self.tile.lat_max) < 0.0001

    def test_bottom_right_pixel_maps_to_se_corner(self):
        lon, lat = pixel_to_geo(400, 400, self.tile)
        assert abs(lon - self.tile.lon_max) < 0.0001
        assert abs(lat - self.tile.lat_min) < 0.0001

    def test_centre_pixel_maps_to_tile_centre(self):
        lon, lat = pixel_to_geo(200, 200, self.tile)
        assert abs(lon - self.tile.center_lon) < 0.0001
        assert abs(lat - self.tile.center_lat) < 0.0001
