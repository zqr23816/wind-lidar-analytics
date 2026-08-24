from io import BytesIO
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from wind_lidar import analyze_wind, load_lidar_csv, reconstruct_wind


class WindLidarTests(unittest.TestCase):
    def test_loads_export_with_metadata_row(self):
        payload = (
            '"17# turbine"\n'
            '"time(s)","方向1风速(m/s)","方向2风速(m/s)","方向3风速(m/s)","方向4风速(m/s)"\n'
            '"2023-05-24 00:00:01","3.04","2.62","2.39","1.792"\n'
        ).encode("utf-8")
        frame = load_lidar_csv(BytesIO(payload))
        self.assertEqual(list(frame.columns), ["timestamp", "v1", "v2", "v3", "v4"])
        self.assertEqual(frame.loc[0, "v1"], 3.04)

    def test_reconstruction_is_finite_and_quadrant_safe(self):
        frame = pd.DataFrame(
            {"timestamp": pd.date_range("2026-01-01", periods=2, freq="s"),
             "v1": [6.8, -6.8], "v2": [7.66, -7.66],
             "v3": [6.6, -6.6], "v4": [3.26, -3.26]}
        )
        result = reconstruct_wind(frame)
        self.assertTrue(np.isfinite(result["effective_speed"]).all())
        self.assertTrue(result["upper_direction"].between(0, 360, inclusive="left").all())
        self.assertFalse(np.isclose(result.loc[0, "upper_direction"], result.loc[1, "upper_direction"]))

    def test_circular_mean_wraps_through_north(self):
        frame = pd.DataFrame({"effective_speed": [5.0, 5.0], "wind_direction": [359.0, 1.0]})
        summary = analyze_wind(frame)
        self.assertTrue(summary["mean_direction"] < 1 or summary["mean_direction"] > 359)


if __name__ == "__main__":
    unittest.main()

