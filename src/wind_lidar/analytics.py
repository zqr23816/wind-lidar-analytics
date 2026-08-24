"""Quality, aggregation and screening analytics."""

import numpy as np
import pandas as pd


BEAUFORT = [
    (0.5, "无风"),
    (1.6, "软风"),
    (3.4, "轻风"),
    (5.5, "微风"),
    (8.0, "和风"),
    (10.8, "劲风"),
    (13.9, "强风"),
    (17.2, "疾风"),
    (20.8, "大风"),
    (24.5, "烈风"),
    (28.5, "狂风"),
    (32.7, "暴风"),
    (float("inf"), "飓风"),
]


def classify_speed(speed: float) -> str:
    if pd.isna(speed):
        return "无效"
    return next(label for upper, label in BEAUFORT if speed < upper)


def quality_report(frame: pd.DataFrame, speed_limit: float = 75.0) -> dict:
    beams = frame[["v1", "v2", "v3", "v4"]]
    invalid_rows = beams.isna().any(axis=1) | frame["timestamp"].isna()
    out_of_range = (beams.abs() > speed_limit).any(axis=1)
    duplicate_time = frame["timestamp"].duplicated(keep=False)
    return {
        "rows": int(len(frame)),
        "valid_rows": int((~(invalid_rows | out_of_range)).sum()),
        "missing_or_invalid": int(invalid_rows.sum()),
        "out_of_range": int(out_of_range.sum()),
        "duplicate_timestamps": int(duplicate_time.sum()),
    }


def detect_events(
    frame: pd.DataFrame, speed_threshold: float = 20.0, ti_threshold: float = 0.25
) -> pd.DataFrame:
    """Flag operational screening events; this is not IEC certification."""
    result = frame.copy()
    speed = result["effective_speed"]
    rolling_mean = speed.rolling(600, min_periods=60).mean()
    rolling_std = speed.rolling(600, min_periods=60).std()
    result["turbulence_intensity"] = rolling_std / rolling_mean.where(rolling_mean > 0.5)
    result["high_speed_event"] = speed >= speed_threshold
    result["high_turbulence_event"] = result["turbulence_intensity"] >= ti_threshold
    result["screening_event"] = result[
        ["high_speed_event", "high_turbulence_event"]
    ].any(axis=1)
    return result


def analyze_wind(frame: pd.DataFrame) -> dict:
    valid = frame.dropna(subset=["effective_speed", "wind_direction"])
    if valid.empty:
        raise ValueError("No valid reconstructed wind records")
    speed = valid["effective_speed"]
    angles = np.radians(valid["wind_direction"])
    mean_direction = float(
        np.degrees(np.arctan2(np.sin(angles).mean(), np.cos(angles).mean())) % 360
    )
    return {
        "records": int(len(valid)),
        "mean_speed": float(speed.mean()),
        "max_speed": float(speed.max()),
        "p95_speed": float(speed.quantile(0.95)),
        "mean_direction": mean_direction,
        "dominant_class": classify_speed(float(speed.mean())),
    }


