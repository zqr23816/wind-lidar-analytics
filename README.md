# WindSight — 激光雷达风况分析平台

一个面向四束测风激光雷达数据的可部署分析产品：将设备 CSV 转换为可审计的风速、风向、数据质量和异常筛查结果，并提供交互式时间序列与风玫瑰图。

> 公开版本使用合成数据。原始现场数据、机组编号和桌面可执行文件不进入仓库。

## 项目亮点

- 兼容含设备信息首行、中文列名和 GB18030/UTF-8 编码的 WindEYE CSV。
- 四束径向速度矢量化反演；用 `atan2` 保留风向象限。
- 数据质量审计：缺失值、越界值、重复时间戳和有效率。
- 交互式时序图、风速分布、风玫瑰和事件明细。
- 阈值参数可调，结果可下载；附 pytest 和 GitHub Actions。
- Streamlit 单服务架构，适合免费云端演示。

## 快速开始

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
streamlit run app.py
```

未上传 CSV 时会自动使用固定随机种子的合成数据。测试：

```bash
python -m unittest discover -s tests -v
```

## 输入格式

系统会自动寻找时间列和四束速度列，支持如下设备导出格式：

```csv
"site-label"
"time(s)","方向1风速(m/s)","方向2风速(m/s)","方向3风速(m/s)","方向4风速(m/s)"
"2023-05-24 00:00:01","3.04","2.62","2.39","1.792"
```

## 架构

```text
设备 CSV / 合成样例
        │
        ▼
编码与列映射 ──► 数据质量审计
        │
        ▼
四束激光风速/风向反演
        │
        ▼
滚动统计与事件筛查 ──► Streamlit 可视化 / CSV 导出
```

核心模块位于 `src/wind_lidar/`：`io.py` 负责输入边界，`core.py` 负责领域计算，`analytics.py` 负责统计与筛查，`app.py` 仅负责交互和展示。

## 部署到 Streamlit Community Cloud

1. 将仓库推送到 GitHub。
2. 在 Streamlit Community Cloud 新建应用并连接该仓库。
3. Main file path 填 `app.py`，Python 选择 3.11，点击 Deploy。

应用不依赖密钥或外部 API。正式使用前建议增加身份认证、对象存储、审计日志和设备参数管理。

## 工程边界

事件识别是可配置的运行筛查，不构成 IEC 61400-1 型式认证、安全判断或控制指令。公式、设备几何参数和阈值必须结合设备标定、采样频率及适用标准完成独立验证。

