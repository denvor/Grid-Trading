## ADDED Requirements

### Requirement: 回测参数输入表单
系统 SHALL 提供回测参数输入页面，收集以下参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | 枚举 | 是 | 交易对，从 config.ini 加载 |
| interval | 枚举 | 是 | K线周期：1m / 5m / 15m / 1h / 4h |
| capital | 正数 | 是 | 初始资金 (USDT) |
| upper_price | 正数 | 是 | 网格上限 |
| lower_price | 正数 | 是 | 网格下限 |
| grid_size | 正数 | 是 | 网格间距 (USDT) |
| quantity_per_grid | 正数 | 是 | 单次购买数量 (币) |
| start_time | 日期时间 | 是 | 回测开始时间 |
| end_time | 日期时间 | 是 | 回测结束时间 |
| force_refresh | 布尔 | 否 | 强制刷新数据库缓存（默认 false） |

#### Scenario: 提交完整参数
- **WHEN** 用户填写所有必填字段并提交
- **THEN** 系统执行回测并展示结果页面

#### Scenario: 缺少必填字段
- **WHEN** 用户未填写某个必填字段就提交
- **THEN** 系统提示该字段为必填，不执行回测

#### Scenario: 逻辑校验失败
- **WHEN** 用户提交 lower_price ≥ upper_price
- **THEN** 系统提示"网格下限必须小于上限"

#### Scenario: 时间范围校验
- **WHEN** 用户提交 start_time ≥ end_time
- **THEN** 系统提示"开始时间必须早于结束时间"

#### Scenario: 时间跨度过大
- **WHEN** 用户请求时间跨度超过 2 年
- **WHEN** 1m 周期下数据量可能超过 100 万根
- **THEN** 系统提示"时间跨度过大，建议缩小范围或选择更大周期"

### Requirement: 回测结果展示
系统 SHALL 在结果页清晰展示回测统计和收益曲线。

#### Scenario: 关键指标卡片
- **WHEN** 回测完成
- **THEN** 系统展示：总收益率、最大回撤、胜率、交易次数、初始资金、最终资金

#### Scenario: 收益曲线
- **WHEN** 回测完成
- **THEN** 系统展示资金变化曲线（SVG 折线图），X轴=时间，Y轴=资金

#### Scenario: 交易明细列表
- **WHEN** 回测完成且交易次数 > 0
- **THEN** 系统展示每笔成交的时间、方向（买/卖）、价格、数量、利润

#### Scenario: 回测耗时提示
- **WHEN** 数据量 > 2000 根K线
- **THEN** 系统在结果页标注"数据量较大，计算耗时 X 秒"

### Requirement: 与现有测算工具集成
系统 SHALL 回测功能与现有网格测算工具并列，共享导航和配置。

#### Scenario: 导航切换
- **WHEN** 用户在任意页面
- **THEN** 系统提供"网格测算"和"回测"两个入口的导航

#### Scenario: 配置复用
- **WHEN** 用户选择交易对
- **THEN** 系统从 config.ini 加载默认参数（入场价、网格大小等）
