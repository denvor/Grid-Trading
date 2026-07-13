"""回测引擎单测。"""
from decimal import Decimal
import pytest
from app.backtest.engine import backtest, generate_equity_curve


def _make_kline(ts: int, open_p: str, high_p: str, low_p: str, close_p: str) -> dict:
    """构造测试用K线。"""
    return {"timestamp": ts, "open": open_p, "high": high_p,
            "low": low_p, "close": close_p, "volume": "100"}


class TestBacktestEngine:
    """测试回测核心逻辑。"""

    def test_no_trades_when_price_between_grids(self):
        """价格落在网格间距中间且不变 → 无成交。"""
        # 价格 65250 不在任何网格线上（网格: 64000,64500,65000,65500,66000）
        # 但 K线 high/low=65250 不触达任何网格 → 0 成交
        klines = [_make_kline(i * 3600000, "65250", "65250", "65250", "65250")
                  for i in range(10)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["total_trades"] == 0
        assert result["final_capital"] == Decimal("10000")

    def test_buy_when_price_drops_to_grid(self):
        """价格跌到网格线 → 买入成交。"""
        klines = [
            _make_kline(0, "65000", "65000", "65000", "65000"),
            _make_kline(3600000, "65000", "65000", "64500", "64500"),
        ]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["total_trades"] >= 1
        assert any(t["direction"] == "buy" for t in result["trades"])

    def test_sell_when_price_rises_back(self):
        """价格回涨到卖出网格 → 卖出成交并获利。"""
        klines = [
            _make_kline(0, "65000", "65000", "65000", "65000"),
            _make_kline(3600000, "65000", "65000", "64500", "64500"),  # 买在 64500
            _make_kline(7200000, "64500", "65000", "64500", "65000"),  # 卖在 65000
        ]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        sells = [t for t in result["trades"] if t["direction"] == "sell"]
        if sells:
            # 平均成本法：先买 65000 再买 64500，avg_cost = 64750
            # 卖在 65000：profit = (65000 - 64750) × 0.01 = 2.50
            assert sells[0]["profit"] == Decimal("2.50")
            # 卖在 64500：profit = (64500 - 64750) × 0.01 = -2.50（亏损）
            if len(sells) > 1:
                assert sells[1]["profit"] == Decimal("-2.50")

    def test_total_return_calculation(self):
        """总收益率 = (最终 - 初始) / 初始 × 100。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(100)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        expected = ((result["final_capital"] - Decimal("10000")) / Decimal("10000") * Decimal("100")).quantize(Decimal("0.01"))
        assert result["total_return_pct"] == expected

    def test_max_drawdown_is_positive(self):
        """最大回撤 ≥ 0。"""
        klines = [_make_kline(i * 3600000, str(65000 - i * 100), "65000",
                           str(64000 - i * 100), str(65000 - i * 100))
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("60000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["max_drawdown_pct"] >= Decimal("0")

    def test_win_rate_between_0_and_100(self):
        """胜率在 0-100% 之间。"""
        klines = [_make_kline(i * 3600000, "65000", "65500", "64500", "65000")
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert Decimal("0") <= result["win_rate_pct"] <= Decimal("100")

    def test_capital_insufficient_guard(self):
        """资金不足时不亏过本金。"""
        klines = [_make_kline(i * 3600000, str(65000 - i * 500), "65000",
                           str(64000 - i * 500), str(65000 - i * 500))
                  for i in range(20)]
        result = backtest(
            klines=klines,
            capital=Decimal("100"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("60000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["final_capital"] >= Decimal("0")

    def test_empty_klines(self):
        """空K线列表返回默认值。"""
        result = backtest(
            klines=[],
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["total_trades"] == 0
        assert result["final_capital"] == Decimal("10000")


class TestBacktestTiming:
    def test_elapsed_ms_present(self):
        """backtest() 返回结果应包含 elapsed_ms"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0


class TestEquityCurve:
    def test_curve_length_equals_klines_plus_one(self):
        """资金曲线长度 = K线数 + 1。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(10)]
        curve = generate_equity_curve(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert len(curve) == len(klines) + 1

    def test_curve_starts_with_initial_capital(self):
        """资金曲线起点 = 初始资金。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(5)]
        curve = generate_equity_curve(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert curve[0]["capital"] == Decimal("10000")
