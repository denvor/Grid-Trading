## ADDED Requirements

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

#### Scenario: CLI 显示进度
- **WHEN** 数据需要分页获取（如 3000 根分 3 次请求）
- **THEN** 系统打印每页获取进度（如 "Fetched 1000/3000 klines (33%)"）

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
