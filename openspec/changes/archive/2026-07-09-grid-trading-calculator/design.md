## Context

当前项目为空目录，仅有 `CLAUDE.md` 和 `.gitignore`。需要从零搭建一个本地运行的网格交易测算工具，技术栈为 Flask + Jinja2，使用 `venv` 虚拟环境。无数据库、无外部 API，纯测算工具。

## Goals / Non-Goals

**Goals:**

- 提供 Web 表单让用户输入网格交易参数（资金、杠杆、网格大小、上下限、方向）
- 实现核心测算引擎，计算爆仓价、安全边际、最大回撤、单次网格收益
- 在结果页展示安全性评估（✅安全 / ⚠️警告 / 💥危险）和参数建议
- 保持轻量：单页输入→单页输出，无 JS 框架，本地 `flask run`

**Non-Goals:**

- 不做收益/年化测算（需历史数据和波动率假设，超出初版范围）
- 不做回测、实时价格、交易所 API 集成
- 不做用户系统、数据库、多币种切换

## Decisions

### 1. 币种配置模块

`config.ini` 声明每种币种的缺省参数（入场价、上下限%、网格大小、单次购买量、初始资金）。`app/config_loader.py` 加载并提供给表单首屏渲染和币种切换。

```ini
[BTCUSDT]
name = Bitcoin
entry_price = 65000
upper_pct = 10
lower_pct = 10
grid_size = 500
quantity_per_grid = 0.01
capital = 1000
```

理由：不同币种价格量级不同，固定缺省值有助于用户快速输入；新增币种只需加 ini section。

### 2. 测算引擎：独立纯函数模块

`app/calculator.py` 实现所有计算逻辑，零 Flask 依赖。理由：
- 纯函数便于单元测试和独立验证
- 可在 Web 之外复用（CLI、脚本、未来 API）

核心公式（以做多为例）：
- 爆仓价 = 入场价 × (1 - 1/杠杆)（简化的全仓模型，忽略资金费率与手续费）
- 安全边际 = (网格下限 - 爆仓价) / 爆仓价，正数则安全
- 网格数量 = ceil((上限 - 下限) / 网格大小)
- 单次网格名义价值 = 单次购买数量 × 入场价
- 单次网格利润 = 单次购买数量 × 网格大小（价差 × 数量，与杠杆无关）
- 总占用资金 = 单次名义价值 × 网格数量 / 杠杆（杠杆越高，实际占用保证金越少）
- 剩余资金 = 初始资金 - 总占用资金
- 最大回撤 = (入场价 - 下限) / 入场价 × 杠杆 × 100%

### 3. Flask 应用结构

```
GridTrading/
├── app/
│   ├── __init__.py         # Flask 工厂
│   ├── calculator.py       # 测算核心（纯函数）
│   ├── config_loader.py    # 加载 config.ini
│   ├── routes.py           # /
│   └── templates/
│       ├── base.html       # 公共模板
│       ├── index.html      # 输入表单
│       └── result.html     # 测算结果
├── config.ini              # 币种缺省参数
├── .gitignore
├── CLAUDE.md
├── requirements.txt
└── venv/                   # 不入库
```

### 4. 表单数据保留策略

- **首屏（GET /，无 querystring）**：服务端用首币种配置渲染缺省值，input 有 value
- **从结果页返回（GET /?symbol=...&...）**：服务端从 querystring 恢复用户输入渲染表单
- **校验失败重新渲染**：服务端带 `form=request.form` 渲染
- **切换币种**：JS 读取 `<select>` 的 data-* 属性，仅在字段为空时填充（用户手动改过的值不覆盖）

### 3. 计算精度：`decimal.Decimal`

金融计算避免浮点误差，所有价格 / 金额运算使用 `Decimal`。理由：
- 网格价格间距和杠杆除法对精度敏感
- Python 标准库自带，无额外依赖

### 4. 方向：先仅做多

初版仅支持**做多（Long）**。做空和中性网格可在后续扩展，避免初版复杂度膨胀。表单中方向字段暂为固定值。

### 5. 前端：原生 HTML + 轻量 CSS

不使用 JS 框架。表单提交即刷新页面展示结果，保持零构建步骤、零前端依赖。

## Risks / Trade-offs

- **[Risk]** 简化的爆仓价公式未计入资金费率、手续费、维持保证金 → [Mitigation] 在结果页明显标注「全仓简化模型」，后续可扩展逐仓参数
- **[Risk]** 无实时价格输入 → [Mitigation] 用户输入入场价作为参考基准，测算结果以相对百分比呈现，不依赖实际行情
- **[Trade-off]** Decimal 精度带来的性能开销 → [Mitigation] 测算规模极小（单次 HTTP 请求内几十次运算），可忽略
