## Context

现有工具是静态参数测算（爆仓价、安全等级、单次利润），用户输入参数后得到理论值。但用户更想知道：**这套参数在过去 3 个月真实行情中能赚多少钱？** 需要新增回测功能，接入币安公开K线数据，模拟网格策略在历史数据上的表现。

技术栈与现有工具一致：Flask + Jinja2 + `decimal.Decimal` 高精度运算。新增 SQLite 本地数据库存储K线数据（避免重复请求 API）。

**网络环境**：访问 `api.binance.com` 需要通过代理 `http://127.0.0.1:20171`。

## Goals / Non-Goals

**Goals:**

- 从币安公开 API 获取历史K线数据（OHLCV），无需 API Key
- 数据存入本地 SQLite 数据库缓存，避免重复请求
- 实现网格策略回测引擎：遍历K线，模拟网格挂单成交
- 输出回测统计：总收益率、最大回撤、胜率、交易次数、每笔利润列表
- 回测结果可视化：收益曲线（前端轻量 SVG/Canvas，无外部图表库）
- 与现有测算工具并列，共享 `config.ini` 币种配置

**Non-Goals:**

- 不做实时回测（仅历史数据）
- 不做机器学习/参数优化
- 不接入 API Key 私有数据（仅公开K线）
- 不做多策略对比（仅网格策略）

## Decisions

### 1. 数据获取：独立 CLI + 币安公开 API + SQLite 缓存

**独立命令行工具** `fetch_data.py`（项目根目录）：

```bash
python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01
python fetch_data.py --symbol ETHUSDT --interval 15m --start 2024-06-01 --end 2024-06-30 --force
```

与 Web 应用解耦：
- 用户先运行 CLI 拉取数据到数据库
- 回测 Web 页面直接读数据库，无需网络
- 避免浏览器请求超时问题

API 细节：
- `https://api.binance.com/api/v3/klines`，无需 API Key
- 单次最多 1000 根K线，分页获取（调整 `startTime`/`endTime`）
- 支持周期：1m、5m、15m、1h、4h
- 数据字段：`[timestamp, open, high, low, close, volume, ...]`，仅取 OHLCV
- 使用标准库 `urllib.request` + `sqlite3`，无额外依赖

配置（`config.ini`）：
- `proxy` = `http://127.0.0.1:20171`
- `request_interval` = `1.0` 秒（每次请求间隔，避免限流）

数据库缓存：相同 (symbol, interval, timestamp) 不重复存储，CLI 支持 `--force` 强制刷新

### 2. 回测引擎：逐K线模拟

核心逻辑：

```
初始化: 资金 = capital, 持仓 = 0, 网格列表 = []
对每根K线 (按时间顺序):
  1. 检查是否有网格挂单在当前K线的 [low, high] 范围内成交
  2. 成交后: 更新持仓/资金, 在对手侧挂新单（买成后挂卖单, 卖成后挂买单）
  3. 记录每笔交易的利润
  4. 更新资金曲线
输出: 总收益率, 最大回撤, 胜率, 交易次数, 资金曲线
```

网格挂单规则：
- 入场价上下各挂 N 个网格（N = (upper - lower) / grid_size）
- 价格到达网格线时，以该价格成交（简化：用K线 high/low 判断是否触达）
- 每格买入 quantity_per_grid 币，卖出时获得价差利润

### 3. 精度处理

与现有工具一致，所有金额运算使用 `decimal.Decimal`，最终输出 quantize 到 2 位小数。

### 4. 前端展示

- 回测参数表单：复用现有 DeFi 玻璃主题
- 结果页：关键指标卡片 + 收益曲线（轻量 SVG，无外部依赖）
- 收益曲线：用 SVG polyline 绘制资金变化，纯前端生成

### 5. 数据库设计

SQLite 数据库（路径见 `config.ini` → `database.path`，默认 `data/klines.db`，`.gitignore` 入库）：

```sql
CREATE TABLE klines (
    symbol TEXT NOT NULL,          -- BTCUSDT
    interval TEXT NOT NULL,        -- 1h
    timestamp INTEGER NOT NULL,    -- 毫秒时间戳
    open TEXT NOT NULL,            -- Decimal 用 TEXT 存储保精度
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT NOT NULL,
    PRIMARY KEY (symbol, interval, timestamp)
);
```

查询时 `Decimal(open)` 转换。`(symbol, interval, timestamp)` 复合主键保证幂等。

### 6. 模块结构

```
fetch_data.py          # ← 独立 CLI 工具（项目根目录）
app/backtest/
├── __init__.py        # Blueprint 注册
├── data_fetcher.py    # 币安 API 数据获取 + DB 读写（CLI + Web 共用）
├── engine.py          # 回测核心逻辑
└── routes.py          # /backtest 路由
data/
└── klines.db          # SQLite 数据库（不入 git）
```

`fetch_data.py` 是一个独立可执行脚本，导入 `app/backtest/data_fetcher.py` 中的函数，
通过 `config.ini` 读取 `proxy` 和 `request_interval`，循环分页获取并 sleep 间隔。

## Risks / Trade-offs

- **[Risk]** 币安 API 限流（1200 req/min）→ [Mitigation] 数据库缓存避免重复请求，首次拉取后后续秒开
- **[Risk]** 简化成交模型（用 high/low 判断触达）可能与真实订单簿有偏差 → [Mitigation] 在结果页标注"简化模型，未考虑滑点和深度"
- **[Trade-off]** 回测计算在请求同步完成，大数据量（>3000根）可能耗时 1-2 秒 → [Mitigation] 暂不做异步，后续可扩展
- **[Risk]** 代理不可用时 API 调用失败 → [Mitigation] 配置可切换（环境变量 `BINANCE_PROXY`），不可用时提示用户
