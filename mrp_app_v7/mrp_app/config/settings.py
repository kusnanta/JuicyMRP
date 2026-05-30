"""config/settings.py — central configuration loader."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


class Settings:
    FORECAST_HORIZON_DAYS: int = int(os.getenv("FORECAST_HORIZON_DAYS", "30"))
    TRAIN_TEST_SPLIT_RATIO: float = float(os.getenv("TRAIN_TEST_SPLIT_RATIO", "0.8"))
    MIN_DATA_POINTS: int = int(os.getenv("MIN_DATA_POINTS", "14"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ROOT_DIR: Path = _ROOT


settings = Settings()
