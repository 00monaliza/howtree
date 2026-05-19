"""
Map tile downloader.

Implements the MapProvider protocol with:
- YandexProvider (primary, best Central Asia coverage)
- MapboxProvider (fallback)

Design: each provider is stateless and constructs a URL per TileSpec.
The downloader handles retries, timeout, and temp file management.
"""
from __future__ import annotations

import asyncio
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.gis.coordinate_transform import TileSpec

logger = get_logger(__name__)
settings = get_settings()


class MapProvider(Protocol):
    """Protocol defining the interface for satellite tile providers."""

    def tile_url(self, tile: TileSpec) -> str:
        """Build the HTTP URL for this tile."""
        ...


class YandexProvider:
    """
    Yandex Static Maps — satellite layer.
    Documentation: https://yandex.com/dev/staticapi/
    Best coverage for Kazakhstan / Central Asia.
    """

    BASE_URL = "https://static-maps.yandex.ru/1.x/"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def tile_url(self, tile: TileSpec) -> str:
        ll = f"{tile.center_lon:.6f},{tile.center_lat:.6f}"
        return (
            f"{self.BASE_URL}"
            f"?ll={ll}"
            f"&z={tile.zoom}"
            f"&l=sat"
            f"&size={tile.width_px},{tile.height_px}"
            f"&apikey={self._api_key}"
        )


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
    if settings.map_provider == "yandex" and settings.yandex_maps_api_key:
        return YandexProvider(settings.yandex_maps_api_key)
    elif settings.mapbox_token:
        logger.warning("falling_back_to_mapbox", reason="yandex_key_missing")
        return MapboxProvider(settings.mapbox_token)
    else:
        raise RuntimeError(
            "No map provider configured. Set YANDEX_MAPS_API_KEY or MAPBOX_TOKEN."
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
            response.raise_for_status()

            dest.write_bytes(response.content)
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
