"""Input normalization for WindEYE-style CSV exports."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


ALIASES = {
    "timestamp": ("time", "时间", "timestamp"),
    "v1": ("方向1", "direction1", "v1"),
    "v2": ("方向2", "direction2", "v2"),
    "v3": ("方向3", "direction3", "v3"),
    "v4": ("方向4", "direction4", "v4"),
}


def _read_bytes(source: str | Path | bytes | BinaryIO) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    source.seek(0)
    return source.read()


def _decode(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "gb18030", "utf-8"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported text encoding; use UTF-8 or GB18030")


def _looks_like_header(line: str) -> bool:
    lowered = line.lower()
    return ("time" in lowered or "时间" in lowered) and line.count(",") >= 4


def load_lidar_csv(source: str | Path | bytes | BinaryIO) -> pd.DataFrame:
    """Load a CSV with an optional first-line site/instrument label."""
    text = _decode(_read_bytes(source))
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("The uploaded file is empty")
    header_index = next(
        (index for index, line in enumerate(lines[:10]) if _looks_like_header(line)),
        None,
    )
    if header_index is None:
        raise ValueError("Could not locate a timestamp + four-beam header row")

    frame = pd.read_csv(BytesIO("\n".join(lines[header_index:]).encode("utf-8")))
    normalized = {}
    for canonical, aliases in ALIASES.items():
        for column in frame.columns:
            compact = str(column).strip().lower().replace(" ", "")
            if any(alias.lower() in compact for alias in aliases):
                normalized[canonical] = column
                break
    if set(normalized) != set(ALIASES):
        missing = sorted(set(ALIASES) - set(normalized))
        raise ValueError(f"Could not map columns: {', '.join(missing)}")

    result = frame[[normalized[key] for key in ALIASES]].copy()
    result.columns = list(ALIASES)
    result["timestamp"] = pd.to_datetime(
        result["timestamp"].astype(str).str.strip(), errors="coerce"
    )
    for column in ("v1", "v2", "v3", "v4"):
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


