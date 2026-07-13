"""测算引擎单测。"""
from decimal import Decimal
from app.calculator import (
    calculate_liquidation_price,
    assess_safety,
    calculate_grid_distribution,
    calculate_max_drawdown,
    generate_suggestions,
    analyze,
)


class TestCalculateLiquidationPrice:
    """测试全仓爆仓价：liq = avg_entry − capital / 总币量"""

    def test_cross_basic(self):
        # avg_entry=100, capital=1000, qty=1, 10格 → 总币量=10
        # liq = 100 − 1000/10 = 0 → 永不爆仓（资金 10 倍于仓位）
        result = calculate_liquidation_price(Decimal("100"), Decimal("5"), "cross", Decimal("1000"), Decimal("1"), 10)
        assert result == Decimal("0")

    def test_cross_liq(self):
        # avg_entry=100, capital=50, qty=1, 10格 → 总币量=10
        # liq = 100 − 50/10 = 95.00
        result = calculate_liquidation_price(Decimal("100"), Decimal("5"), "cross", Decimal("50"), Decimal("1"), 10)
        assert result == Decimal("95.00")

    def test_isolated_basic(self):
        # isolated: liq = avg_entry × (1 − 1/leverage)
        result = calculate_liquidation_price(Decimal("100"), Decimal("5"), "isolated", Decimal("1000"), Decimal("1"), 10)
        assert result == Decimal("80.00")

    def test_isolated_1x(self):
        result = calculate_liquidation_price(Decimal("100"), Decimal("1"), "isolated", Decimal("1000"), Decimal("1"), 10)
        assert result == Decimal("0")


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


class TestCalculateGridDistribution:
    def test_simple_grid_5x(self):
        result = calculate_grid_distribution(
            upper=Decimal("110"), lower=Decimal("90"),
            grid_size=Decimal("2"), entry_price=Decimal("100"),
            leverage=Decimal("5"), quantity_per_grid=Decimal("1"),
        )
        assert result["grid_count"] == 10
        assert result["nominal_per_grid"] == Decimal("100.00")
        assert result["profit_per_grid"] == Decimal("2.00")
        assert result["total_capital_used"] == Decimal("200.00")

    def test_simple_grid_1x(self):
        result = calculate_grid_distribution(
            upper=Decimal("110"), lower=Decimal("90"),
            grid_size=Decimal("2"), entry_price=Decimal("100"),
            leverage=Decimal("1"), quantity_per_grid=Decimal("1"),
        )
        assert result["grid_count"] == 10
        assert result["profit_per_grid"] == Decimal("2.00")
        assert result["total_capital_used"] == Decimal("1000.00")

    def test_btc_grid(self):
        result = calculate_grid_distribution(
            upper=Decimal("71500"), lower=Decimal("58500"),
            grid_size=Decimal("500"), entry_price=Decimal("65000"),
            leverage=Decimal("1"), quantity_per_grid=Decimal("0.01"),
        )
        assert result["grid_count"] == 26
        assert result["nominal_per_grid"] == Decimal("650.00")
        assert result["profit_per_grid"] == Decimal("5.00")
        assert result["total_capital_used"] == Decimal("16900.00")


class TestCalculateMaxDrawdown:
    """网格逐步建仓，真实回撤约为单笔满仓的一半。"""

    def test_20_percent_drop_5x(self):
        # (100-80)/100 * 5 * 100 / 2 = 50.00
        result = calculate_max_drawdown(Decimal("100"), Decimal("80"), Decimal("5"))
        assert result == Decimal("50.00")

    def test_10_percent_drop_3x(self):
        # (100-90)/100 * 3 * 100 / 2 = 15.00
        result = calculate_max_drawdown(Decimal("100"), Decimal("90"), Decimal("3"))
        assert result == Decimal("15.00")


class TestGenerateSuggestions:
    def test_safe(self):
        result = generate_suggestions("safe", Decimal("3"), Decimal("95"), Decimal("80"))
        assert "安全" in result[0]

    def test_danger(self):
        result = generate_suggestions("danger", Decimal("10"), Decimal("75"), Decimal("80"))
        assert any("杠杆" in s for s in result) or any("下限" in s for s in result)


class TestAnalyze:
    def test_analyze_returns_full_result(self):
        # BTC 3x, cross: avg_entry=65000, 总币量=0.01×26=0.26
        # liq = 65000 - 10000/0.26 = 65000 - 38461.54 = 26538.46
        # 安全: 58500 > 26538.46 × 1.1 = 29192.31 → safe
        result = analyze(
            capital=Decimal("10000"), leverage=Decimal("3"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        assert "liquidation_price" in result
        assert "safety" in result
        assert "grid" in result
        assert "max_drawdown" in result
        assert "capital" in result
        assert "suggestions" in result
        assert result["liquidation_price"] == Decimal("26538.46")
        assert result["safety"]["level"] == "safe"
        assert result["capital"]["sufficient"] is True
        assert result["grid"]["total_capital_used"] == Decimal("5633.33")
        assert result["capital"]["remaining"] == Decimal("4366.67")

    def test_analyze_capital_shortfall(self):
        result = analyze(
            capital=Decimal("5000"), leverage=Decimal("3"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        assert result["capital"]["sufficient"] is False
        assert any("不足" in s for s in result["suggestions"])

    def test_analyze_capital_shortfall_escalates_to_warning(self):
        """capital 不足时若 liq=0 被判 safe, 应强制升级为 warning"""
        # capital=100, 5x, 0.01×26格: total_qty=0.26, margin_per_coin=384.6 < avg_entry 65000
        # liq = 65000 - 384.6 > 0 所以本来就不是 safe。换更大的 qty 让 capital 小到大 liq<0
        # capital=100, qty=0.5, 26格: total_qty=13, margin_per_coin=7.69, liq≈64992 → lower=58500 < 64992 → danger
        # 找个 capital ≈ margin 的边界: capital=3380=margin → liq=65000-3380/0.26=52000
        # 这种情况下不该测试。此 test 验证: 如果 safe + capital不足 → 升级
        result = analyze(
            capital=Decimal("3380"), leverage=Decimal("5"),  # total_used=3380, capital_ok=True(边界)
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        # capital=3380 == margin=3380, capital_ok=True, 不触发升级
        assert result["capital"]["sufficient"] is True
        assert result["safety"]["level"] == "safe"  # 没有误升级

        # 真正的 capital 不足场景, 且 liq 被 clamp 到 0
        # capital=500, leverage=1(spot), qty=0.01, 26格: margin=0.01×65000×26/1=16900 > 500
        result2 = analyze(
            capital=Decimal("500"), leverage=Decimal("1"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        assert result2["capital"]["sufficient"] is False
        # leverage=1 → liq=0 → 原本 safe; 因 capital 不足升级 warning
        assert result2["safety"]["level"] == "warning"

    def test_analyze_capital_shortfall_suggestions_match_badge(self):
        """capital 不足升级后 suggestions 文字应与 warning badge 一致(不能出现 ✅ 安全)"""
        result = analyze(
            capital=Decimal("500"), leverage=Decimal("1"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        # safety 是 warning → suggestions 不应包含 "✅ 当前参数安全"
        has_safe_msg = any("安全" in s and "不足" not in s for s in result["suggestions"])
        assert not has_safe_msg, f"warning 等级不应出现 '安全' 文字: {result['suggestions']}"
        # 应有 ⚠ 警告
        assert any("⚠" in s for s in result["suggestions"])

    def test_analyze_cross_safe_no_liq(self):
        """全仓：资金远大于仓位时爆仓价应为 0（永不爆仓）"""
        # capital=100000, qty=0.01, 26格, 总币量=0.26
        # liq = 65000 - 100000/0.26 = 负数 → 0
        result = analyze(
            capital=Decimal("100000"), leverage=Decimal("5"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="cross",
        )
        assert result["liquidation_price"] == Decimal("0")
        assert result["safety"]["level"] == "safe"

    def test_analyze_isolated_liq(self):
        """逐仓：用 avg_entry × (1 - 1/leverage)"""
        # avg_entry = 65000, liq = 65000 × 0.8 = 52000
        result = analyze(
            capital=Decimal("100000"), leverage=Decimal("5"),
            entry_price=Decimal("65000"), upper_price=Decimal("71500"),
            lower_price=Decimal("58500"), grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"), margin_mode="isolated",
        )
        assert result["liquidation_price"] == Decimal("52000.00")
