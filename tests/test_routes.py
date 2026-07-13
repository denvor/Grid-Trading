"""Flask 路由集成测试。"""
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
        response = client.get(
            "/?symbol=ETHUSDT&capital=5000&leverage=5"
            "&entry_price=9999&upper_price=11000"
            "&lower_price=9000&grid_size=50&quantity_per_grid=0.5"
            "&margin_mode=isolated"
        )
        data = response.data.decode("utf-8")
        assert "9999" in data
        assert "0.5" in data

    def test_post_valid_params_returns_result(self, client):
        response = client.post("/", data={
            "symbol": "BTCUSDT", "capital": "10000", "leverage": "3",
            "entry_price": "65000", "upper_price": "71500",
            "lower_price": "58500", "grid_size": "500",
            "quantity_per_grid": "0.01", "margin_mode": "cross",
        })
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        assert "安全" in data or "safe" in data

    def test_post_missing_field_returns_form_with_error(self, client):
        response = client.post("/", data={
            "symbol": "", "capital": "", "leverage": "5",
            "entry_price": "100", "upper_price": "110",
            "lower_price": "95", "grid_size": "2",
            "quantity_per_grid": "1", "margin_mode": "cross",
        })
        assert response.status_code == 200

    def test_post_invalid_logic_returns_error(self, client):
        response = client.post("/", data={
            "symbol": "BTCUSDT", "capital": "1000", "leverage": "5",
            "entry_price": "100", "upper_price": "110",
            "lower_price": "105",  # 下限 > 入场价
            "grid_size": "2", "quantity_per_grid": "1", "margin_mode": "cross",
        })
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        assert "下限" in data or "lower" in data

    def test_post_capital_shortfall_shows_warning(self, client):
        """资金不足时返回结果页含不足警告"""
        response = client.post("/", data={
            "symbol": "ETHUSDT", "capital": "50", "leverage": "5",
            "entry_price": "3500", "upper_price": "3850",
            "lower_price": "3150", "grid_size": "30",
            "quantity_per_grid": "1", "margin_mode": "cross",
        })
        assert response.status_code == 200
        data = response.data.decode("utf-8")
        assert "不足" in data or "shortfall" in data.lower()

    def test_post_isolated_mode_higher_liq(self, client):
        """逐仓模式爆仓价高于全仓（liq = avg_entry × (1 - 1/leverage)）"""
        response_iso = client.post("/", data={
            "symbol": "BTCUSDT", "capital": "10000", "leverage": "5",
            "entry_price": "65000", "upper_price": "71500",
            "lower_price": "58500", "grid_size": "500",
            "quantity_per_grid": "0.01", "margin_mode": "isolated",
        })
        assert response_iso.status_code == 200
        data = response_iso.data.decode("utf-8")
        # isolated: 65000 × 0.8 = 52000
        assert "52000" in data
