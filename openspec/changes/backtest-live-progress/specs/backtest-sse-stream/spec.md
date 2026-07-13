## ADDED Requirements

### Requirement: SSE 流式回测路由
系统 SHALL 暴露 `GET /backtest/stream?symbol=&interval=&capital=&upper_price=&lower_price=&grid_size=&quantity_per_grid=&start_time=&end_time=` 路由，返回 `text/event-stream`，并通过 SSE 事件推送回测进度。

#### Scenario: 成功启动流
- **WHEN** 参数齐全且数据库有 K 线
- **THEN** 流立即发送 `retry: 5000` 与一个初始 `event: progress`（percent 0），开启回测

#### Scenario: 参数校验失败
- **WHEN** 缺必填字段或数值非法
- **THEN** 返回 HTTP 400，JSON body，不建立 SSE流

#### Scenario: K 线未缓存
- **WHEN** 数据库中无请求 symbol/interval/范围的数据
- **THEN** 发送 `event: error` data `{"error": "数据库中没有 ..."}`，关闭流

### Requirement: progress 事件推送
每处理约 1% 进度（最少每 100 根），系统 SHALL 推送一个 `event: progress` 事件，JSON 体为 `{percent, kline_index, total_klines, elapsed_ms, eta_ms, trades_count}`。

#### Scenario: 进度单调递增
- **WHEN** 流进行中
- **THEN** 连续 `progress` 事件的 `percent` 单调非递减，从 0 到 100

#### Scenario: eta_ms 稳定收敛
- **WHEN** 流接近尾声
- **THEN** `eta_ms` 趋势向 0，不会负值

### Requirement: done 事件
回测完毕，系统 SHALL 推送 `event: done`，data 包含完整回测结果 JSON（与现有 result.html 渲染所需字段相同）。

#### Scenario: done 事件包含所有统计字段
- **WHEN** 回测完成
- **THEN** 推送 `event: done` data = `{"result": {total_return_pct, ..., curve_points, ...}, "elapsed_ms": N}`

#### Scenario: done 事件后关闭连接
- **WHEN** `done` 已推送
- **THEN** SSE 连接关闭，浏览器 `EventSource` 触发 `onerror` 或自然结束

### Requirement: 错误事件
若回测过程中抛异常（K 线未找到、数值非法），系统 SHALL 推送 `event: error` data `{"error": "具体原因"}` 并关闭流。

#### Scenario: 异常可序列化
- **WHEN** 出现任何未捕获异常
- **THEN** 错误消息_serialize 为 JSON 并不含敏感路径

### Requirement: HTTP 头正确
系统 SHALL 返回 `Content-Type: text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`（关闭 nginx 缓冲）。

#### Scenario: 浏览器识别为流
- **WHEN** EventSource 连接
- **THEN** 浏览器立即识别为 SSE 流，事件实时触发（不缓冲到结束）
