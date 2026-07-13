"""回测核心逻辑。"""
import time as _time_module
from decimal import Decimal

from app.calculator import _quantize  # 复用 calculator 的同款量化函数)


def backtest(klines: list[dict], capital: Decimal,
             upper_price: Decimal, lower_price: Decimal,
             grid_size: Decimal, quantity_per_grid: Decimal,
             progress_callback=None) -> dict:
    """执行网格策略回测。

    Args:
        klines: 按时间排序的K线列表
        capital: 初始资金
        upper_price: 网格上限
        lower_price: 网格下限
        grid_size: 网格间距
        quantity_per_grid: 单次购买数量
        progress_callback: 可选回调 (percent, kline_index, total_klines, elapsed_ms, trades_count)

    Returns:
        dict: {total_return_pct, max_drawdown_pct, win_rate_pct, total_trades,
               final_capital, trades, equity_curve, elapsed_ms}
    """
    if not klines:
        return {
            "total_return_pct": Decimal("0"),
            "max_drawdown_pct": Decimal("0"),
            "win_rate_pct": Decimal("0"),
            "total_trades": 0,
            "final_capital": capital,
            "trades": [],
            "equity_curve": [{"timestamp": 0, "capital": capital}],
            "elapsed_ms": 0,
        }

    # 初始化
    balance = capital
    holdings = Decimal("0")
    avg_cost = Decimal("0")  # 平均持仓成本（每币）
    trades = []
    equity_curve = [{"timestamp": klines[0]["timestamp"], "capital": capital}]

    # 计算网格价格列表
    grid_prices = []
    price = lower_price
    while price <= upper_price:
        grid_prices.append(_quantize(price))
        price += grid_size

    # 跟踪每个网格持仓状态
    grid_state = {p: {"has_position": False} for p in grid_prices}

    total_klines = len(klines)
    # 每 0.5% 进度回调一次（最少每 1 根），200 次/run 上限
    callback_every = max(1, total_klines // 200) if progress_callback else 0
    _t0 = _time_module.perf_counter()

    for i, kline in enumerate(klines):
        # 进度回调（节流，零开销 when None）
        if callback_every and i % callback_every == 0:
            elapsed_ms = int((_time_module.perf_counter() - _t0) * 1000)
            percent = int((i + 1) / max(total_klines, 1) * 100)
            progress_callback(percent, i + 1, total_klines, elapsed_ms, len(trades))

        low = Decimal(kline["low"])
        high = Decimal(kline["high"])

        for gp in grid_prices:
            # 检查价格是否触达此网格
            if low <= gp <= high:
                if not grid_state[gp]["has_position"]:
                    # 买入：先检查资金，确认可买入后再更新加权平均成本
                    cost = gp * quantity_per_grid
                    if balance >= cost:
                        avg_cost = (avg_cost * holdings + gp * quantity_per_grid) / (holdings + quantity_per_grid)
                        balance -= cost
                        holdings += quantity_per_grid
                        grid_state[gp]["has_position"] = True
                        trades.append({
                            "timestamp": kline["timestamp"],
                            "direction": "buy",
                            "price": gp,
                            "quantity": quantity_per_grid,
                            "profit": Decimal("0"),
                        })
                else:
                    # 卖出：利润 = (卖出价 - 平均成本) × 数量
                    revenue = gp * quantity_per_grid
                    balance += revenue
                    holdings -= quantity_per_grid
                    profit = _quantize((gp - avg_cost) * quantity_per_grid)
                    grid_state[gp]["has_position"] = False
                    trades.append({
                        "timestamp": kline["timestamp"],
                        "direction": "sell",
                        "price": gp,
                        "quantity": quantity_per_grid,
                        "profit": profit,
                    })
                    # 清仓后重置平均成本
                    if holdings == 0:
                        avg_cost = Decimal("0")

        # 记录资金曲线
        current_value = balance + holdings * Decimal(kline["close"])
        equity_curve.append({
            "timestamp": kline["timestamp"],
            "capital": _quantize(current_value),
        })

    # 最终 100% 回调
    if progress_callback and total_klines > 0:
        elapsed_ms = int((_time_module.perf_counter() - _t0) * 1000)
        progress_callback(100, total_klines, total_klines, elapsed_ms, len(trades))

    final_capital = balance + holdings * Decimal(klines[-1]["close"])
    final_capital = _quantize(final_capital)

    # 统计指标
    total_return_pct = _quantize((final_capital - capital) / capital * Decimal("100"))
    max_drawdown_pct = _calc_max_drawdown(equity_curve)
    win_rate_pct = _calc_win_rate(trades)
    buy_count = sum(1 for t in trades if t["direction"] == "buy")
    sell_count = sum(1 for t in trades if t["direction"] == "sell")
    pairs = min(buy_count, sell_count)
    final_holdings_qty = holdings
    final_avg_cost = avg_cost
    final_last_price = Decimal(klines[-1]["close"])
    # 持仓市值按现价计算（保证：持仓市值 + 剩余资金 = 总资产）
    final_holdings_value = _quantize(holdings * final_last_price)

    # SVG 收益曲线点集
    curve_points, start_y = _calc_svg_points(equity_curve)

    _elapsed_ms = int((_time_module.perf_counter() - _t0) * 1000)

    return {
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "total_trades": len(trades),
        "buy_count": buy_count,
        "sell_count": sell_count,
        "pairs": pairs,
        "final_holdings_qty": final_holdings_qty,
        "final_avg_cost": final_avg_cost,
        "final_last_price": final_last_price,
        "final_holdings_value": final_holdings_value,
        "final_balance": balance,
        "final_capital": final_capital,
        "trades": trades,
        "equity_curve": equity_curve,
        "curve_points": curve_points,
        "start_y": start_y,
        "elapsed_ms": _elapsed_ms,
    }


def _calc_max_drawdown(equity_curve: list[dict]) -> Decimal:
    """计算最大回撤。"""
    peak = Decimal("0")
    max_dd = Decimal("0")
    for point in equity_curve:
        value = point["capital"]
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak * Decimal("100")
            if dd > max_dd:
                max_dd = dd
    return _quantize(max_dd)


def _calc_win_rate(trades: list[dict]) -> Decimal:
    """计算胜率 = 盈利卖出 / 总卖出次数。"""
    sell_trades = [t for t in trades if t["direction"] == "sell"]
    if not sell_trades:
        return Decimal("0")
    wins = sum(1 for t in sell_trades if t["profit"] > 0)
    return _quantize(Decimal(wins) / Decimal(len(sell_trades)) * Decimal("100"))


def _calc_svg_points(equity_curve: list[dict]) -> tuple[str, float]:
    """计算 SVG polyline 点集。

    Returns:
        (points_str, start_y) — points_str 是 "x,y x,y ..." 格式, start_y 是起点 y 坐标
    """
    if not equity_curve:
        return "", 120.0

    values = [float(p["capital"]) for p in equity_curve]
    min_v = min(values)
    max_v = max(values)
    range_v = max_v - min_v if max_v != min_v else 1.0

    width = 800.0
    height = 240.0
    n = len(values)

    points = []
    for i, v in enumerate(values):
        x = (i / max(1, n - 1)) * width
        # y 反转（值越大越靠上），留 10px 边距
        y = height - ((v - min_v) / range_v) * (height - 20) - 10
        points.append(f"{x:.1f},{y:.1f}")

    start_y = height - ((values[0] - min_v) / range_v) * (height - 20) - 10
    return " ".join(points), start_y


def generate_equity_curve(klines: list[dict], capital: Decimal,
                          upper_price: Decimal, lower_price: Decimal,
                          grid_size: Decimal, quantity_per_grid: Decimal) -> list[dict]:
    """生成独立资金曲线（用于前端绘图）。"""
    result = backtest(klines, capital, upper_price, lower_price, grid_size, quantity_per_grid)
    return result["equity_curve"]
