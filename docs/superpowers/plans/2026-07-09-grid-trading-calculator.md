# Grid Trading Calculator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个本地运行的加密货币网格交易测算工具，用户通过 Web 表单选择币种并输入参数，系统返回爆仓价、安全等级、网格分布、资金占用、最大回撤及参数建议。

**Architecture:** 纯函数测算引擎 (`app/calculator.py`) + 币种配置加载 (`app/config_loader.py`) + Flask Web 层 (`app/routes.py`) + Jinja2 模板。测算引擎零 Flask 依赖，便于单测。所有金额运算使用 `decimal.Decimal`。首屏服务端渲染缺省值。

**Tech Stack:** Python 3.x, Flask, Jinja2, decimal（标准库）

---

## File Structure

```
GridTrading/
├── app/
│   ├── __init__.py          # Flask 工厂，create_app()
│   ├── calculator.py        # 测算核心：纯函数，零外部依赖
│   ├── config_loader.py     # 加载 config.ini
│   ├── routes.py            # / 路由（GET 表单 + POST 测算）
│   ├── templates/
│   │   ├── base.html        # 公共骨架
│   │   ├── index.html       # 输入表单（含币种下拉 + JS 填充缺省值）
│   │   └── result.html      # 测算结果（含资金占用展示）
│   └── static/
│       └── style.css        # 基础样式 + 安全/警告/危险三色
├── config.ini               # 币种缺省参数（BTC/ETH/BNB）
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py   # 测算引擎单测
│   ├── test_config_loader.py# 配置加载单测
│   └── test_routes.py       # Flask 路由集成测试
├── requirements.txt         # Flask
├── .gitignore
├── CLAUDE.md
└── venv/                    # 虚拟环境（不入 git）
```

---

## Task 1: 项目初始化 — venv + 依赖 + config

**Files:**
- Create: `requirements.txt`
- Create: `config.ini`
- Create: `tests/__init__.py`

- [ ] **Step 1: 创建虚拟环境并激活**

```bash
cd /home/denvor/work/GridTrading
python3 -m venv venv
source venv/bin/activate
```

- [ ] **Step 2: 创建 requirements.txt**

```text
Flask>=3.0
```

- [ ] **Step 3: 创建 config.ini**

```ini
[BTCUSDT]
name = Bitcoin
entry_price = 65000
upper_pct = 10
lower_pct = 10
grid_size = 500
quantity_per_grid = 0.01
capital = 1000

[ETHUSDT]
name = Ethereum
entry_price = 3500
upper_pct = 12
lower_pct = 12
grid_size = 30
quantity_per_grid = 0.1
capital = 1000

[BNBUSDT]
name = BNB
entry_price = 600
upper_pct = 15
lower_pct = 15
grid_size = 10
quantity_per_grid = 0.5
capital = 1000
```

- [ ] **Step 4: 安装依赖**

```bash
pip install -r requirements.txt
pip install pytest
```

- [ ] **Step 5: 创建 tests/__init__.py**

```python
# tests package
```

- [ ] **Step 6: 验证 pytest 可用并提交**

```bash
pytest --version
git init 2>/dev/null || true
git add requirements.txt config.ini tests/__init__.py .gitignore CLAUDE.md
git commit -m "chore: init project with venv, pytest, config.ini"
```

---

## Task 2: 配置加载模块

**Files:**
- Create: `app/__init__.py`
- Create: `app/config_loader.py`
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: 创建 app/__init__.py**

```python
# GridTrading app package
```

- [ ] **Step 2: 写失败测试**

`tests/test_config_loader.py`:

```python
from app.config_loader import get_symbols, get_symbol


class TestConfigLoader:
    def test_get_symbols_returns_list(self):
        symbols = get_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) >= 3

    def test_symbols_contain_btc(self):
        symbols = get_symbols()
        symbols_names = [s["symbol"] for s in symbols]
        assert "BTCUSDT" in symbols_names

    def test_btc_has_required_fields(self):
        btc = get_symbol("BTCUSDT")
        assert btc is not None
        assert "entry_price" in btc
        assert "upper_pct" in btc
        assert "lower_pct" in btc
        assert "grid_size" in btc
        assert "quantity_per_grid" in btc
        assert "capital" in btc

    def test_get_symbol_case_insensitive(self):
        assert get_symbol("btcusdt") is not None
        assert get_symbol("BTCUSDT") is not None

    def test_get_symbol_nonexistent_returns_none(self):
        assert get_symbol("FOOBAR") is None
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/test_config_loader.py -v
```

预期：`ImportError`

- [ ] **Step 4: 实现 config_loader.py**

`app/config_loader.py`:

```python
"""加载币种配置。"""
import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.ini")

_config = configparser.ConfigParser()
_config.read(CONFIG_PATH, encoding="utf-8")


def get_symbols() -> list[dict]:
    """返回所有币种配置列表。"""
    symbols = []
    for section in _config.sections():
        symbols.append({
            "symbol": section.upper(),
            "name": _config.get(section, "name"),
            "entry_price": _config.get(section, "entry_price"),
            "upper_pct": _config.get(section, "upper_pct"),
            "lower_pct": _config.get(section, "lower_pct"),
            "grid_size": _config.get(section, "grid_size"),
            "quantity_per_grid": _config.get(section, "quantity_per_grid"),
            "capital": _config.get(section, "capital"),
        })
    return symbols


def get_symbol(symbol: str) -> dict | None:
    """返回指定币种配置，不存在返回 None。"""
    for s in get_symbols():
        if s["symbol"] == symbol.upper():
            return s
    return None
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_config_loader.py -v
```

预期：6 个 PASS

- [ ] **Step 6: 提交**

```bash
git add app/__init__.py app/config_loader.py tests/test_config_loader.py
git commit -m "feat(config): add config-loader for symbol defaults"
```

---

## Task 3: 测算引擎 — 爆仓价

**Files:**
- Create: `app/calculator.py`
- Create: `tests/test_calculator.py`

- [ ] **Step 1: 写失败测试**

`tests/test_calculator.py`:

```python
from decimal import Decimal
from app.calculator import calculate_liquidation_price


class TestCalculateLiquidationPrice:
    """测试爆仓价计算：爆仓价 = 入场价 × (1 - 1/杠杆)"""

    def test_5x_leverage(self):
        result = calculate_liquidation_price(Decimal("100"), Decimal("5"))
        assert result == Decimal("80.00")

    def test_1x_leverage(self):
        result = calculate_liquidation_price(Decimal("100"), Decimal("1"))
        assert result == Decimal("0")

    def test_10x_leverage(self):
        result = calculate_liquidation_price(Decimal("50000"), Decimal("10"))
        assert result == Decimal("45000.00")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_calculator.py -v
```

预期：`ModuleNotFoundError`

- [ ] **Step 3: 实现 calculate_liquidation_price**

`app/calculator.py`:

```python
"""网格交易测算引擎 — 纯函数，零 Flask 依赖。"""
from decimal import Decimal, ROUND_HALF_UP


def _quantize(value: Decimal) -> Decimal:
    """将结果量化为 2 位小数。"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_liquidation_price(entry_price: Decimal, leverage: Decimal) -> Decimal:
    """计算做多爆仓价（全仓简化模型）。

    公式：爆仓价 = 入场价 × (1 - 1/杠杆)
    杠杆为 1 时返回 0（永不爆仓）。
    """
    if leverage <= Decimal("1"):
        return Decimal("0")
    price = entry_price * (Decimal("1") - Decimal("1") / leverage)
    return _quantize(price)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_calculator.py -v
```

预期：3 个 PASS

- [ ] **Step 5: 提交**

```bash
git add app/calculator.py tests/test_calculator.py
git commit -m "feat(calculator): add liquidation price calculation"
```

---

## Task 4: 测算引擎 — 安全性评估

**Files:**
- Modify: `app/calculator.py`
- Modify: `tests/test_calculator.py`

- [ ] **Step 1: 写失败测试（追加）**

```python
from app.calculator import assess_safety


class TestAssessSafety:
    def test_safe_params(self):
        result = assess_safety(Decimal("80"), Decimal("95"))
        assert result["level"] == "safe"
        assert result["buffer_pct"] > Decimal("10")

    def test_warning_params(self):
        result = assess_safety(Decimal("80"), Decimal("84"))
        assert result["level"] == "warning"

    def test_danger_params(self):
        result = assess_safety(Decimal("80"), Decimal("75"))
        assert result["level"] == "danger"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_calculator.py::TestAssessSafety -v
```

- [ ] **Step 3: 实现 assess_safety**

追加到 `app/calculator.py`:

```python
def assess_safety(liquidation_price: Decimal, lower_price: Decimal) -> dict:
    """评估参数安全性。返回 {level, buffer_pct}"""
    if liquidation_price <= Decimal("0"):
        return {"level": "safe", "buffer_pct": Decimal("0")}

    threshold = liquidation_price * Decimal("1.1")
    buffer_pct = ((lower_price - liquidation_price) / liquidation_price) * Decimal("100")
    buffer_pct = _quantize(buffer_pct)

    if lower_price <= liquidation_price:
        level = "danger"
    elif lower_price < threshold:
        level = "warning"
    else:
        level = "safe"

    return {"level": level, "buffer_pct": buffer_pct}
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_calculator.py::TestAssessSafety -v
```

- [ ] **Step 5: 提交**

```bash
git add app/calculator.py tests/test_calculator.py
git commit -m "feat(calculator): add safety assessment"
```

---

## Task 5: 测算引擎 — 网格分布 + 资金校验

**Files:**
- Modify: `app/calculator.py`
- Modify: `tests/test_calculator.py`

- [ ] **Step 1: 写失败测试**

```python
from app.calculator import calculate_grid_distribution


class TestCalculateGridDistribution:
    def test_simple_grid_5x(self):
        # 上限=110, 下限=90, 网格=2, 入场价=100, 杠杆=5, 单次买1币
        result = calculate_grid_distribution(
            upper=Decimal("110"), lower=Decimal("90"),
            grid_size=Decimal("2"), entry_price=Decimal("100"),
            leverage=Decimal("5"), quantity_per_grid=Decimal("1"),
        )
        assert result["grid_count"] == 10
        assert result["nominal_per_grid"] == Decimal("100.00")
        assert result["profit_per_grid"] == Decimal("2.00")  # 1×2
        assert result["total_capital_used"] == Decimal("200.00")  # 100×10/5

    def test_simple_grid_1x(self):
        # 现货1x, 占用 = 名义 × 格数
        result = calculate_grid_distribution(
            upper=Decimal("110"), lower=Decimal("90"),
            grid_size=Decimal("2"), entry_price=Decimal("100"),
            leverage=Decimal("1"), quantity_per_grid=Decimal("1"),
        )
        assert result["grid_count"] == 10
        assert result["profit_per_grid"] == Decimal("2.00")
        assert result["total_capital_used"] == Decimal("1000.00")  # 100×10/1

    def test_btc_grid(self):
        # BTC: 上限=71500, 下限=58500, 网格=500, 入场价=65000, 杠杆=1, 买0.01
        result = calculate_grid_distribution(
            upper=Decimal("71500"), lower=Decimal("58500"),
            grid_size=Decimal("500"), entry_price=Decimal("65000"),
            leverage=Decimal("1"), quantity_per_grid=Decimal("0.01"),
        )
        assert result["grid_count"] == 26
        assert result["nominal_per_grid"] == Decimal("650.00")
        assert result["profit_per_grid"] == Decimal("5.00")  # 0.01×500
        assert result["total_capital_used"] == Decimal("16900.00")  # 650×26/1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_calculator.py::TestCalculateGridDistribution -v
```

- [ ] **Step 3: 实现 calculate_grid_distribution**

追加到 `app/calculator.py`:

```python
import math


def calculate_grid_distribution(
    upper: Decimal, lower: Decimal, grid_size: Decimal,
    entry_price: Decimal, leverage: Decimal, quantity_per_grid: Decimal,
) -> dict:
    """计算网格分布。

    公式：
    - 网格数量 = ceil((上限 - 下限) / 网格大小)
    - 单次网格名义价值 = 单次购买数量 × 入场价
    - 单次网格利润 = 单次购买数量 × 网格大小（价差 × 数量）
    - 总占用资金 = 单次名义价值 × 网格数量 / 杠杆
    """
    grid_count = math.ceil((upper - lower) / grid_size)
    nominal_per_grid = _quantize(quantity_per_grid * entry_price)
    profit_per_grid = _quantize(quantity_per_grid * grid_size)
    total_capital_used = _quantize(nominal_per_grid * Decimal(str(grid_count)) / leverage)

    return {
        "grid_count": grid_count,
        "quantity_per_grid": quantity_per_grid,
        "nominal_per_grid": nominal_per_grid,
        "profit_per_grid": profit_per_grid,
        "total_capital_used": total_capital_used,
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_calculator.py::TestCalculateGridDistribution -v
```

- [ ] **Step 5: 提交**

```bash
git add app/calculator.py tests/test_calculator.py
git commit -m "feat(calculator): add grid distribution with quantity-based sizing"
```

---

## Task 6: 测算引擎 — 最大回撤 + 建议 + analyze

**Files:**
- Modify: `app/calculator.py`
- Modify: `tests/test_calculator.py`

- [ ] **Step 1: 写失败测试**

```python
from app.calculator import calculate_max_drawdown, generate_suggestions, analyze


class TestCalculateMaxDrawdown:
    def test_20_percent_drop_5x(self):
        result = calculate_max_drawdown(Decimal("100"), Decimal("80"), Decimal("5"))
        assert result == Decimal("100.00")

    def test_10_percent_drop_3x(self):
        result = calculate_max_drawdown(Decimal("100"), Decimal("90"), Decimal("3"))
        assert result == Decimal("30.00")


class TestGenerateSuggestions:
    def test_safe(self):
        result = generate_suggestions("safe", Decimal("3"), Decimal("95"), Decimal("80"))
        assert "安全" in result[0]

    def test_danger(self):
        result = generate_suggestions("danger", Decimal("10"), Decimal("75"), Decimal("80"))
        assert any("杠杆" in s for s in result) or any("下限" in s for s in result)

    def test_capital_shortfall_appended(self):
        suggestions = []
        generate_suggestions("safe", Decimal("1"), Decimal("50"), Decimal("0"))
        # capital check handled in analyze


class TestAnalyze:
    def test_analyze_returns_full_result(self):
        # BTC 3x, 0.01币, 26格 → 总占用 = 650×26/3 = 5633.33
        result = analyze(
            capital=Decimal("10000"), leverage=Decimal("3"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert "liquidation_price" in result
        assert "safety" in result
        assert "grid" in result
        assert "max_drawdown" in result
        assert "capital" in result
        assert "suggestions" in result
        assert result["capital"]["sufficient"] is True
        assert result["grid"]["total_capital_used"] == Decimal("5633.33")
        assert result["capital"]["remaining"] == Decimal("4366.67")

    def test_analyze_capital_shortfall(self):
        result = analyze(
            capital=Decimal("5000"), leverage=Decimal("3"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["capital"]["sufficient"] is False
        assert any("不足" in s for s in result["suggestions"])
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_calculator.py::TestAnalyze -v
```

- [ ] **Step 3: 实现 calculate_max_drawdown, generate_suggestions, analyze**

追加到 `app/calculator.py`:

```python
def calculate_max_drawdown(entry_price: Decimal, lower_price: Decimal, leverage: Decimal) -> Decimal:
    """估算从入场价跌到网格下限的最大回撤。"""
    drawdown = (entry_price - lower_price) / entry_price * leverage * Decimal("100")
    return _quantize(drawdown)


def generate_suggestions(level: str, leverage: Decimal, lower_price: Decimal, liquidation_price: Decimal) -> list:
    """根据安全等级生成参数调整建议。"""
    suggestions = []

    if level == "safe":
        suggestions.append("✅ 当前参数安全，可以执行。")
        return suggestions

    if level == "danger":
        suggestions.append("💥 危险：网格下限低于爆仓价，在设定区间内将爆仓！")
        safe_lower = _quantize(liquidation_price * Decimal("1.1"))
        suggestions.append(f"💡 建议：将网格下限提高至 {safe_lower} USDT 以上，或降低杠杆。")
        return suggestions

    suggestions.append("⚠️ 警告：安全边际不足 10%，存在爆仓风险。")
    safe_lower = _quantize(liquidation_price * Decimal("1.1"))
    suggestions.append(f"💡 建议：将网格下限提高至 {safe_lower} USDT 以上，或降低杠杆。")
    return suggestions


def analyze(
    capital: Decimal, leverage: Decimal, entry_price: Decimal,
    upper_price: Decimal, lower_price: Decimal, grid_size: Decimal,
    quantity_per_grid: Decimal,
) -> dict:
    """聚合所有测算，返回完整结果。"""
    liquidation_price = calculate_liquidation_price(entry_price, leverage)
    safety = assess_safety(liquidation_price, lower_price)
    grid = calculate_grid_distribution(upper_price, lower_price, grid_size, entry_price, leverage, quantity_per_grid)
    max_drawdown = calculate_max_drawdown(entry_price, lower_price, leverage)
    suggestions = generate_suggestions(safety["level"], leverage, lower_price, liquidation_price)

    # 初始资金校验：杠杆占用 = 名义 / 杠杆
    total_used = grid["total_capital_used"]
    capital_ok = capital >= total_used
    capital_remaining = _quantize(capital - total_used)

    if not capital_ok:
        shortfall = _quantize(total_used - capital)
        suggestions.insert(0, f"💰 资金不足：总占用 {total_used} USDT，超出初始资金 {shortfall} USDT！")

    return {
        "liquidation_price": liquidation_price,
        "safety": safety,
        "grid": grid,
        "max_drawdown": max_drawdown,
        "capital": {
            "initial": capital,
            "total_used": total_used,
            "remaining": capital_remaining,
            "sufficient": capital_ok,
        },
        "suggestions": suggestions,
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_calculator.py -v
```

- [ ] **Step 5: 提交**

```bash
git add app/calculator.py tests/test_calculator.py
git commit -m "feat(calculator): add drawdown, suggestions, capital check, analyze entry"
```

---

## Task 7: Flask 应用骨架

**Files:**
- Create: `app/__init__.py`（重写为工厂）
- Create: `app/routes.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: 重写 app/__init__.py**

```python
"""Flask 应用工厂。"""
import os
from flask import Flask


def create_app() -> Flask:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    return app
```

- [ ] **Step 2: 写失败测试**

`tests/test_routes.py`:

```python
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestIndexRoute:
    def test_get_index_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_get_index_prefills_defaults(self, client):
        """首屏应渲染首币种缺省值"""
        response = client.get("/")
        data = response.data.decode("utf-8")
        assert "65000" in data  # BTC default entry_price
        assert "0.01" in data   # BTC default quantity

    def test_get_with_querystring_restores_user_values(self, client):
        """从结果页返回应保留用户输入"""
        response = client.get("/?symbol=ETHUSDT&capital=5000&leverage=5&entry_price=9999&upper_price=11000&lower_price=9000&grid_size=50&quantity_per_grid=0.5")
        data = response.data.decode("utf-8")
        assert "9999" in data
        assert "0.5" in data

    def test_post_valid_params_returns_result(self, client):
        response = client.post("/", data={
            "symbol": "BTCUSDT", "capital": "20000", "leverage": "3",
            "entry_price": "65000", "upper_price": "71500",
            "lower_price": "58500", "grid_size": "500",
            "quantity_per_grid": "0.01",
        })
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        assert "安全" in data or "safe" in data

    def test_post_missing_field_returns_form_with_error(self, client):
        response = client.post("/", data={
            "symbol": "", "capital": "", "leverage": "5",
            "entry_price": "100", "upper_price": "110",
            "lower_price": "95", "grid_size": "2",
            "quantity_per_grid": "1",
        })
        assert response.status_code == 200

    def test_post_invalid_logic_returns_error(self, client):
        response = client.post("/", data={
            "symbol": "BTCUSDT", "capital": "1000", "leverage": "5",
            "entry_price": "100", "upper_price": "110",
            "lower_price": "105",  # 下限 > 入场价
            "grid_size": "2", "quantity_per_grid": "1",
        })
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        assert "下限" in data or "lower" in data
```

- [ ] **Step 3: 运行测试确认失败**

```bash
pytest tests/test_routes.py -v
```

- [ ] **Step 4: 实现 routes.py**

`app/routes.py`:

```python
"""Flask 路由：参数表单 + 测算结果。"""
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request

from app.calculator import analyze
from app.config_loader import get_symbols

main_bp = Blueprint("main", __name__)


def _parse_and_validate(form: dict):
    """解析并校验表单参数。返回 (params_dict, errors_list)。"""
    errors = []
    required_fields = [
        "symbol", "capital", "leverage", "entry_price",
        "upper_price", "lower_price", "grid_size", "quantity_per_grid",
    ]

    for field in required_fields:
        if not form.get(field, "").strip():
            errors.append(f"字段 {field} 为必填项")

    if errors:
        return {}, errors

    try:
        params = {
            "symbol": form["symbol"],
            "capital": Decimal(form["capital"]),
            "leverage": Decimal(form["leverage"]),
            "entry_price": Decimal(form["entry_price"]),
            "upper_price": Decimal(form["upper_price"]),
            "lower_price": Decimal(form["lower_price"]),
            "grid_size": Decimal(form["grid_size"]),
            "quantity_per_grid": Decimal(form["quantity_per_grid"]),
        }
    except (InvalidOperation, ValueError):
        return {}, ["请输入有效的数值"]

    if params["leverage"] < Decimal("1") or params["leverage"] > Decimal("125"):
        errors.append("杠杆必须在 1-125 之间")

    if params["upper_price"] <= params["entry_price"]:
        errors.append("网格上限必须大于入场价")

    if params["lower_price"] >= params["entry_price"]:
        errors.append("网格下限必须小于入场价")

    if params["grid_size"] <= Decimal("0"):
        errors.append("网格大小必须为正数")

    if params["quantity_per_grid"] <= Decimal("0"):
        errors.append("单次购买数量必须为正数")

    if params["capital"] <= Decimal("0"):
        errors.append("初始资金必须为正数")

    return params, errors


@main_bp.route("/", methods=["GET", "POST"])
def index():
    symbols = get_symbols()
    if request.method == "POST":
        params, errors = _parse_and_validate(request.form)
        if errors:
            return render_template("index.html", errors=errors, form=request.form, symbols=symbols)

        result = analyze(
            leverage=params["leverage"], entry_price=params["entry_price"],
            upper_price=params["upper_price"], lower_price=params["lower_price"],
            grid_size=params["grid_size"], quantity_per_grid=params["quantity_per_grid"],
            capital=params["capital"],
        )
        return render_template("result.html", result=result, params=params, symbols=symbols)

    # GET: querystring 恢复用户输入；否则首币种缺省
    form = None
    if request.args.get("symbol"):
        form = {
            "symbol": request.args.get("symbol", ""),
            "capital": request.args.get("capital", ""),
            "leverage": request.args.get("leverage", ""),
            "entry_price": request.args.get("entry_price", ""),
            "upper_price": request.args.get("upper_price", ""),
            "lower_price": request.args.get("lower_price", ""),
            "grid_size": request.args.get("grid_size", ""),
            "quantity_per_grid": request.args.get("quantity_per_grid", ""),
        }
    elif symbols:
        s = symbols[0]
        entry = float(s["entry_price"])
        upper_pct = float(s["upper_pct"])
        lower_pct = float(s["lower_pct"])
        form = {
            "symbol": s["symbol"], "capital": s["capital"], "leverage": "1",
            "entry_price": s["entry_price"],
            "upper_price": f"{entry * (1 + upper_pct / 100):.2f}",
            "lower_price": f"{entry * (1 - lower_pct / 100):.2f}",
            "grid_size": s["grid_size"],
            "quantity_per_grid": s["quantity_per_grid"],
        }

    return render_template("index.html", errors=None, form=form, symbols=symbols)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_routes.py -v
```

- [ ] **Step 6: 提交**

```bash
git add app/__init__.py app/routes.py tests/test_routes.py
git commit -m "feat(routes): add Flask routes with config-driven defaults and form preservation"
```

---

## Task 8: 前端模板与样式

**Files:**
- Create: `app/templates/base.html`
- Create: `app/templates/index.html`（含币种下拉 + JS 缺省填充）
- Create: `app/templates/result.html`（含资金占用展示）
- Create: `app/static/style.css`

- [ ] **Step 1: 创建 base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}网格交易测算工具{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <div class="container">
        <h1>🧮 网格交易测算工具</h1>
        {% block content %}{% endblock %}
        <footer>
            <p class="disclaimer">⚠️ 本工具使用全仓简化模型测算，未计入资金费率、手续费、维持保证金。结果仅供参考。</p>
        </footer>
    </div>
</body>
</html>
```

- [ ] **Step 2: 创建 index.html（含币种下拉 + JS 缺省填充）**

```html
{% extends "base.html" %}
{% block title %}参数输入 — 网格交易测算{% endblock %}
{% block content %}
<form method="POST" action="/" class="grid-form">
    {% if errors %}
    <div class="errors">
        <ul>{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul>
    </div>
    {% endif %}

    <div class="form-group">
        <label for="capital">初始资金 (USDT)</label>
        <input type="number" step="0.01" name="capital" id="capital" min="0" required
               value="{{ form.capital if form else '' }}">
    </div>

    <div class="form-group">
        <label for="symbol">币种</label>
        <select name="symbol" id="symbol" required>
            {% for s in symbols %}
            <option value="{{ s.symbol }}"
                {% if form and form.symbol == s.symbol %}selected{% endif %}
                {% if not form and loop.first %}selected{% endif %}
                data-entry="{{ s.entry_price }}"
                data-upper-pct="{{ s.upper_pct }}"
                data-lower-pct="{{ s.lower_pct }}"
                data-grid-size="{{ s.grid_size }}"
                data-quantity="{{ s.quantity_per_grid }}"
                data-capital="{{ s.capital }}">
                {{ s.symbol }} ({{ s.name }})
            </option>
            {% endfor %}
        </select>
    </div>

    <div class="form-group">
        <label for="leverage">杠杆 (1-125x)</label>
        <input type="number" step="1" name="leverage" id="leverage" min="1" max="125" required
               value="{{ form.leverage if form else '1' }}">
    </div>

    <div class="form-group">
        <label for="entry_price">入场价 (USDT)</label>
        <input type="number" step="0.01" name="entry_price" id="entry_price" required
               value="{{ form.entry_price if form else '' }}">
    </div>

    <div class="form-group">
        <label for="upper_price">网格上限 (USDT)</label>
        <input type="number" step="0.01" name="upper_price" id="upper_price" required
               value="{{ form.upper_price if form else '' }}">
    </div>

    <div class="form-group">
        <label for="lower_price">网格下限 (USDT)</label>
        <input type="number" step="0.01" name="lower_price" id="lower_price" required
               value="{{ form.lower_price if form else '' }}">
    </div>

    <div class="form-group">
        <label for="grid_size">网格大小 (USDT)</label>
        <input type="number" step="0.01" name="grid_size" id="grid_size" required
               value="{{ form.grid_size if form else '' }}">
    </div>

    <div class="form-group">
        <label for="quantity_per_grid">单次网格购买数量 (币)</label>
        <input type="number" step="any" name="quantity_per_grid" id="quantity_per_grid" min="0" required
               value="{{ form.quantity_per_grid if form else '' }}">
    </div>

    <button type="submit" class="btn-submit">开始测算</button>
</form>

<script>
function fillDefaults() {
    const opt = document.getElementById('symbol').options[document.getElementById('symbol').selectedIndex];
    const entry = parseFloat(opt.dataset.entry);
    const upperPct = parseFloat(opt.dataset.upperPct);
    const lowerPct = parseFloat(opt.dataset.lowerPct);
    if (!document.getElementById('entry_price').value) document.getElementById('entry_price').value = entry;
    if (!document.getElementById('upper_price').value) document.getElementById('upper_price').value = (entry * (1 + upperPct / 100)).toFixed(2);
    if (!document.getElementById('lower_price').value) document.getElementById('lower_price').value = (entry * (1 - lowerPct / 100)).toFixed(2);
    if (!document.getElementById('grid_size').value) document.getElementById('grid_size').value = opt.dataset.gridSize;
    if (!document.getElementById('quantity_per_grid').value) document.getElementById('quantity_per_grid').value = opt.dataset.quantity;
    if (!document.getElementById('capital').value) document.getElementById('capital').value = opt.dataset.capital;
}
document.getElementById('symbol').addEventListener('change', fillDefaults);
window.addEventListener('DOMContentLoaded', fillDefaults);
</script>
{% endblock %}
```

- [ ] **Step 3: 创建 result.html（含资金占用展示 + 带参返回链接）**

```html
{% extends "base.html" %}
{% block title %}测算结果 — 网格交易测算{% endblock %}
{% block content %}
<div class="result">
    <h2>测算结果 — {{ params.symbol }}</h2>

    <div class="safety-badge safety-{{ result.safety.level }}">
        {% if result.safety.level == "safe" %}✅ 安全
        {% elif result.safety.level == "warning" %}⚠️ 警告
        {% else %}💥 危险{% endif %}
    </div>

    <table class="result-table">
        <tr><td>初始资金</td><td><strong>{{ result.capital.initial }} USDT</strong></td></tr>
        <tr><td>爆仓价</td><td><strong>{{ result.liquidation_price }} USDT</strong></td></tr>
        <tr><td>安全边际</td><td>{{ result.safety.buffer_pct }}%</td></tr>
        <tr><td>单次网格购买</td><td>{{ result.grid.quantity_per_grid }} 币</td></tr>
        <tr><td>单次网格名义价值</td><td>{{ result.grid.nominal_per_grid }} USDT</td></tr>
        <tr><td>单次网格利润</td><td>{{ result.grid.profit_per_grid }} USDT</td></tr>
        <tr><td>网格数量</td><td>{{ result.grid.grid_count }} 格</td></tr>
        <tr><td>总占用资金</td><td>{{ result.grid.total_capital_used }} USDT</td></tr>
        <tr><td>剩余资金</td>
            <td class="{{ 'text-ok' if result.capital.sufficient else 'text-danger' }}">
                {{ result.capital.remaining }} USDT
                {% if not result.capital.sufficient %}（不足！）{% endif %}
            </td>
        </tr>
        <tr><td>最大回撤</td><td>{{ result.max_drawdown }}%</td></tr>
    </table>

    <div class="suggestions">
        <h3>建议</h3>
        <ul>{% for s in result.suggestions %}<li>{{ s }}</li>{% endfor %}</ul>
    </div>

    <a href="/?symbol={{ params.symbol }}&capital={{ params.capital }}&leverage={{ params.leverage }}&entry_price={{ params.entry_price }}&upper_price={{ params.upper_price }}&lower_price={{ params.lower_price }}&grid_size={{ params.grid_size }}&quantity_per_grid={{ params.quantity_per_grid }}" class="btn-back">← 重新测算</a>
</div>
{% endblock %}
```

- [ ] **Step 4: 创建 style.css**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #1a1a2e; color: #e0e0e0; }
.container { max-width: 600px; margin: 40px auto; padding: 20px; }
h1 { text-align: center; margin-bottom: 30px; color: #00d4ff; }
h2 { margin-bottom: 20px; }

.grid-form { background: #16213e; padding: 30px; border-radius: 12px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; color: #a0a0c0; }
.form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #2a2a4a; border-radius: 6px; background: #0f3460; color: #e0e0e0; font-size: 16px; }
.btn-submit { width: 100%; padding: 12px; background: #00d4ff; color: #1a1a2e; border: none; border-radius: 6px; font-size: 18px; font-weight: bold; cursor: pointer; margin-top: 10px; }
.btn-submit:hover { background: #00b8d4; }

.errors { background: #ff444433; border: 1px solid #ff4444; padding: 12px; border-radius: 6px; margin-bottom: 20px; }
.errors li { color: #ff6666; list-style: none; }

.result { background: #16213e; padding: 30px; border-radius: 12px; }
.safety-badge { text-align: center; padding: 16px; border-radius: 8px; font-size: 24px; font-weight: bold; margin-bottom: 20px; }
.safety-safe { background: #00c85333; color: #00c853; border: 1px solid #00c853; }
.safety-warning { background: #ffab0033; color: #ffab00; border: 1px solid #ffab00; }
.safety-danger { background: #ff174433; color: #ff1744; border: 1px solid #ff1744; }

.result-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
.result-table td { padding: 10px; border-bottom: 1px solid #2a2a4a; }
.result-table td:first-child { color: #a0a0c0; }

.text-ok { color: #00c853; }
.text-danger { color: #ff1744; font-weight: bold; }

.suggestions { background: #0f3460; padding: 16px; border-radius: 8px; margin-bottom: 20px; }
.suggestions li { list-style: none; padding: 4px 0; }

.btn-back { display: inline-block; color: #00d4ff; text-decoration: none; padding: 10px 0; }

.disclaimer { text-align: center; color: #666; font-size: 12px; margin-top: 30px; }
```

- [ ] **Step 5: 运行全部测试确认通过**

```bash
pytest tests/ -v
```

- [ ] **Step 6: 提交**

```bash
git add app/templates/ app/static/
git commit -m "feat(frontend): add symbol selector, quantity field, capital display"
```

---

## Task 9: 运行验证

- [ ] **Step 1: 启动 Flask 应用**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
python -m flask --app app run --debug
```

- [ ] **Step 2: 浏览器访问 http://127.0.0.1:5000，确认表单页首屏自动填充 BTC 缺省值**

- [ ] **Step 3: 填写安全+资金充足参数提交**

参数：symbol=BTCUSDT, capital=10000, leverage=3, entry_price=65000, upper=71500, lower=58500, grid_size=500, quantity=0.01

预期：✅安全，爆仓价=43333.33，总占用=5633.33（650×26/3），剩余=4366.67（绿色）

- [ ] **Step 4: 填写资金不足参数提交**

参数：symbol=ETHUSDT, capital=50, leverage=5, entry_price=3500, upper=3850, lower=3150, grid_size=30, quantity=1

预期：资金不足红色警告，建议列表顶部提示超出金额

- [ ] **Step 5: 验证表单数据保留**

完成测算后点"重新测算"，确认表单保留用户提交的参数而非重置为配置缺省值

- [ ] **Step 6: 验证切换币种填充缺省值**

手动清空入场价等字段，切到 ETHUSDT，确认自动填充 3500 / 3920 / 3080 / 30 / 0.1 / 1000

- [ ] **Step 7: 验证校验**

- 空字段：提示必填
- 下限 > 入场价：提示"网格下限必须小于入场价"
- 杠杆=0：提示"杠杆必须在 1-125 之间"
- 数量为 0：提示"单次购买数量必须为正数"

- [ ] **Step 8: 最终提交**

```bash
git add -A
git commit -m "feat: grid trading calculator complete - verified all scenarios"
```

---

## Spec Coverage

| Spec 需求 | 对应 Task |
|-----------|-----------|
| 币种配置（config.ini） | Task 1 + Task 2 |
| 参数输入表单（含 symbol / quantity / capital） | Task 7 + Task 8 |
| 首屏渲染缺省值 | Task 7 (routes GET) |
| 表单数据保留（querystring + form） | Task 7 + Task 8 |
| 爆仓价计算 | Task 3 |
| 安全性评估（三级） | Task 4 |
| 网格分布测算（quantity-based） | Task 5 |
| 初始资金校验 | Task 6 (analyze) |
| 最大回撤估算 | Task 6 |
| 结果展示与建议 | Task 8 (result.html) |
| 精度与单位（2 位小数、Decimal） | Task 3-6（全程 _quantize） |
