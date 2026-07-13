## Why

回测 6 万根 K 线（BTCUSDT 1h 全历史）时，`engine.backtest()` 在主线程跑 5–30 秒，浏览器只是转圈，用户不知道是卡了还是在做进度。提交 POST /backtest 后没有任何中间反馈，体验像"假死"。

需要一种**近终端风格**的实时进度视图：能在页面上看到当前处理到第几根 K 线、百分比、已成交笔数、耗时、预计剩余。

## What Changes

### 新增能力

- `engine.backtest()` 支持可选的 `progress_callback(percent, kline_index, total_klines, elapsed_ms, trades_count)` —— 每处理 N 根 K 线回调一次，不阻塞主计算
- 新增 `GET /backtest/stream?symbol=&interval=&...` SSE 路由：拉取 K 线 → 跑回测（带回调）→ 每 0.5 秒或每 1% 进度推送一个事件给浏览器；最终事件 `done` 携带结果 JSON
- `templates/backtest/index.html` 改造：
  - 表单提交时阻止默认 POST、改为 JS fetch `/backtest/stream`
  - 显示一个**"终端窗口"容器**（`backlog` 风格：终端黑底 + 滚动输出）
  - 实时追加进度行（`[#####..] 60% | K线 36000/60000 | 成交 128 笔 | 用时 8s | ETA 5s`）
  - 结束后由后端 `done` 事件驱动 `location.href = '/backtest/result?jobid=...'` 或直接用返回的 HTML 渲染结果

### 改动能力

- 现有的 `POST /backtest` 路由保留作为非流式 fallback（旧浏览器 / 按回车直接访问时仍可用），**不删除**
- `engine.backtest()` 对外签名不变，`progress_callback` 默认 `None` —— 旧调用方零改动

## Capabilities

### New Capabilities

- `backtest-sse-stream`：基于 SSE 的实时进度回测，并把进度渲染为"终端窗口"

### Modified Capabilities

- `backtest-engine`：回测引擎增加可选 `progress_callback`，并在处理 K 线的热点循环内定期调用

## Impact

- `app/backtest/engine.py`：修改 `backtest()` 函数体，注入回调
- `app/backtest/routes.py`：新增 `stream_backtest()` 路由；保留原 `backtest_index()` 作为 fallback
- `app/templates/backtest/index.html`：改造表单提交 + 新增终端窗口 DOM + SSE 客户端 JS
- `tests/`：新增 tests/test_backtest_stream.py（mock progress_callback 调用频次与最终答案不变）
- 静态资源无新增；无 npm / 框架依赖；纯原生 `EventSource`（IE 不支持但项目不要求 IE）
