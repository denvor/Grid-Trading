## Why

`fetch_data.py` 在拉取大量历史数据时，进度输出只有 `已获取 X 根K线...`（每页回滚同一行），没有总量预估、没有百分比、没有 ETA。拉 BTCUSDT 1h 这种 30000+ 条数据，用户跑了多久、还要跑多久，心里完全没底。

另外，数据库里已经存了什么数据、各 symbol/interval 的时间跨度、有没有空洞，目前只能进 SQLite CLI 手动查询，缺少内建的查看工具。

## What Changes

### 改动 1：`fetch_data.go` 进度可预期化

- **预判总数**：用 `(end_ts - start_ts) / interval_ms` 算出预计K线总数（上限），拉取前打印一次 `[预计 30647 根]`
- **进度条替换**：每页完成打印一行 `[#####.....] 60%  已获取 18318/30647  (当前 2024-07-01 12:00)  用时 12s  预计剩余 8s`
- **跳页标记**：已缓存的页打印一行 `  ✓ 跳过第 N/M 页（已在库）`
- **完成摘要**：同现在的"获取 X 根，存入 Y 条（跳过 Z 页）"，去掉 `\r` 同行走马灯

### 改动 2：新增 `check_data.py`

独立 CLI，用于查看数据库现状：

```
python check_data.py                          # 列出所有 symbol/interval 的数据概况
python check_data.py --symbol BTCUSDT          # 只看 BTCUSDT 的所有 interval
python check_data.py --symbol BTCUSDT --interval 1h  # 详细看 + 检测空洞
```

输出字段：symbol / interval / 记录数 / 最早时间 / 最近时间 / 时间跨度 / 间隔（中位/最小/最大）/ 空洞数。

## Capabilities

### New Capabilities

- `data-cli-inspector`：查看数据库现有数据的独立 CLI 工具，支持摘要 / 详情 / 空洞检测。

### Modified Capabilities

- `data-fetcher`：进度上报契约变更——`progress_callback(fetched, estimated_total, page, total_pages, eta_seconds, last_kline_ts)` 签名扩展（6 参数），CLI 层据此渲染百分比进度条、ETA 与当前 K 线时间。

## Impact

- `fetch_data.py`：主函数大量重写（进度渲染 + total 预估）
- `app/backtest/data_fetcher.py`：`progress_callback` 签名扩展（6 个参数替代 3 个），新增 `estimate_total_klines(symbol, interval, start_ts, end_ts)` 辅助
- `tests/test_data_fetcher.py`：更新 `progress_callback` mock 断言（6 参数）
- 新增 `check_data.py`（CLI）+ `tests/test_check_data_cli.py`
- `openspec/specs/data-fetcher/spec.md`：delta spec 更新进度上报契约
- 无运行时依赖变更；不修改数据库 schema；不修改任何 HTTP 路由
