#!/usr/bin/env python3
"""Train the desktop-object detector on Windows, Ubuntu, or Jetson."""

from pathlib import Path

import torch
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parent
PRETRAINED_MODEL = PROJECT_ROOT / "models" / "pretrained" / "yolo11n.pt"

model = YOLO(str(PRETRAINED_MODEL if PRETRAINED_MODEL.exists() else "yolo11n.pt"))
model.train(
    data=str(PROJECT_ROOT / "data.yaml"),
    epochs=100,
    imgsz=640,
    batch=4,
    device=0 if torch.cuda.is_available() else "cpu",
    workers=2,
    project=str(PROJECT_ROOT / "training"),
    name="desktop_objects_v2",
    pretrained=True,
    plots=True,
)
