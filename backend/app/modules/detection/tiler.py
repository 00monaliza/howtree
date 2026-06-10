"""
Map tile downloader.

Implements the MapProvider protocol with:
- EsriProvider (no key, same imagery family as the frontend map)
- YandexProvider
- MapboxProvider

Design: each provider is stateless and constructs a URL per TileSpec.
The downloader handles retries, timeout, and temp file management.
"""
from __future__ import annotations

import asyncio
import math
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from typing import Protocol

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.gis.coordinate_transform import TileSpec

logger = get_logger(__name__)
settings = get_settings()


def _redact_url_secret(url: str) -> str:
    parts = urlsplit(url)
    query = urlencode(
        [
            (key, "***" if key.lower() in {"apikey", "key", "access_token"} else value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ]
    )
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))


class MapProvider(Protocol):
    """Protocol defining the interface for satellite tile providers."""

    def tile_url(self, tile: TileSpec) -> str:
        """Build the HTTP URL for this tile."""
        ...


class EsriProvider:
    """
    Esri World Imagery MapServer export endpoint.

    Requests images in Web Mercator (imageSR=102100) so that pixel coordinates
    match the Mercator-projected display on the frontend, eliminating the
    ~1.59× vertical distortion that occurs at 51°N with geographic (4326) output.
    """

    BASE_URL = (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/export"
    )

    def tile_url(self, tile: TileSpec) -> str:
        # Bbox in WGS84 (bboxSR=4326); output image in Web Mercator (imageSR=102100)
        bbox = f"{tile.lon_min},{tile.lat_min},{tile.lon_max},{tile.lat_max}"
        return (
            f"{self.BASE_URL}"
            f"?bbox={bbox}"
            f"&bboxSR=4326"
            f"&imageSR=102100"
            f"&size={tile.width_px},{tile.height_px}"
            f"&format=png"
            f"&f=image"
        )


class YandexProvider:
    """
    Yandex satellite tiles via the public CDN (sat01-04.maps.yandex.net).
    No API key required. Best coverage for Kazakhstan / Central Asia.
    CDN tiles are 256×256; TileDownloader resizes to match TileSpec dimensions.
    """

    def __init__(self, api_key: str = "") -> None:
        # api_key retained for API compatibility but unused — CDN needs no auth
        pass

    def tile_url(self, tile: TileSpec) -> str:
        z = tile.zoom
        lat_r = math.radians(tile.center_lat)
        x = int((tile.center_lon + 180) / 360 * (1 << z))
        y = int((1 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2 * (1 << z))
        server = (x + y) % 4 + 1  # round-robin across sat01–sat04
        return f"https://sat0{server}.maps.yandex.net/tiles?l=sat&x={x}&y={y}&z={z}"


class MapboxProvider:
    """
    Mapbox satellite tiles.
    Used as fallback when Yandex is unavailable or unconfigured.
    """

    BASE_URL = "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"

    def __init__(self, token: str) -> None:
        self._token = token

    def tile_url(self, tile: TileSpec) -> str:
        ll = f"{tile.center_lon:.6f},{tile.center_lat:.6f}"
        return (
            f"{self.BASE_URL}"
            f"/{ll},{tile.zoom}"
            f"/{tile.width_px}x{tile.height_px}"
            f"?access_token={self._token}"
        )


def get_map_provider() -> MapProvider:
    """Factory — selects provider based on config."""
    if settings.map_provider == "esri":
        return EsriProvider()
    if settings.map_provider == "yandex" and settings.yandex_maps_api_key:
        return YandexProvider(settings.yandex_maps_api_key)
    if settings.map_provider == "mapbox" and settings.mapbox_token:
        return MapboxProvider(settings.mapbox_token)
    if settings.map_provider == "yandex" and settings.mapbox_token:
        logger.warning("falling_back_to_mapbox", reason="yandex_key_missing")
        return MapboxProvider(settings.mapbox_token)
    raise RuntimeError(
        "No imagery provider configured. Set MAP_PROVIDER=esri, "
        "YANDEX_MAPS_API_KEY, or MAPBOX_TOKEN."
    )


class TileDownloader:
    """
    Downloads tiles concurrently with retries.
    Files written to a temp directory, caller is responsible for cleanup.
    """

    def __init__(
        self,
        provider: MapProvider | None = None,
        max_concurrent: int = 8,
        timeout_s: float = 30.0,
    ) -> None:
        self._provider = provider or get_map_provider()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = httpx.Timeout(timeout_s)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _download_one(
        self,
        client: httpx.AsyncClient,
        tile: TileSpec,
        dest: Path,
    ) -> Path:
        async with self._semaphore:
            url = self._provider.tile_url(tile)
            logger.debug("downloading_tile", url=url[:80])

            response = await client.get(url, timeout=self._timeout)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(
                    f"Tile provider returned HTTP {exc.response.status_code} for "
                    f"{_redact_url_secret(str(exc.request.url))}"
                ) from exc

            dest.write_bytes(response.content)

            # Resize if provider returned a different size than TileSpec expects
            # (e.g. Yandex CDN always delivers 256×256)
            if tile.width_px != 256 or tile.height_px != 256:
                from PIL import Image
                import io as _io
                img = Image.open(_io.BytesIO(response.content)).convert("RGB")
                if img.size != (tile.width_px, tile.height_px):
                    img = img.resize((tile.width_px, tile.height_px), Image.LANCZOS)
                    img.save(dest, format="PNG")

            return dest

    async def download_tiles(
        self,
        tiles: list[TileSpec],
        work_dir: Path,
    ) -> list[tuple[TileSpec, Path]]:
        """
        Download all tiles into work_dir.

        Returns:
            List of (TileSpec, path_to_image) pairs, in the same order as input.
        """
        work_dir.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [
                self._download_one(
                    client,
                    tile,
                    work_dir / f"tile_{i:04d}.png",
                )
                for i, tile in enumerate(tiles)
            ]
            paths = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[tuple[TileSpec, Path]] = []
        for tile, path in zip(tiles, paths):
            if isinstance(path, Exception):
                logger.error("tile_download_failed", error=str(path))
                raise RuntimeError(f"Failed to download tile: {path}") from path
            results.append((tile, path))

        logger.info("tiles_downloaded", count=len(results))
        return results
