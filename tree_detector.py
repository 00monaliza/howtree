from __future__ import annotations

import io
import sys
import urllib.request

import cv2
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy.ndimage import distance_transform_edt, gaussian_filter
from skimage.feature import peak_local_max
from skimage.segmentation import watershed
from skimage.measure import regionprops, label as sk_label
CONFIG = {
  
    "IMAGE_PATH": None,
    "BBOX": (71.40, 51.10, 71.50, 51.18),  
    "MAP_SIZE": (1024, 1024),              

    "HSV_GREEN_LOWER": (35, 35, 30),
    "HSV_GREEN_UPPER": (90, 255, 190),

    "ORANGE_ROOF_H":   (0,  22),   # H: оранжевые крыши
    "ORANGE_ROOF_S":   80,          # S ≥ порог
    "ORANGE_ROOF_V":   100,         # V ≥ порог

    "YELLOW_ROAD_H":   (22, 34),   # H: жёлтые дороги
    "YELLOW_ROAD_S":   80,
    "YELLOW_ROAD_V":   150,

    "BRIGHT_V_THRESH": 195,         # V ≥ порог яркости (блики, бетон)

    # Морфология
    "MORPH_OPEN_KERNEL":  3,        # размер ядра MORPH_OPEN
    "MORPH_CLOSE_KERNEL": 5,        # размер ядра MORPH_CLOSE

    # Watershed
    "SIGMA":        2.5,            # сглаживание distance-map перед поиском пиков
    "MIN_DISTANCE": 10,             # минимальное расстояние между центрами крон (пиксели)

    # Фильтр регионов
    "AREA_MIN": 50,                 # минимальная площадь дерева (пикс²)
    "AREA_MAX": 2500,               # максимальная площадь дерева (пикс²)

    # Выходные файлы
    "OUT_BOXES":   "result_boxes.jpg",
    "OUT_CENTERS": "result_centers.jpg",
    "OUT_STATS":   "stats.txt",
}


def load_image(cfg: dict) -> np.ndarray:
    """Загружает изображение из одного из трёх источников:

    1. Файл с диска (IMAGE_PATH задан и файл существует).
    2. Спутниковый тайл ESRI по координатам bbox (BBOX задан, IMAGE_PATH = None).
    3. Синтетическое изображение (оба параметра не заданы — для unit-теста).
    """
    path = cfg.get("IMAGE_PATH")
    bbox = cfg.get("BBOX")

    if path and Path(path).exists():
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Не удалось прочитать изображение: {path}")
        print(f"[источник] файл: {path}")
        return img

    if bbox is not None:
        return _download_esri_tile(bbox, cfg.get("MAP_SIZE", (1024, 1024)))

    print("[источник] синтетическое тестовое изображение")
    return _make_synthetic_image()


def _download_esri_tile(
    bbox: tuple[float, float, float, float],
    size: tuple[int, int],
) -> np.ndarray:

    lon_min, lat_min, lon_max, lat_max = bbox
    w, h = size

    url = (
        "https://server.arcgisonline.com/ArcGIS/rest/services/"
        "World_Imagery/MapServer/export"
        f"?bbox={lon_min},{lat_min},{lon_max},{lat_max}"
        "&bboxSR=4326&imageSR=4326"
        f"&size={w},{h}"
        "&format=png&f=image"
    )

    print(f"[источник] карта ESRI  bbox=({lon_min},{lat_min},{lon_max},{lat_max})  {w}×{h}px")
    print(f"           скачиваем ...")

    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = resp.read()
    except Exception as e:
        raise RuntimeError(f"Не удалось скачать тайл ESRI: {e}") from e

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("ESRI вернул данные, но cv2.imdecode не смог их прочитать.")

    print(f"           готово: {img.shape[1]}×{img.shape[0]} пикс")
    return img


def _make_synthetic_image(size: int = 800, n_trees: int = 60, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)

    # Базовый фон — тёмно-серый асфальт
    canvas_hsv = np.zeros((size, size, 3), dtype=np.uint8)
    canvas_hsv[:, :] = (0, 0, 60)                    # H=0, S=0, V=60

    # Жёлтые дороги (должны вычитаться пайплайном)
    for _ in range(4):
        x = rng.integers(0, size)
        w = rng.integers(20, 50)
        canvas_hsv[:, max(0, x - w // 2):x + w // 2] = (28, 120, 180)

    # Оранжевые крыши (должны вычитаться)
    for _ in range(10):
        x, y = rng.integers(50, size - 50, 2)
        rw, rh = rng.integers(20, 60, 2)
        canvas_hsv[y:y + rh, x:x + rw] = (10, 150, 160)

    # Яркие блики (должны вычитаться)
    for _ in range(5):
        x, y = rng.integers(0, size, 2)
        r = rng.integers(5, 20)
        cv2.circle(canvas_hsv, (int(x), int(y)), int(r), (0, 0, 210), -1)

    # Деревья — зелёные круги с вариацией HSV
    for _ in range(n_trees):
        cx, cy = rng.integers(30, size - 30, 2)
        radius  = rng.integers(10, 25)
        h = int(rng.integers(40, 85))          # зелёный H
        s = int(rng.integers(60, 220))          # насыщенность
        v = int(rng.integers(50, 170))          # яркость (не выше порога)
        cv2.circle(canvas_hsv, (int(cx), int(cy)), int(radius), (h, s, v), -1)

    # Конвертируем HSV → BGR для нормального сохранения/обработки
    return cv2.cvtColor(canvas_hsv, cv2.COLOR_HSV2BGR)


def build_green_mask(bgr: np.ndarray, cfg: dict) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lower = np.array(cfg["HSV_GREEN_LOWER"], dtype=np.uint8)
    upper = np.array(cfg["HSV_GREEN_UPPER"], dtype=np.uint8)
    return cv2.inRange(hsv, lower, upper)

def subtract_noise_masks(bgr: np.ndarray, green_mask: np.ndarray, cfg: dict) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    # Маска оранжевых крыш
    h0_lo, h0_hi = cfg["ORANGE_ROOF_H"]
    orange = (
        (h >= h0_lo) & (h <= h0_hi) &
        (s >= cfg["ORANGE_ROOF_S"]) &
        (v >= cfg["ORANGE_ROOF_V"])
    ).astype(np.uint8) * 255

    # Маска жёлтых дорог
    h1_lo, h1_hi = cfg["YELLOW_ROAD_H"]
    yellow = (
        (h >= h1_lo) & (h <= h1_hi) &
        (s >= cfg["YELLOW_ROAD_S"]) &
        (v >= cfg["YELLOW_ROAD_V"])
    ).astype(np.uint8) * 255

    # Маска ярких объектов (блики, бетон)
    bright = (v >= cfg["BRIGHT_V_THRESH"]).astype(np.uint8) * 255

    # Вычитаем все три маски из зелёной
    noise = cv2.bitwise_or(orange, cv2.bitwise_or(yellow, bright))
    clean = cv2.bitwise_and(green_mask, cv2.bitwise_not(noise))
    return clean

def apply_morphology(mask: np.ndarray, cfg: dict) -> np.ndarray:
    """Применяет MORPH_OPEN → MORPH_CLOSE для удаления шума и заполнения дыр (шаг 7)."""
    k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                  (cfg["MORPH_OPEN_KERNEL"], cfg["MORPH_OPEN_KERNEL"]))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                  (cfg["MORPH_CLOSE_KERNEL"], cfg["MORPH_CLOSE_KERNEL"]))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  k_open)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, k_close)
    return closed

def compute_distance_map(mask: np.ndarray, sigma: float) -> np.ndarray:

    binary = (mask > 0).astype(np.uint8)
    dist   = distance_transform_edt(binary).astype(np.float32)
    smoothed = gaussian_filter(dist, sigma=sigma)
    # Нормировка для удобства визуализации
    max_val = smoothed.max()
    if max_val > 0:
        smoothed /= max_val
    return smoothed


def find_tree_centers(dist_map: np.ndarray, min_distance: int) -> np.ndarray:
    peaks = peak_local_max(
        dist_map,
        min_distance=min_distance,
        threshold_rel=0.1,     # игнорируем слабые пики
    )
    return peaks

def run_watershed(mask: np.ndarray, peaks: np.ndarray) -> np.ndarray:
    """Запускает watershed по маркерам из peaks, ограниченный маской (шаг 10).

    Возвращает label-карту (int32), где 0 — фон.
    """
    # Создаём карту маркеров: каждый пик — уникальный целочисленный метка
    markers = np.zeros(mask.shape, dtype=np.int32)
    for idx, (r, c) in enumerate(peaks, start=1):
        markers[r, c] = idx

    # Инвертируем маску: watershed «заливает» от маркеров к минимумам
    binary = (mask > 0).astype(np.uint8)
    labels = watershed(-mask.astype(np.float32), markers, mask=binary)
    return labels

def filter_regions(labels: np.ndarray, area_min: int, area_max: int):
    """Фильтрует сегменты watershed по площади (шаг 11).

    Возвращает список regionprops объектов прошедших фильтр.
    """
    regions = regionprops(labels)
    return [r for r in regions if area_min <= r.area <= area_max]

def draw_bounding_boxes(bgr: np.ndarray, regions) -> np.ndarray:
    """Рисует bounding box каждого дерева поверх исходного снимка (шаг 12)."""
    out = bgr.copy()
    for region in regions:
        min_r, min_c, max_r, max_c = region.bbox
        # Зелёный прямоугольник
        cv2.rectangle(out, (min_c, min_r), (max_c, max_r), (0, 220, 80), 1)
        # Маленький крест в центре
        cr, cc = int(region.centroid[0]), int(region.centroid[1])
        cv2.drawMarker(out, (cc, cr), (255, 255, 0),
                       cv2.MARKER_CROSS, markerSize=5, thickness=1)
    return out


def draw_centers(bgr: np.ndarray, regions) -> np.ndarray:
    """Рисует точки центров крон (шаг 12 — альтернативный вид)."""
    out = bgr.copy()
    for region in regions:
        cr, cc = int(region.centroid[0]), int(region.centroid[1])
        cv2.circle(out, (cc, cr), 3, (0, 255, 120), -1)
        cv2.circle(out, (cc, cr), 5, (0, 180, 60),   1)
    return out

def compute_stats(bgr: np.ndarray, clean_mask: np.ndarray, regions) -> dict:
    """Вычисляет итоговую статистику (шаг 13)."""
    total_px   = bgr.shape[0] * bgr.shape[1]
    green_px   = int(np.count_nonzero(clean_mask))
    green_pct  = round(green_px / total_px * 100, 2)
    tree_count = len(regions)

    areas = [r.area for r in regions]
    avg_area = round(float(np.mean(areas)), 1) if areas else 0.0

    return {
        "tree_count": tree_count,
        "green_coverage_pct": green_pct,
        "green_pixels": green_px,
        "total_pixels": total_px,
        "avg_tree_area_px": avg_area,
    }


def save_stats(stats: dict, cfg: dict, path: str) -> None:
    """Записывает статистику и параметры конфигурации в текстовый файл."""
    lines = [
        "=" * 50,
        "  РЕЗУЛЬТАТЫ ДЕТЕКЦИИ ДЕРЕВЬЕВ",
        "=" * 50,
        f"Деревьев обнаружено : {stats['tree_count']}",
        f"Покрытие зеленью   : {stats['green_coverage_pct']} %",
        f"Зелёных пикселей   : {stats['green_pixels']} / {stats['total_pixels']}",
        f"Средняя площадь    : {stats['avg_tree_area_px']} пикс²",
        "",
        "ИСПОЛЬЗОВАННЫЕ ПАРАМЕТРЫ:",
        f"  IMAGE_PATH        : {cfg['IMAGE_PATH'] or '(карта)'}",
        f"  BBOX              : {cfg.get('BBOX', 'N/A')}",
        f"  HSV_GREEN_LOWER   : {cfg['HSV_GREEN_LOWER']}",
        f"  HSV_GREEN_UPPER   : {cfg['HSV_GREEN_UPPER']}",
        f"  SIGMA             : {cfg['SIGMA']}",
        f"  MIN_DISTANCE      : {cfg['MIN_DISTANCE']}",
        f"  AREA_MIN / MAX    : {cfg['AREA_MIN']} / {cfg['AREA_MAX']}",
        "=" * 50,
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def main():
    cfg = CONFIG

    bgr = load_image(cfg)
    print(f"[1] Изображение загружено: {bgr.shape[1]}×{bgr.shape[0]} пикс")

    green_mask = build_green_mask(bgr, cfg)
    print(f"[2-3] Зелёных пикселей до вычитания: {np.count_nonzero(green_mask)}")

    clean_mask = subtract_noise_masks(bgr, green_mask, cfg)
    print(f"[4-6] Зелёных пикселей после вычитания: {np.count_nonzero(clean_mask)}")

    morph_mask = apply_morphology(clean_mask, cfg)
    print(f"[7]   После морфологии: {np.count_nonzero(morph_mask)}")

    dist_map = compute_distance_map(morph_mask, cfg["SIGMA"])

    peaks = find_tree_centers(dist_map, cfg["MIN_DISTANCE"])
    print(f"[9]   Найдено пиков (потенциальных деревьев): {len(peaks)}")

    labels = run_watershed(morph_mask, peaks)

    regions = filter_regions(labels, cfg["AREA_MIN"], cfg["AREA_MAX"])
    print(f"[11]  Деревьев после фильтрации по площади: {len(regions)}")

    img_boxes   = draw_bounding_boxes(bgr, regions)
    img_centers = draw_centers(bgr, regions)

    cv2.imwrite(cfg["OUT_BOXES"],   img_boxes)
    cv2.imwrite(cfg["OUT_CENTERS"], img_centers)
    print(f"[12]  Сохранено: {cfg['OUT_BOXES']}, {cfg['OUT_CENTERS']}")

    stats = compute_stats(bgr, clean_mask, regions)
    save_stats(stats, cfg, cfg["OUT_STATS"])

    print()
    print(f"  Деревьев обнаружено : {stats['tree_count']}")
    print(f"  Покрытие зеленью   : {stats['green_coverage_pct']} %")
    print(f"  Средняя площадь    : {stats['avg_tree_area_px']} пикс²")
    print()
    print("  Параметры:")
    print(f"    HSV_GREEN  : {cfg['HSV_GREEN_LOWER']} – {cfg['HSV_GREEN_UPPER']}")
    print(f"    SIGMA      : {cfg['SIGMA']}")
    print(f"    MIN_DIST   : {cfg['MIN_DISTANCE']}")
    print(f"    AREA       : {cfg['AREA_MIN']} – {cfg['AREA_MAX']} пикс²")
    print(f"  Статистика → {cfg['OUT_STATS']}")


if __name__ == "__main__":
    main()
