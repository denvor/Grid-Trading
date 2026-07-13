## ADDED Requirements

### Requirement: 进度回调契约
`engine.backtest()`  SHALL 接受可选关键字参数 `progress_callback: Callable[[int, int, int, int, int], None] | None = None`。

#### Scenario: 无回调时行为不变
- **WHEN** 调用 `backtest(klines, capital, upper_price, lower_price, grid_size, quantity_per_grid)`
- **THEN** 行为与当前完全一致，不产生任何回调调用

#### Scenario: 有回调时每 N 根触发
- **WHEN** 传入 `progress_callback` 函数，K 线数为 10000
- **THEN** `progress_callback` 被调用约 50–200 次（每 0.5%–1% 一次或每 100 根一次，取较大者）

### Requirement: 回调参数语义
每次回调的 5 个参数 SHALL 含义为：`percent`（0–100 整数）、`kline_index`（已处理根数）、`total_klines`、`elapsed_ms`（毫秒）、`trades_count`（截至目前成交笔数）。

#### Scenario: percent 单调递增
- **WHEN** 连续回调
- **THEN** `percent` 非递减，最终达到 100

#### Scenario: trades_count 与最终结果一致
- **WHEN** 最后一个 `percent == 100` 的回调
- **THEN** `trades_count` 等于 `result["total_trades"]`

### Requirement: 回调零开销
`progress_callback=None` 路径 SHALL 不产生额外函数调用或时间开销超过 0.1%。

#### Scenario: None 路径不调用
- **WHEN** `progress_callback=None`
- **THEN** 计算过程中不产生任何回调相关函数调用
