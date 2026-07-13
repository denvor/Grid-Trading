## Why

现有工具只能做静态参数测算（会不会爆仓、单次利润多少钱），无法验证网格策略在真实历史行情中的表现。通过接入币安公开K线数据接口，让用户用历史数据回测自己的网格参数，看到实际收益率、最大回撤、胜率等关键指标，从而更有信心地投入真金白银。

## What Changes

- 新增独立回测引擎模块，通过币安公开 API 获取历史K线数据（无需 API Key）
- 实现网格策略回测逻辑：遍历K线，模拟挂单成交，统计每笔网格利润
- 回测结果页面：总收益率、最大回撤、胜率、交易次数、收益曲线
- 新增数据获取模块，支持多时间周期（1h/4h/1d）和多交易对
- 复用现有 `config.ini` 中的币种配置

## Capabilities

### New Capabilities

- `data-fetcher`: 从币安公开 API 获取历史K线数据，支持多周期、分页获取
- `backtest-engine`: 核心回测逻辑，基于 OHLCV 数据模拟网格策略执行，输出完整回测统计
- `backtest-ui`: 回测参数输入表单 + 结果可视化展示

### Modified Capabilities

无（全新功能，不修改现有 spec）

## Impact

- **代码**: 新增 `app/backtest/` 目录（data_fetcher.py / engine.py / routes.py），新模板 `app/templates/backtest_*.html`
- **依赖**: 仅使用 Python 标准库 `urllib`（无需额外 pip 包），与现有 `decimal` 精度保持一致
- **API**: 调用币安公开接口 `https://api.binance.com/api/v3/klines`（无需 API Key）
- **UI**: 新增 `/backtest` 路由，与现有 `/` 测算页面并列
- **CLAUDE.md**: 无需修改（保持无数据库、纯测算工具的定位）
