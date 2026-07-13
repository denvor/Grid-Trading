## Purpose
提供独立命令行工具 `fetch_data.py` 与底层 `data_fetcher` 模块，从币安公开 API 获取历史 K 线数据并存入 SQLite 数据库，支持缓存、增量跳过与进度可视化。

## Requirements

### Requirement: CLI 数据拉取工具
系统 SHALL 提供独立的命令行工具 `fetch_data.py`，用于从币安 API 获取历史K线数据并存入 SQLite 数据库。

#### Scenario: CLI 完整参数调用
- **WHEN** 用户执行 `python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01`
- **THEN** 系统分页获取对应时间段的所有K线数据，存入数据库

#### Scenario: CLI 强制刷新
- **WHEN** 用户执行时添加 `--force` 参数
- **THEN** 系统忽略数据库缓存，重新从 API 拉取并覆盖

#### Scenario: CLI 缺必填参数
- **WHEN** 用户未指定 `--symbol` 或 `--interval` 或 `--start`
- **THEN** 系统打印用法说明并退出

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

#### Scenario: CLI 请求间隔
- **WHEN** 连续发送多个 API 请求
- **THEN** 每次请求之间等待 `config.ini` 中 `request_interval` 指定的秒数

### Requirement: 从币安公开 API 获取历史K线数据
系统 SHALL 从币安公开 API 获取指定交易对的历史K线数据（OHLCV），无需 API Key。访问需要通过代理。

#### Scenario: 成功获取 BTCUSDT 1h K线
- **WHEN** 请求 symbol=BTCUSDT interval=1h start_time=xxx end_time=yyy
- **THEN** 系统通过代理请求 API 并返回对应时间范围内的K线数据

#### Scenario: 分页获取超过 1000 根数据
- **WHEN** 请求时间范围跨度超过 1000 根K线
- **THEN** 系统自动分页请求（每次 ≤1000 根），按时间顺序合并返回

#### Scenario: API 不可用或代理异常
- **WHEN** 币安 API 返回错误或代理不可达
- **THEN** 系统返回友好的错误提示，不崩溃

#### Scenario: 无效交易对
- **WHEN** 请求不存在的交易对（如 INVALIDUSDT）
- **THEN** 系统返回明确的错误信息

### Requirement: 支持多种K线周期
系统 SHALL 支持 1m、5m、15m、1h、4h 五种K线周期。

#### Scenario: 各周期正确映射
- **WHEN** 用户选择 interval=1m / 5m / 15m / 1h / 4h
- **THEN** 系统获取对应周期的K线数据

#### Scenario: symbol 自动大写归一化
- **WHEN** 用户输入小写 symbol（如 `btcusdt`）
- **THEN** 系统自动转为大写 `BTCUSDT` 再请求

### Requirement: 数据库缓存与幂等写入
系统 SHALL 将获取的K线数据存入 SQLite 数据库，支持缓存复用。

#### Scenario: 首次获取
- **WHEN** 数据库中不存在请求的数据
- **THEN** 系统从 API 获取并存入数据库

#### Scenario: 按页增量跳过已缓存数据
- **WHEN** 数据库中已存在请求范围内某些页的数据（该页已有 ≥95% 覆盖率或已满 1000 条）
- **THEN** 系统跳过这些页的 API 请求，仅拉取剩余缺失的页
- **AND** 在 CLI 输出中报告跳过的页数

#### Scenario: 全部数据已缓存
- **WHEN** 请求范围内所有页的数据都已存在于数据库
- **THEN** 系统不发送任何 API 请求，直接返回缓存数据
- **AND** CLI 输出"跳过 N 页已有数据"

#### Scenario: 强制刷新
- **WHEN** 用户使用 `--force` 或在 Web 端勾选"强制刷新"
- **THEN** 系统忽略缓存，重新从 API 获取并覆盖

#### Scenario: 数据库幂等插入
- **WHEN** 插入已存在的主键 (symbol, interval, timestamp)
- **THEN** 系统使用 `INSERT OR REPLACE` 更新，不报错

### Requirement: 分页游标安全推进
系统 SHALL 在翻页时确保游标始终前进，即使 API 返回的时间戳早于预期范围，也不会陷入无限循环。

#### Scenario: API 返回早于请求范围的 timestamp
- **WHEN** API 返回的最后一根K线 timestamp 早于 current_end
- **THEN** 系统设置 `current_start = max(last_timestamp + 1, current_end + 1)` 以保证前进

### Requirement: 数据格式标准化
系统 SHALL 将原始 API 响应转换为统一的数据结构，价格使用 Decimal 类型。

#### Scenario: 转换K线格式
- **WHEN** 获取到原始K线数据
- **THEN** 系统输出统一格式: {symbol, interval, timestamp, open, high, low, close, volume}，价格使用 Decimal

#### Scenario: Decimal 精度保真
- **WHEN** 从数据库读取价格字段（存储为 TEXT）
- **THEN** 系统用 `Decimal(text_value)` 转换，不丢失精度

### Requirement: 配置集中管理
系统 SHALL 从 `config.ini` 读取代理地址和请求间隔。

#### Scenario: 读取代理配置
- **WHEN** 发送 API 请求
- **THEN** 系统使用 `config.ini` 中 `[api]` 节的 `proxy` 值

#### Scenario: 读取请求间隔
- **WHEN** 连续发送 API 请求
- **THEN** 系统使用 `config.ini` 中 `[api]` 节的 `request_interval` 值作为间隔秒数

#### Scenario: 配置缺失时使用默认值
- **WHEN** `config.ini` 未配置 proxy 或 request_interval
- **THEN** 系统使用合理默认值（proxy=None, interval=1.0），不崩溃

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
