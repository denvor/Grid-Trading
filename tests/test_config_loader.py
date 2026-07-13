"""配置加载模块单测。"""
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
        for key in ["entry_price", "upper_pct", "lower_pct", "grid_size", "quantity_per_grid", "capital"]:
            assert key in btc

    def test_get_symbol_case_insensitive(self):
        assert get_symbol("btcusdt") is not None
        assert get_symbol("BTCUSDT") is not None

    def test_get_symbol_nonexistent_returns_none(self):
        assert get_symbol("FOOBAR") is None
