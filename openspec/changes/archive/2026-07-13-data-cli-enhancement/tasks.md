# Data CLI Enhancement 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 改进 fetch_data 进度的"可预期性"，并提供独立的 check_data.py 查看数据库现状。

**Architecture:** progress_callback 签名从 3 参数扩展为 6 参数（fetched, estimated_total, page, total_pages, eta_seconds, last_kline_ts），通过 try/except TypeError 向下兼容旧 3 参数回调；CLI 调用方负责渲染 ASCII 进度条，并把 `last_kline_ts` 毫秒时间戳格式化为 `(当前 YYYY-MM-DD HH:MM)` 一列。check_data.py 复用 database.py 现有函数，通过分页流式统计时间戳间隔来算中位数和空洞。

**Tech Stack:** Python 3.12+ 标准库（argparse, shutil.get_terminal_size, time.perf_counter）；无第三方依赖。

---

## 1. 数据获取进度扩展

- [x] 1.1 在 `app/backtest/data_fetcher.py` 中修改 `fetch_klines_paginated`：循环开始前计算 `estimated_total = (end_ts - start_ts) // (interval_seconds * 1000) + 1`，每页完成时刷新 `last_ts = klines[-1]["timestamp"]`（跳页时取 `current_end` 末点），用 6 参数调用 `progress_callback(fetched, estimated_total, page, total_pages, eta, last_ts)`
- [x] 1.2 在 `progress_callback` 调用外套一层 `try/except TypeError`，失败时回退调旧 3 参数版本 `progress_callback(fetched, current_end, end_ts)`
- [x] 1.3 `time.perf_counter()` 记录起始时间，每页算出 elapsed 与 eta
- [x] 1.4 新增公开辅助函数 `estimate_total_klines(symbol, interval, start_ts, end_ts) -> int`

验证：`pytest tests/test_data_fetcher.py -q` 全绿；检查 mock 断言中 `progress_callback.call_args` 已按 6 参数适配。

## 2. fetch_data.py 进度渲染

- [x] 2.1 改 `fetch_data.main()` 内的 `_progress_callback` 函数：签名改为 `(fetched, estimated_total, page, total_pages, eta, last_kline_ts)`，渲染格式 `[#####.....] 60%  已获取 X/Y  (当前 YYYY-MM-DD HH:MM)  用时 Zs  预计剩余 Ws`
- [x] 2.2 进度条宽度通过 `shutil.get_terminal_size()` 自适应（最小 40 列），填充 `#`，空白 `.`
- [x] 2.3 启动时打印 `[预计 N 根]` 一行（预估值单独在 main() 里算一次）
- [x] 2.4 跳页回调渲染一行 `  ✓ 跳过第 page/total_pages 页（已在库）`
- [x] 2.5 完成摘要改为 `完成！获取 X 根K线（预估 Y），存入数据库 Z 条（跳过 W 页已有数据）`

验证：`pytest tests/test_fetch_data_cli.py -q` 全绿；新增断言覆盖预判总量、进度条汇总行 ETA 字段格式、当前 K 线时间格式（`YYYY-MM-DD HH:MM`）。

## 3. 新增 check_data.py CLI

- [x] 3.1 创建 `/home/denvor/work/GridTrading/check_data.py`：argparse 接受 `--symbol` / `--interval` / `--gap-threshold` / `--json`
- [x] 3.2 无过滤时调 `list_symbol_intervals`，对每个组合调 `count_klines`，打印汇总表
- [x] 3.3 有过滤时调 `query_klines_paginated`（每页 5000），流式扫描相邻间隔算中位数 + 标记空洞
- [x] 3.4 `--json` 分支：输出 JSON 列表/对象，timestamp 一律毫秒
- [x] 3.5 数据库为空 / 找不到匹配的分支友好提示

验证：单元测试见 Task 4。

## 4. 新增测试

- [x] 4.1 创建 `/home/denvor/work/GridTrading/tests/test_check_data_cli.py`
- [x] 4.2 `test_check_all_lists_symbols_intervals`：tmp_db 插入 2 个 symbol × 2 个 interval，验证输出行数
- [x] 4.3 `test_check_symbol_filter`：加 `--symbol BTCUSDT`，验证 ETH 行被过滤
- [x] 4.4 `test_check_gap_detection`：在 100 根后插入 4h 间隔，验证空洞数 ≥ 1（gap-threshold=1.5）
- [x] 4.5 `test_check_empty_db`：空库友好提示
- [x] 4.6 `test_check_json_output`：`--json` 输出可被 `json.loads` 解析

验证：`pytest tests/test_check_data_cli.py -q` 全绿。

## 5. 回归

- [x] 5.1 全量测试：`pytest tests/ -q` 应当 89+N 全绿（N 为本次新增用例）
