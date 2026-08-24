"""Vectorized four-beam wind reconstruction."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class LidarGeometry:
    """Instrument geometry in degrees."""

    half_angle: float = 18.0
    horizontal_angle: float = 13.0
    vertical_angle: float = 12.62


def reconstruct_wind(
    frame: pd.DataFrame, geometry: LidarGeometry | None = None
) -> pd.DataFrame:
    """Reconstruct effective speed and four pair-wise directions from V1..V4.

    ``arctan2`` is deliberately used to preserve quadrants. Invalid or infinite
    beam values propagate as missing values and are surfaced by the quality layer.
    """
    geometry = geometry or LidarGeometry()
    required = ["timestamp", "v1", "v2", "v3", "v4"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    result = frame.copy()
    beams = result[["v1", "v2", "v3", "v4"]].apply(
        pd.to_numeric, errors="coerce"
    )
    result[["v1", "v2", "v3", "v4"]] = beams

    beta = np.radians(geometry.half_angle)
    alpha = np.radians(geometry.horizontal_angle)
    theta = np.radians(geometry.vertical_angle)
    result["effective_speed"] = beams.mean(axis=1, skipna=False) / np.cos(beta)

    pairs = {
        "upper": ("v1", "v2"),
        "lower": ("v4", "v3"),
        "left": ("v4", "v1"),
        "right": ("v3", "v2"),
    }
    for label, (a_name, b_name) in pairs.items():
        a = beams[a_name]
        b = beams[b_name]
        term1 = (b - a) / (2 * np.sin(alpha) * np.cos(theta))
        term2 = (b + a) / (2 * np.cos(alpha) * np.cos(theta))
        result[f"{label}_speed"] = np.hypot(term1, term2)
        numerator = (b - a) * np.cos(alpha)
        denominator = (b + a) * np.sin(alpha)
        result[f"{label}_direction"] = (
            np.degrees(np.arctan2(numerator, denominator)) % 360
        )

    result["wind_direction"] = result["upper_direction"]
    result.replace([np.inf, -np.inf], np.nan, inplace=True)
    return result


