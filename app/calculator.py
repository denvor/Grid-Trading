"""网格交易测算引擎 — 纯函数，零 Flask 依赖。"""
import math
from decimal import Decimal, ROUND_HALF_UP


def _quantize(value: Decimal) -> Decimal:
    """将结果量化为 2 位小数。"""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_grid_avg_entry(upper_price: Decimal, lower_price: Decimal) -> Decimal:
    """计算网格平均开仓价（网格从下限到上限等间距挂单，均值≈上下限中点）。"""
    return _quantize((upper_price + lower_price) / Decimal("2"))


def calculate_liquidation_price_cross(
    avg_entry: Decimal,
    leverage: Decimal,
    capital: Decimal,
    quantity_per_grid: Decimal,
    grid_count: int,
) -> Decimal:
    """全仓网格爆仓价（简化模型）。

    逻辑：全部资金作为整个网格的担保，爆仓条件是累计浮亏 = 全部资金。
    简化公式：liq = avg_entry − capital / 总币量
      - 总币量 = quantity_per_grid × grid_count
      - 若 liq < 0，返回 0（永不爆仓）

    注意：此简化模型下，爆仓价不直接取决于杠杆倍数（杠杆仅决定保证金效率），
    而是取决于总资金与总仓位的比值。leverage 参数仅用于 guard（≤1 时无杠杆永不爆）。
    """
    total_qty = quantity_per_grid * Decimal(str(grid_count))
    if total_qty <= Decimal("0") or leverage <= Decimal("1"):
        return Decimal("0")
    margin_per_coin = capital / total_qty
    liq = avg_entry - margin_per_coin
    if liq <= Decimal("0"):
        return Decimal("0")
    return _quantize(liq)


def calculate_liquidation_price_isolated(
    avg_entry: Decimal,
    leverage: Decimal,
) -> Decimal:
    """逐仓网格爆仓价（每格独立保证金，最坏情况 = 最高位那格先爆）。"""
    if leverage <= Decimal("1"):
        return Decimal("0")
    return _quantize(avg_entry * (Decimal("1") - Decimal("1") / leverage))


def calculate_liquidation_price(
    avg_entry: Decimal,
    leverage: Decimal,
    margin_mode: str,
    capital: Decimal,
    quantity_per_grid: Decimal,
    grid_count: int,
) -> Decimal:
    """根据保证金模式选择爆仓价。"""
    if margin_mode == "isolated":
        return calculate_liquidation_price_isolated(avg_entry, leverage)
    return calculate_liquidation_price_cross(avg_entry, leverage, capital, quantity_per_grid, grid_count)


def assess_safety(liquidation_price: Decimal, lower_price: Decimal) -> dict:
    """评估参数安全性。

    注意：爆仓价 <= 0 意味着仓位极小或资金极充足，不会爆仓；
    但这并不代表"绝对安全"——外层还应检查 capital 是否足以覆盖总占用。
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

    公式：
    - 网格数量 = ceil((上限 - 下限) / 网格大小)
    - 单次网格名义价值 = 单次购买数量 × 入场价
    - 单次网格利润 = 单次购买数量 × 网格大小（价差 × 数量）
    - 总占用资金 = 单次名义价值 × 网格数量 / 杠杆
    """
    grid_count = math.ceil((upper - lower) / grid_size)
    profit_per_grid = _quantize(quantity_per_grid * grid_size)
    # 只在最后一步量化，避免中间四舍五入累积误差
    total_capital_used = _quantize(quantity_per_grid * entry_price * Decimal(str(grid_count)) / leverage)

    return {
        "grid_count": grid_count,
        "quantity_per_grid": quantity_per_grid,
        "nominal_per_grid": _quantize(quantity_per_grid * entry_price),
        "profit_per_grid": profit_per_grid,
        "total_capital_used": total_capital_used,
    }


def calculate_max_drawdown(
    entry_price: Decimal,
    lower_price: Decimal,
    leverage: Decimal,
) -> Decimal:
    """估算网格从入场价跌到下限的最大回撤。

    网格逐步建仓，平均持仓成本在中点附近，真实回撤约为单笔满仓的一半。
    公式：(入场价 - 下限) / 入场价 × 杠杆 × 100% / 2
    """
    drawdown = (entry_price - lower_price) / entry_price * leverage * Decimal("100") / Decimal("2")
    return _quantize(drawdown)


def generate_suggestions(
    level: str,
    leverage: Decimal,
    lower_price: Decimal,
    liquidation_price: Decimal,
) -> list:
    """根据安全等级生成参数调整建议。"""
    if level == "safe":
        return ["✅ 当前参数安全，可以执行。"]

    safe_lower = _quantize(liquidation_price * Decimal("1.1"))
    suggestion = f"💡 建议：将网格下限提高至 {safe_lower} USDT 以上，或降低杠杆。"

    if level == "danger":
        return [
            "💥 危险：网格下限低于爆仓价，在设定区间内将爆仓！",
            suggestion,
        ]
    # warning
    return [
        "⚠️ 警告：安全边际不足 10%，存在爆仓风险。",
        suggestion,
    ]


def _apply_safety_escalation(safety: dict, capital_ok: bool) -> dict:
    """资金不足时安全等级强制提升为 warning（即使 liq=0）。"""
    if not capital_ok and safety["level"] == "safe":
        return {"level": "warning", "buffer_pct": Decimal("0")}
    return safety


def analyze(
    capital: Decimal,
    leverage: Decimal,
    entry_price: Decimal,
    upper_price: Decimal,
    lower_price: Decimal,
    grid_size: Decimal,
    quantity_per_grid: Decimal,
    margin_mode: str = "cross",
) -> dict:
    """聚合所有测算，返回完整结果。

    Args:
        margin_mode: "cross"（全仓）或 "isolated"（逐仓）
    """
    grid = calculate_grid_distribution(upper_price, lower_price, grid_size, entry_price, leverage, quantity_per_grid)
    avg_entry = calculate_grid_avg_entry(upper_price, lower_price)
    liquidation_price = calculate_liquidation_price(
        avg_entry, leverage, margin_mode, capital,
        quantity_per_grid, grid["grid_count"],
    )
    safety = assess_safety(liquidation_price, lower_price)
    max_drawdown = calculate_max_drawdown(entry_price, lower_price, leverage)

    # 初始资金校验
    total_used = grid["total_capital_used"]
    capital_ok = capital >= total_used
    capital_remaining = _quantize(capital - total_used)
    safety = _apply_safety_escalation(safety, capital_ok)

    # 在 safety 确定后再生成建议，确保建议文字与 badge 一致
    suggestions = generate_suggestions(safety["level"], leverage, lower_price, liquidation_price)

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
