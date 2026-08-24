from pathlib import Path
import sys

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from wind_lidar import analyze_wind, detect_events, load_lidar_csv, reconstruct_wind
from wind_lidar.analytics import quality_report


st.set_page_config(page_title="WindSight | 激光雷达风况分析", page_icon="🌬️", layout="wide")
st.title("WindSight · 激光雷达风况分析")
st.caption("四束激光反演 · 数据质量审计 · 风况可视化 · 运行阈值筛查")


@st.cache_data
def demo_data(rows: int = 3600) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    timestamp = pd.date_range("2026-01-01", periods=rows, freq="s")
    base = 7 + 1.6 * np.sin(np.linspace(0, 8 * np.pi, rows))
    noise = rng.normal(0, 0.35, (rows, 4))
    beams = base[:, None] * np.array([1.02, 1.08, 0.96, 0.90]) + noise
    beams[1450:1470] += 14
    return pd.DataFrame(
        {"timestamp": timestamp, **{f"v{i+1}": beams[:, i] for i in range(4)}}
    )


with st.sidebar:
    st.header("分析设置")
    uploaded = st.file_uploader("上传 WindEYE CSV", type=["csv"])
    speed_threshold = st.slider("高风速筛查阈值 (m/s)", 10.0, 40.0, 20.0, 0.5)
    ti_threshold = st.slider("高湍流筛查阈值", 0.10, 0.50, 0.25, 0.01)
    st.info("未上传文件时自动加载 1 小时合成演示数据。现场数据只在当前会话内处理。")

try:
    raw = load_lidar_csv(uploaded.getvalue()) if uploaded else demo_data()
    quality = quality_report(raw)
    reconstructed = reconstruct_wind(raw)
    analyzed = detect_events(reconstructed, speed_threshold, ti_threshold)
    summary = analyze_wind(analyzed)
except Exception as exc:
    st.error(f"数据解析失败：{exc}")
    st.stop()

metrics = st.columns(5)
metrics[0].metric("有效记录", f"{summary['records']:,}")
metrics[1].metric("平均风速", f"{summary['mean_speed']:.2f} m/s")
metrics[2].metric("P95 风速", f"{summary['p95_speed']:.2f} m/s")
metrics[3].metric("平均风向", f"{summary['mean_direction']:.1f}°")
metrics[4].metric("筛查事件", f"{int(analyzed['screening_event'].sum()):,}")

overview, direction, quality_tab, method = st.tabs(["总览", "风向分布", "数据质量", "方法说明"])

with overview:
    speed_chart = px.line(
        analyzed,
        x="timestamp",
        y="effective_speed",
        title="有效风速时间序列",
        labels={"timestamp": "时间", "effective_speed": "风速 (m/s)"},
    )
    speed_chart.add_hline(y=speed_threshold, line_dash="dash", line_color="#FFB000")
    st.plotly_chart(speed_chart, use_container_width=True)
    left, right = st.columns(2)
    left.plotly_chart(
        px.histogram(analyzed, x="effective_speed", nbins=45, title="风速分布"),
        use_container_width=True,
    )
    events = analyzed.loc[analyzed["screening_event"], [
        "timestamp", "effective_speed", "wind_direction", "turbulence_intensity",
        "high_speed_event", "high_turbulence_event",
    ]]
    right.subheader("事件明细")
    right.dataframe(events.tail(100), use_container_width=True, hide_index=True)

with direction:
    rose = analyzed.dropna(subset=["wind_direction", "effective_speed"]).copy()
    rose["direction_bin"] = (np.round(rose["wind_direction"] / 15) * 15) % 360
    rose["speed_band"] = pd.cut(
        rose["effective_speed"], [-np.inf, 3, 6, 9, 12, np.inf],
        labels=["<3", "3–6", "6–9", "9–12", ">=12"],
    )
    grouped = rose.groupby(["direction_bin", "speed_band"], observed=True).size().reset_index(name="count")
    st.plotly_chart(
        px.bar_polar(grouped, r="count", theta="direction_bin", color="speed_band", title="风玫瑰图"),
        use_container_width=True,
    )

with quality_tab:
    cols = st.columns(5)
    labels = ["总行数", "有效行", "缺失/无效", "越界值", "重复时间戳"]
    keys = ["rows", "valid_rows", "missing_or_invalid", "out_of_range", "duplicate_timestamps"]
    for col, label, key in zip(cols, labels, keys):
        col.metric(label, f"{quality[key]:,}")
    st.dataframe(raw.head(100), use_container_width=True, hide_index=True)

with method:
    st.markdown("""
    本应用将四束径向速度标准化为 `V1–V4`，按设备几何参数完成成对反演，
    并用圆周统计计算平均风向。湍流强度采用滚动窗口内 `标准差 / 平均风速`。

    **边界说明：** 当前事件模块用于工程数据筛查，不构成 IEC 61400-1 型式认证、
    安全判断或控制指令。上线生产前需用设备标定数据、采样频率和适用标准重新验证。
    """)

st.download_button(
    "下载分析结果 CSV",
    analyzed.to_csv(index=False).encode("utf-8-sig"),
    "wind_lidar_analysis.csv",
    "text/csv",
)


