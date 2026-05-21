"""
Pipeline для обработки загружаемых пользователем снимков.

Поддерживает:
- GeoTIFF (с геопривязкой — rasterio читает координаты автоматически)
- Обычные JPEG/PNG (пользователь указывает bbox вручную)
- Дроновые снимки (без привязки — bbox задаётся вручную)

Логика:
1. Читаем изображение через rasterio (GeoTIFF) или Pillow (JPEG/PNG)
2. Нарезаем на тайлы 400×400 с перекрытием 20%
3. Запускаем DeepForest на каждом тайле
4. Конвертируем пиксели → координаты
5. NMS-дедупликация
6. Сохраняем в PostGIS
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import get_settings
from app.core.logging import get_logger
from app.modules.detection.deduplication import Detection, nms
from app.modules.detection.detector import predict_tile

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ImageTileSpec:
    """Тайл вырезанный из загруженного снимка."""
    x: int          # пиксельные координаты верхнего левого угла
    y: int
    width: int
    height: int
    # Географические координаты (если известны)
    lon_min: float
    lat_min: float
    lon_max: float
    lat_max: float


def _pixel_to_geo(
    px: float, py: float,
    img_width: int, img_height: int,
    lon_min: float, lat_min: float, lon_max: float, lat_max: float,
) -> tuple[float, float]:
    lon = lon_min + (px / img_width) * (lon_max - lon_min)
    lat = lat_max - (py / img_height) * (lat_max - lat_min)
    return lon, lat


def _tile_image(
    img: Image.Image,
    tile_size: int,
    overlap: float,
    lon_min: float, lat_min: float,
    lon_max: float, lat_max: float,
) -> list[tuple[ImageTileSpec, Image.Image]]:
    """Нарезка изображения на перекрывающиеся тайлы."""
    W, H = img.size
    stride = int(tile_size * (1 - overlap))

    tiles = []
    y = 0
    while y < H:
        x = 0
        while x < W:
            x2 = min(x + tile_size, W)
            y2 = min(y + tile_size, H)
            tile_img = img.crop((x, y, x2, y2))

            # Паддинг если тайл меньше tile_size
            if tile_img.width < tile_size or tile_img.height < tile_size:
                padded = Image.new("RGB", (tile_size, tile_size), (0, 0, 0))
                padded.paste(tile_img, (0, 0))
                tile_img = padded

            # Географические координаты этого тайла
            tlon_min, tlat_max = _pixel_to_geo(x, y, W, H, lon_min, lat_min, lon_max, lat_max)
            tlon_max, tlat_min = _pixel_to_geo(x2, y2, W, H, lon_min, lat_min, lon_max, lat_max)

            spec = ImageTileSpec(
                x=x, y=y,
                width=x2 - x, height=y2 - y,
                lon_min=tlon_min, lat_min=tlat_min,
                lon_max=tlon_max, lat_max=tlat_max,
            )
            tiles.append((spec, tile_img))

            if x2 == W:
                break
            x = min(x + stride, W - tile_size)

        if y2 == H:
            break
        y = min(y + stride, H - tile_size)

    return tiles


def _estimate_canopy(det: Detection) -> float:
    lat_m = 111_111
    lon_m = 111_111 * math.cos(math.radians(det.lat))
    w = (det.lon_max - det.lon_min) * lon_m
    h = (det.lat_max - det.lat_min) * lat_m
    return w * h


def process_uploaded_image(
    image_path: Path,
    lon_min: float,
    lat_min: float,
    lon_max: float,
    lat_max: float,
    progress_cb=None,
) -> list[Detection]:
    """
    Обработка загруженного снимка.

    Args:
        image_path: Путь к файлу (GeoTIFF, JPEG, PNG)
        lon_min/lat_min/lon_max/lat_max: Географический bbox снимка
        progress_cb: callback(progress_pct, message)

    Returns:
        Список обнаруженных деревьев после NMS.
    """
    def emit(pct: int, msg: str):
        if progress_cb:
            progress_cb(pct, msg)

    emit(5, "Открываем снимок")

    # Пробуем читать как GeoTIFF через rasterio
    if image_path.suffix.lower() in (".tif", ".tiff"):
        try:
            import rasterio
            from rasterio.warp import transform_bounds

            with rasterio.open(image_path) as src:
                bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                lon_min, lat_min, lon_max, lat_max = bounds
                # Читаем первые 3 канала как RGB
                data = src.read([1, 2, 3]) if src.count >= 3 else src.read([1, 1, 1])
                # rasterio возвращает (C, H, W), PIL нужен (H, W, C)
                img = Image.fromarray(np.moveaxis(data, 0, -1).astype(np.uint8))
                logger.info("geotiff_loaded",
                    size=f"{img.width}x{img.height}",
                    bounds=[lon_min, lat_min, lon_max, lat_max])
        except Exception as exc:
            logger.warning("rasterio_failed", error=str(exc), fallback="pillow")
            img = Image.open(image_path).convert("RGB")
    else:
        img = Image.open(image_path).convert("RGB")

    emit(10, f"Снимок загружен: {img.width}×{img.height} пикселей")

    # Нарезка на тайлы
    tile_size = settings.tile_size
    tiles = _tile_image(img, tile_size, settings.tile_overlap, lon_min, lat_min, lon_max, lat_max)
    emit(15, f"Нарезано {len(tiles)} тайлов")

    # Инференс
    all_detections: list[Detection] = []
    tmp_dir = image_path.parent / "tiles"
    tmp_dir.mkdir(exist_ok=True)

    for i, (spec, tile_img) in enumerate(tiles):
        pct = 15 + int((i / len(tiles)) * 65)
        emit(pct, f"Анализ тайла {i + 1}/{len(tiles)}")

        tile_path = tmp_dir / f"tile_{i:04d}.png"
        tile_img.save(tile_path)

        df = predict_tile(tile_path)
        tile_path.unlink(missing_ok=True)

        if df.empty:
            continue

        for _, row in df.iterrows():
            cx = (row["xmin"] + row["xmax"]) / 2
            cy = (row["ymin"] + row["ymax"]) / 2

            def px(x, y):
                lon = spec.lon_min + (x / tile_size) * (spec.lon_max - spec.lon_min)
                lat = spec.lat_max - (y / tile_size) * (spec.lat_max - spec.lat_min)
                return lon, lat

            c_lon, c_lat = px(cx, cy)
            min_lon, max_lat = px(row["xmin"], row["ymin"])
            max_lon, min_lat = px(row["xmax"], row["ymax"])

            det = Detection(
                lon=c_lon, lat=c_lat,
                lon_min=min(min_lon, max_lon), lat_min=min(min_lat, max_lat),
                lon_max=max(min_lon, max_lon), lat_max=max(min_lat, max_lat),
                confidence=float(row["score"]),
            )
            det = Detection(
                **{**det.__dict__, "canopy_area_m2": _estimate_canopy(det)}
            )
            all_detections.append(det)

    emit(82, f"Дедупликация {len(all_detections)} обнаружений")
    final = nms(all_detections, iou_threshold=0.3)
    emit(90, f"Готово: {len(final)} деревьев")

    return final
