## MODIFIED Requirements

### Requirement: CLI 显示进度
CLI 工具 SHALL 在拉取数据时向用户实时报告进度。

#### Scenario: 启动时预判总量
- **WHEN** 用户执行 `python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-12-31`
- **THEN** 系统首先打印一行预判总量，格式为 `[预计 N 根]`，其中 N 由 `(end_ts - start_ts) / interval_ms` 计算得出

#### Scenario: 每页完成打印一行带 ETA 与当前 K 线时间的进度
- **WHEN** 数据需要分页获取（如 30647 根分 31 次请求）
- **THEN** 每完成一页系统打印一行累加的可视化进度 `[#####.....] 60%  已获取 18318/30647  (当前 2024-07-01 12:00)  用时 12s  预计剩余 8s`
- **AND** 进度条位于行首，百分比紧跟，已获取/预估在中间，`(当前 YYYY-MM-DD HH:MM)` 在右侧，用时与 ETA 在行尾

#### Scenario: 跳页打印一行标记
- **WHEN** 某页数据已在库（≥95% 覆盖率或满 1000 条）
- **THEN** 系统打印一行缩进的标记 `  ✓ 跳过第 N/M 页（已在库）`，不污染进度条行

#### Scenario: 进度回调签名扩展
- **WHEN** 调用方传入 6 参数回调 `progress(fetched, estimated_total, page, total_pages, eta_seconds, last_kline_ts)`
- **THEN** `fetch_klines_paginated` 在每页完成时调用回调，参数含义与签名一致
- **AND** `last_kline_ts` 为已拉取到的最新一根 K 线的毫秒时间戳（UTC）；跳页时取当前页末点
- **AND** 向下兼容旧的 3 参数回调 `progress(fetched, current_end, total_end)`——若传入后者，系统退回旧语义

#### Scenario: 完成时打印实际与预估对照
- **WHEN** 拉取完毕
- **THEN** 系统打印 `完成！获取 X 根K线（预估 Y），存入数据库 Z 条（跳过 W 页已有数据）`
- **AND** X 与 Y 在同一行并列，偏差一目了然

## ADDED Requirements

### Requirement: 数据总量预估函数
系统 SHALL 暴露 `estimate_total_klines(symbol, interval, start_ts, end_ts) -> int` 用于预判给定参数下预计拉取的 K 线总数。

#### Scenario: 估算 1h 全年
- **WHEN** `estimate_total_klines("BTCUSDT", "1h", "2024-01-01", "2024-12-31")` 被调用
- **THEN** 返回 `(end_ms - start_ms) // 3_600_000 + 1`

#### Scenario: 边界——小于一个间隔
- **WHEN** `start_ts == end_ts`
- **THEN** 返回 1（最少一根）

### Requirement: 请求间隔继续遵守
系统 SHALL 在连续请求之间继续遵守 `config.ini` 的 `request_interval`，预估总量与 ETA 输出不得改变这一行为。

#### Scenario: 请求间隔保持
- **WHEN** 连续发送 API 请求
- **THEN** 每次请求之间等待 `config.ini` 中 `request_interval` 指定的秒数
- **AND** 新增的 progress_callback 调用不影响该等待
