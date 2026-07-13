"""配置加载模块单测。"""
import pytest
from app.config_loader import get_symbols, get_symbol, save_symbol, CONFIG_PATH


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
        for key in ["entry_price", "upper_price", "lower_price", "grid_size",
                    "quantity_per_grid", "capital", "leverage", "margin_mode"]:
            assert key in btc, f"缺少字段 {key}"
        # 上下限应为具体价格（而非百分比）
        assert float(btc["upper_price"]) > float(btc["entry_price"])
        assert float(btc["lower_price"]) < float(btc["entry_price"])

    def test_get_symbol_case_insensitive(self):
        assert get_symbol("btcusdt") is not None
        assert get_symbol("BTCUSDT") is not None

    def test_get_symbol_nonexistent_returns_none(self):
        assert get_symbol("FOOBAR") is None

    def test_save_symbol_roundtrip(self, tmp_path, monkeypatch):
        """save_symbol 后应能立即读回更新值。"""
        import configparser
        # 用临时 config 文件
        tmp_cfg = tmp_path / "test_config.ini"
        tmp_cfg.write_text("""[BTCUSDT]
name = Bitcoin
entry_price = 65000
upper_price = 71500
lower_price = 58500
grid_size = 500
quantity_per_grid = 0.01
capital = 1000
leverage = 1
margin_mode = cross
""")
        monkeypatch.setattr("app.config_loader.CONFIG_PATH", str(tmp_cfg))
        # 强制重新加载
        from app.config_loader import _config
        _config.read(str(tmp_cfg), encoding="utf-8")

        save_symbol(
            symbol="BTCUSDT", capital="2000", leverage="5",
            upper_price="70000", lower_price="60000", grid_size="250",
            quantity_per_grid="0.02", margin_mode="isolated",
        )
        # 重新读取验证
        _config.read(str(tmp_cfg), encoding="utf-8")
        assert _config.get("BTCUSDT", "capital") == "2000"
        assert _config.get("BTCUSDT", "upper_price") == "70000"
        assert _config.get("BTCUSDT", "lower_price") == "60000"
        assert _config.get("BTCUSDT", "grid_size") == "250"
        assert _config.get("BTCUSDT", "quantity_per_grid") == "0.02"
        assert _config.get("BTCUSDT", "leverage") == "5"
        assert _config.get("BTCUSDT", "margin_mode") == "isolated"
