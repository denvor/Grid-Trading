## Context

回测有时需要 5–30 秒（大量 K 线 + 网格循环），当前 POST /backtest 是同步阻塞后整体重定向到 result.html，浏览器只是转圈。

## Goals / Non-Goals

**Goals:**
- 在浏览器内建"终端窗口"，实时显示回测进度
- 使用 SSE (text/event-stream) 推送给浏览器
- 现有 `POST /backtest` 路由作为 fallback 保留（旧浏览器 / 直接 URL 访问仍可用）
- `engine.backtest()` 对外签名不变（progress_callback=None 即无回调）

**Non-Goals:**
- 不做 WebSocket（SSE 是单向足以够用）
- 不做多 job 排队 / 取消 job（单点回测+session）
- 不把进度持久化到 DB（内存够用）
- 不引入前端框架（原生 EventSource）

## Decisions

### D1：SSE endpoint 形式

`GET /backtest/stream?symbol=&interval=&capital=&upper_price=&lower_price=&grid_size=&quantity_per_grid=&start_time=&end_time=`

- GET 参数易于在 `<a>` 链接 / `window.open` / `EventSource` 直接消费
- 参数与现有 POST /backtest 表单字段对齐
- 返回 `text/event-stream`，chunked transfer

### D2：SSE 事件格式

三个事件类型：

```
event: progress
data: {"percent": 60, "kline_index": 36000, "total_klines": 60000,
        "elapsed_ms": 8000, "eta_ms": 5000, "trades": 128}

event: log
data: "[12:34:56] K线 36000/60000  价格 65230  买入 10 笔  卖出 8 笔"

event: done
data: {"result": {...}, "elapsed_ms": 13200}
```

前端根据 event type 分别渲染：
- `progress` → 终端行（单行更新进度条）
- `log` → 追加到 backlog（保留最近 N 行）
- `done` → 解析 result，客户端渲染 result 卡片（不再重定向）

### D3：进度回调注入位置

`engine.backtest()` 的热点循环是 `for kline in klines:`。每 CALLBACK_INTERVAL 根调用一次（默认 100 根 或 每 1%，取较大者）：

```python
CALLBACK_EVERY = max(1, min(100, total_klines // 100))

for i, kline in enumerate(klines):
    ...
    if progress_callback and i % CALLBACK_EVERY == 0:
        elapsed = perf_counter() - t0
        eta = (elapsed / max(i, 1)) * (total_klines - i)
        progress_callback(percent=... kline_index=i+1, ... )
```

回调开销：O(1)，占总时间 < 0.1%，符合"zero cost when unused"。

### D4：结果渲染方式

`done` 事件后，前端把 result 内联渲染在当前页面（移除终端窗口、显示与 result.html 一致的 metric 卡片）。**好处**：不跳转、不重发请求。**额外代价**：前端要有一点渲染逻辑。

为简化，也可选择 `window.location = '/backtest/result?jobid=XXX'` 模式——但需要后端缓存 result。这里选择：前端拿到 `done.result` 后直接 render，无额外 route。

### D5：旧 POST fallback

`POST /backtest` 保留，但不走 SSE。直接调 `backtest()` 然后 redirect 到 result。非 JS 浏览器仍可用。同时在 template 里把 form 的 `action` 改成 `onsubmit="return startStreamBacktest()"`；`startStreamBacktest()` 内部：
1. 序列化表单为 query params
2. 显示终端容器
3. `new EventSource('/backtest/stream?' + params)`
4. `return false` 阻止原生 POST

### D6：进度条 UI 风格

终端窗口 CSS：黑底绿字/青字，`font-family: monospace`，`overflow-y: auto`，`height: 320px`。进度行用 ANSI-ish 颜色（青=#0ff 进度条，绿=#0f0 成交统计）。与 Bootstrap 5、glassmorphism 风格并存。

## Risks / Trade-offs

| 风险 | 规避 |
|------|------|
| SSE 代理被 corporate proxy 缓冲 | 生产环境少用；本地 dev 无此问题 |
| 长连接被浏览器并发连接限制（6/域） | 回测默认单用户独占；高峰不常见 |
| `EventSource` 不支持 POST | 走 GET 参数（参数已在 URL 可见，非机密） |
| 客户端 JS 渲染 result 与 result.html 模板逻辑重复 | 复用量少；结果数据结构化，JS 简单展开 |
| progress_callback 引发微秒级延迟累积 | max(1%, 100根) 节流；回调极轻 |

## Migration Plan

1. 改 `engine.backtest()` 加 progress_callback
2. 加 `stream_backtest` 路由
3. 改 index.html 表单 + 终端容器
4. 加 tests
5. 跑全量回归

## Open Questions

- 客户端渲染 result 卡片 vs 重定向 /result → 选择"客户端渲染"（无跳转更顺畅）
- CALLBACK_EVERY 确切值 → 取 `max(1, total_klines // 200)` 即每 0.5% 推一次，上限 200 次推送/run，浏览器负担微乎其微
