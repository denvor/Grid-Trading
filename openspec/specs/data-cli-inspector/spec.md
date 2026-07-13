## Purpose
提供独立命令行工具 `check_data.py`，查看数据库现有数据的概况、详情与空洞检测。

## Requirements

### Requirement: CLI 数据查看工具
系统 SHALL 提供独立的命令行工具 `check_data.py`，用于查看数据库现有数据的概况、详情与空洞检测。

#### Scenario: 无参数列出所有数据
- **WHEN** 用户执行 `python check_data.py`
- **THEN** 系统列出数据库中每个 symbol × interval 一行，字段：`symbol | interval | 记录数 | 最早时间 | 最近时间 | 时间跨度`
- **AND** 按 symbol / interval 排序

#### Scenario: 按 symbol 过滤
- **WHEN** 用户执行 `python check_data.py --symbol BTCUSDT`
- **THEN** 仅输出 BTCUSDT 的所有 interval 数据

#### Scenario: 按 symbol + interval 查看详情
- **WHEN** 用户执行 `python check_data.py --symbol BTCUSDT --interval 1h`
- **THEN** 输出该组合的详细统计：记录数、最早时间、最近时间、时间跨度、中位间隔、最小间隔、最大间隔、空洞数
- **AND** 空洞判定中位间隔 × `--gap-threshold`（默认 1.5）

#### Scenario: 指定 gap-threshold
- **WHEN** 用户执行 `python check_data.py --symbol BTCUSDT --interval 1h --gap-threshold 2.0`
- **THEN** 仅当间隔 > 中位间隔 × 2.0 才算空洞

#### Scenario: JSON 输出
- **WHEN** 用户执行 `python check_data.py --json` 或 `--json --symbol BTCUSDT --interval 1h`
- **THEN** 输出机器可解析的 JSON，`datetime` 字段用毫秒时间戳表示

#### Scenario: 数据库为空
- **WHEN** 数据库无任何数据
- **THEN** 友好提示 `数据库为空，请先使用 fetch_data.py 拉取数据`

#### Scenario: 找不到匹配
- **WHEN** 用户 `--symbol` 或 `--interval` 在库中不存在
- **THEN** 打印 `未找到匹配的数据。已缓存交易对：...` 并列出可用的 symbol

### Requirement: 空洞检测算法
系统 SHALL 在详情视图下扫描 K 线的相邻时间戳间隔，标记超过阈值的断点为"空洞"。

#### Scenario: 数据连续
- **WHEN** K 线间隔中位 3600000ms（1h），最大间隔 3600000ms，gap-threshold=1.5
- **THEN** 空洞数 = 0

#### Scenario: 存在断点
- **WHEN** 数据在第 100 根与第 101 根之间间隔 14400000ms（4h），中位间隔 3600000ms，gap-threshold=1.5
- **THEN** 空洞数 ≥ 1（14400000 > 3600000 × 1.5 = 5400000）

#### Scenario: 大数据集采样
- **WHEN** 某 symbol+interval 超过 50000 条
- **THEN** 只读前 50000 条做间隔统计，并在输出注明 `统计采样 50000/N 条`

### Requirement: 复用数据库层
`check_data.py`  SHALL 调用 `app.backtest.database` 暴露的现有函数（`list_symbol_intervals`、`count_klines`、`query_klines_paginated`、`init_db`），不直接写 SQL。

#### Scenario: 不直接写 SQL
- **WHEN** check_data.py 读取数据库
- **THEN** 所有查询通过 `list_symbol_intervals`、`count_klines`、`query_klines_paginated` 或 `init_db`/`get_db_path` 完成
- **AND** 不出现任何 `import sqlite3` 直接连接
