"""网格交易测算引擎 — 纯函数，零外部依赖。"""
import math
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


def assess_safety(liquidation_price: Decimal, lower_price: Decimal) -> dict:
    """评估参数安全性。

    返回 dict: {level: "safe"|"warning"|"danger", buffer_pct: Decimal}
    """
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


def calculate_grid_distribution(
    upper: Decimal,
    lower: Decimal,
    grid_size: Decimal,
    entry_price: Decimal,
    leverage: Decimal,
    quantity_per_grid: Decimal,
) -> dict:
    """计算网格分布。

    - 网格数量 = ceil((上限 - 下限) / 网格大小)
    - 单次网格名义价值 = 单次购买数量 × 入场价
    - 单次网格利润 = 单次购买数量 × 网格大小（价差 × 数量）
    - 总占用资金 = 单次网格名义价值 × 网格数量 / 杠杆
      （杠杆越高，实际占用保证金越少）
    """
    grid_count = math.ceil((upper - lower) / grid_size)

    nominal_per_grid = quantity_per_grid * entry_price  # 单次网格名义价值
    profit_per_grid = _quantize(quantity_per_grid * grid_size)  # 价差 × 数量

    total_capital_used = _quantize(nominal_per_grid * Decimal(str(grid_count)) / leverage)

    return {
        "grid_count": grid_count,
        "quantity_per_grid": quantity_per_grid,
        "nominal_per_grid": _quantize(nominal_per_grid),
        "profit_per_grid": profit_per_grid,
        "total_capital_used": total_capital_used,
    }


def calculate_max_drawdown(
    entry_price: Decimal,
    lower_price: Decimal,
    leverage: Decimal,
) -> Decimal:
    """估算从入场价跌到网格下限的最大回撤。

    公式：(入场价 - 下限) / 入场价 × 杠杆 × 100%
    """
    drawdown = (entry_price - lower_price) / entry_price * leverage * Decimal("100")
    return _quantize(drawdown)


def generate_suggestions(
    level: str,
    leverage: Decimal,
    lower_price: Decimal,
    liquidation_price: Decimal,
) -> list:
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

    # warning
    suggestions.append("⚠️ 警告：安全边际不足 10%，存在爆仓风险。")
    safe_lower = _quantize(liquidation_price * Decimal("1.1"))
    suggestions.append(f"💡 建议：将网格下限提高至 {safe_lower} USDT 以上，或降低杠杆。")
    return suggestions


def analyze(
    leverage: Decimal,
    entry_price: Decimal,
    upper_price: Decimal,
    lower_price: Decimal,
    grid_size: Decimal,
    quantity_per_grid: Decimal,
    capital: Decimal,
) -> dict:
    """聚合所有测算，返回完整结果。"""
    liquidation_price = calculate_liquidation_price(entry_price, leverage)
    safety = assess_safety(liquidation_price, lower_price)
    grid = calculate_grid_distribution(
        upper_price, lower_price, grid_size, entry_price, leverage, quantity_per_grid
    )
    max_drawdown = calculate_max_drawdown(entry_price, lower_price, leverage)
    suggestions = generate_suggestions(safety["level"], leverage, lower_price, liquidation_price)

    # 初始资金校验
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
