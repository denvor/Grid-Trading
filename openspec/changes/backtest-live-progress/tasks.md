# Backtest Live Progress 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在浏览器终端窗口内实时显示回测进度，通过 SSE 推送。

**Architecture:** `engine.backtest()` 增加可选 `progress_callback`，每 ~1% 进度调用一次；`/backtest/stream` GET 路由调起回测并推送 `progress` / `done` / `error` 事件；前端 `templates/backtest/index.html` 阻止默认 POST，改用 EventSource _CONN，把进度追加到"终端容器"，完成后本地渲染 result。

**Tech Stack:** Python 3.12+ 原生 + Flask `stream_with_context`；原生 `EventSource`；无第三方。

---

## 1. Engine 改造

- [x] 1.1 在 `app/backtest/engine.py` 修改 `backtest()` 签名：新增 `progress_callback=None`
- [x] 1.2 在 `for i, kline in enumerate(klines):` 循环内按 `CALLBACK_EVERY = max(1, total_klines // 200)` 节流，触发回调
- [x] 1.3 回调参数按 D2 设计：`(percent, kline_index, total_klines, elapsed_ms, trades_count)`
- [x] 1.4 确保 `progress_callback=None` 路径零开销

验证：现有 tests/test_backtest_engine.py 全绿；新参数不影响行为。

## 2. 新增 SSE 路由

- [x] 2.1 在 `app/backtest/routes.py` 新增 `GET /backtest/stream`，返回 `Response(stream_with_context(...), mimetype='text/event-stream')`
- [x] 2.2 校验参数（复用 `_parse_and_validate` 逻辑或抽出新 helper `_parse_stream_query`），参数非法返回 400
- [x] 2.3 从 DB 拉 K 线，无数据推 `event: error`
- [x] 2.4 调 `fetch_interval_summary` 或 `count_klines_in_range` 预判总行数，告知前端（`total_klines`）
- [x] 2.5 调 backtest() 时传 `progress_callback`，每次回调写 `event: progress` SSE 帧
- [x] 2.6 回测结束写 `event: done`，最终数据包含完整 result
- [x] 2.7 异常捕获 → `event: error` 帧 + 关闭

验证：`curl -N http://localhost:5000/backtest/stream?...` 可见 SSE 帧。

## 3. 前端改造

- [x] 3.1 在 `templates/backtest/index.html` 新增 `#terminal` 容器 + `#result-inline` 容器，默认隐藏
- [x] 3.2 新增 `#terminal` 的 CSS（monospace 终端风，黑底青字）
- [x] 3.3 改造 `<form onsubmit="return startStreamBacktest()">`，`startStreamBacktest()`：
  - 序列化表单字段为 URL query params
  - 显示 #terminal、清空 backlog
  - `const es = new EventSource('/backtest/stream?' + params)`
  - `es.addEventListener('progress', ...)` 追加进度行（替换上一行进度条）
  - `es.addEventListener('done', ...)` 关闭 es、渲染行内 result
  - `es.addEventListener('error', ...)` 提示错误（可能是 SSE 错误帧或连接断开）
  - return false
- [x] 3.4 简单实现行内 result 渲染：用 result 字典里的 metric 字段填充 ~4 个 metric 卡片

验证：浏览器手动访问 /backtest，填参，点"开始回测"，观察进度。

## 4. 新增测试

- [x] 4.1 新增 `tests/test_backtest_stream.py`：
  - 4.1.1 `test_progress_callback_called`：小K线数据，`progress_callback` mock 验证被调用、最终 percent==100
  - 4.1.2 `test_result_unchanged_with_callback`：对比 with/without callback 最终 result 相同（数学不变）
  - 4.1.3 `test_stream_returns_400_on_missing_params`
  - 4.1.4 `test_stream_returns_error_event_on_missing_klines`
  - 4.1.5 `test_stream_done_event_includes_result`

验证：`pytest tests/test_backtest_stream.py -q` 全绿。

## 5. 回归

- [x] 5.1 全量测试：`pytest tests/ -q` 全绿

## 6. Fallback 保留

- [x] 6.1 确认 `POST /backtest` 仍存在且行为不变（不构建终端页面，直接返回 result.html）
- [x] 6.2 在 index.html 中 JS fallback：若 `EventSource` 不支持（IE），仍走原生 POST
