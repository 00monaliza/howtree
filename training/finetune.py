"""
Fine-tune DeepForest on the prepared urban tree dataset.

Usage:
    source ../backend/.venv/bin/activate
    python finetune.py

Output: ../deepforest_urban_finetuned.pt
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import torch

TRAINING_DIR = Path(__file__).parent
PREPARED_DIR = TRAINING_DIR / "prepared"
CHECKPOINT_IN = TRAINING_DIR.parent / "deepforest_urban_trees_FULL.pt"
CHECKPOINT_OUT = TRAINING_DIR.parent / "deepforest_urban_finetuned.pt"

EPOCHS = 15
BATCH_SIZE = 4
LR = 1e-4
NUM_WORKERS = 0  # 0 for macOS compatibility


def main() -> None:
    print(f"DeepForest fine-tuning")
    print(f"  checkpoint in : {CHECKPOINT_IN}")
    print(f"  checkpoint out: {CHECKPOINT_OUT}")
    print(f"  train CSV     : {PREPARED_DIR / 'train.csv'}")
    print(f"  val CSV       : {PREPARED_DIR / 'val.csv'}")
    print(f"  epochs        : {EPOCHS}")
    print()

    if not CHECKPOINT_IN.exists():
        raise FileNotFoundError(f"Checkpoint not found: {CHECKPOINT_IN}")
    if not (PREPARED_DIR / "train.csv").exists():
        raise FileNotFoundError("Run prepare_dataset.py first")

    from deepforest import main as deepforest_main

    print("Loading base checkpoint...")
    model = deepforest_main.deepforest.load_from_checkpoint(str(CHECKPOINT_IN))

    # Training config
    model.config["train"]["epochs"] = EPOCHS
    model.config["train"]["batch_size"] = BATCH_SIZE
    model.config["train"]["lr"] = LR
    model.config["train"]["fast_dev_run"] = False
    model.config["train"]["csv_file"] = str(PREPARED_DIR / "train.csv")
    model.config["train"]["root_dir"] = str(PREPARED_DIR / "images")
    model.config["train"]["num_workers"] = NUM_WORKERS

    model.config["validation"]["csv_file"] = str(PREPARED_DIR / "val.csv")
    model.config["validation"]["root_dir"] = str(PREPARED_DIR / "images")
    model.config["validation"]["num_workers"] = NUM_WORKERS

    # Use MPS (Apple Silicon) if available, otherwise CPU
    if torch.backends.mps.is_available():
        accelerator = "mps"
    else:
        accelerator = "cpu"
    devices = 1

    print(f"Training on: {accelerator.upper()}")
    print("Starting training... (this will take a while on CPU)\n")

    t0 = time.time()
    model.create_trainer(
        fast_dev_run=False,
        max_epochs=EPOCHS,
        accelerator=accelerator,
        devices=devices,
        enable_progress_bar=True,
        log_every_n_steps=10,
    )
    model.trainer.fit(model)

    elapsed = (time.time() - t0) / 60
    print(f"\nTraining complete in {elapsed:.1f} min")

    model.save_model(str(CHECKPOINT_OUT))
    print(f"Model saved to: {CHECKPOINT_OUT}")
    print()
    print("Next step: update backend/.env or config.py:")
    print(f'  yolo_model_path = "../deepforest_urban_finetuned.pt"')


if __name__ == "__main__":
    main()
