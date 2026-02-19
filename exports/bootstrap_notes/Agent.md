# Bootstrap 引导说明（离线冒烟用）

文件清单：
- data_raw/bootstrap/trading_calendar.csv
- data_raw/bootstrap/price_600519SH.csv
- data_raw/bootstrap/price_601318SH.csv
- data_raw/bootstrap/smoke_dates.txt  # 两行，冒烟两日
- exports/bootstrap_notes/proxy_notes.md
- inputs/CSI300.csv
- inputs/akshare_docs.md

股票与日期：
- 股票：600519.SH（贵州茅台）、601318.SH（中国平安）
- 冒烟两日：2024-12-30, 2025-08-15

价量字段：date, open, high, low, close, volume, amount(若有), turnover(若有), adj_close_hfq

后续期望（云端沙箱）：
1) 用 trading_calendar 作为基准轴；
2) 以两只票在两日跑通 raw→silver→gold→CPT/SFT/TXT 三格式导出；
3) 无前视审计：特征可用性 ≤ 当日15:00；
4) 标签基于 adj_close_hfq 的未来 1D/5D/20D bps（裁剪至 [-2000,2000]）。
