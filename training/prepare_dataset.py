"""
Prepare urban-tree-detection-data for DeepForest fine-tuning.

Steps:
  1. Convert 4-band TIFF → 3-band RGB PNG (drop NIR)
  2. Convert point annotations → bounding boxes (fixed radius)
  3. Write DeepForest-format CSV files for train and val splits
"""
from __future__ import annotations

import csv
import os
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

DATASET_DIR = Path(__file__).parent / "dataset"
OUT_DIR = Path(__file__).parent / "prepared"

IMAGES_IN = DATASET_DIR / "images"
CSV_IN = DATASET_DIR / "csv"

IMAGES_OUT = OUT_DIR / "images"

# Bounding box half-size in pixels (20px radius ≈ 12m crown at 60 cm/px)
BBOX_RADIUS = 20
IMG_SIZE = 256


def tif_to_png(tif_path: Path, png_path: Path) -> None:
    with rasterio.open(tif_path) as src:
        # bands are 1-indexed; take R, G, B and drop NIR
        r = src.read(1)
        g = src.read(2)
        b = src.read(3)
    rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
    Image.fromarray(rgb).save(png_path)


def points_to_bboxes(csv_path: Path, img_name: str) -> list[dict]:
    rows = []
    if not csv_path.exists():
        return rows
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            x, y = int(row["x"]), int(row["y"])
            xmin = max(0, x - BBOX_RADIUS)
            ymin = max(0, y - BBOX_RADIUS)
            xmax = min(IMG_SIZE, x + BBOX_RADIUS)
            ymax = min(IMG_SIZE, y + BBOX_RADIUS)
            rows.append({
                "image_path": img_name,
                "xmin": xmin,
                "ymin": ymin,
                "xmax": xmax,
                "ymax": ymax,
                "label": "Tree",
            })
    return rows


def build_split(split_file: Path, out_csv: Path) -> int:
    names = [l.strip() for l in split_file.read_text().splitlines() if l.strip()]
    all_rows: list[dict] = []

    for name in names:
        tif_path = IMAGES_IN / f"{name}.tif"
        png_name = f"{name}.png"
        png_path = IMAGES_OUT / png_name

        if not tif_path.exists():
            print(f"  SKIP (no tif): {name}")
            continue

        tif_to_png(tif_path, png_path)

        bboxes = points_to_bboxes(CSV_IN / f"{name}.csv", png_name)
        if bboxes:
            all_rows.extend(bboxes)
        else:
            # image with no trees — DeepForest needs at least a placeholder row
            # with empty boxes to not crash; we skip these images instead
            pass

    fieldnames = ["image_path", "xmin", "ymin", "xmax", "ymax", "label"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    return len(all_rows)


def main() -> None:
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)

    print("Building train split...")
    n_train = build_split(DATASET_DIR / "train.txt", OUT_DIR / "train.csv")
    print(f"  {n_train} train annotations written")

    print("Building val split...")
    n_val = build_split(DATASET_DIR / "val.txt", OUT_DIR / "val.csv")
    print(f"  {n_val} val annotations written")

    print(f"\nDone. Output in: {OUT_DIR}")
    print(f"  images/   — RGB PNGs")
    print(f"  train.csv — {n_train} boxes")
    print(f"  val.csv   — {n_val} boxes")


if __name__ == "__main__":
    main()
