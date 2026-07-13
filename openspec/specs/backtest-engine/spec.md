## Purpose
基于历史 K 线数据模拟网格策略执行，输出完整回测统计（收益率、最大回撤、胜率、交易次数）。

## Requirements

### Requirement: 网格策略回测模拟
系统 SHALL 基于历史K线数据模拟网格策略执行，输出完整回测统计。

#### Scenario: 基础回测流程
- **WHEN** 用户提供参数 (symbol, interval, capital, grid_range, grid_size, quantity, 时间范围)
- **THEN** 系统遍历K线模拟网格挂单成交，输出总收益率、最大回撤、胜率、交易次数

#### Scenario: 网格挂单成交判断
- **WHEN** 某根K线的价格区间 [low, high] 触达网格线价格
- **THEN** 系统判定该网格成交，以网格线价格买入/卖出 quantity 数量的币

#### Scenario: 买入后挂卖单
- **WHEN** 某网格买入成交后
- **THEN** 系统在上方 grid_size 价格处挂一个同数量的卖单

#### Scenario: 卖出后挂买单
- **WHEN** 某网格卖出成交后
- **THEN** 系统在下方 grid_size 价格处挂一个同数量的买单

### Requirement: 回测统计指标
系统 SHALL 计算并输出以下关键指标。

#### Scenario: 总收益率计算
- **WHEN** 回测完成
- **THEN** 系统输出总收益率 = (最终资金 - 初始资金) / 初始资金 × 100%

#### Scenario: 最大回撤计算
- **WHEN** 回测完成
- **THEN** 系统输出最大回撤 = max((峰值 - 谷值) / 峰值 × 100%)，遍历整个资金曲线

#### Scenario: 胜率计算
- **WHEN** 回测完成
- **THEN** 系统输出胜率 = 盈利交易次数 / 总交易次数 × 100%

#### Scenario: 交易明细
- **WHEN** 回测完成
- **THEN** 系统输出每笔成交记录（时间、方向、价格、数量、利润）

### Requirement: 资金与持仓管理
系统 SHALL 在回测过程中正确管理资金和持仓状态。

#### Scenario: 买入时扣减资金
- **WHEN** 网格买入成交
- **THEN** 系统扣减资金（价格 × 数量），增加持仓

#### Scenario: 卖出时增加资金
- **WHEN** 网格卖出成交
- **THEN** 系统增加资金（价格 × 数量），减少持仓

#### Scenario: 资金不足时停止买入
- **WHEN** 剩余资金不足以在当前最低价挂单买入
- **THEN** 系统不再新开买入网格，仅执行已有挂单的卖出

### Requirement: 精度保证
系统 SHALL 所有金额运算使用 `Decimal` 类型，最终结果量化到 2 位小数。

#### Scenario: 利润计算精度
- **WHEN** 计算单笔网格利润
- **THEN** 利润 = (卖价 - 买价) × 数量，结果量化到 2 位小数
