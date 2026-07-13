"""回测路由单测。"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    # 使用 test_request_context 以避免 datastore 需要真实数据库
    with app.test_client() as client:
        yield client


class TestBacktestRoutes:
    def test_get_backtest_page(self, client):
        response = client.get("/backtest")
        assert response.status_code == 200

    def test_post_valid_params_with_data(self, client):
        """有数据时执行回测"""
        mock_klines = MagicMock(return_value=[
            {"timestamp": i * 3600000, "open": "65000", "high": "65500",
             "low": "64500", "close": "65200", "volume": "100"}
            for i in range(24)
        ])
        with patch("app.backtest.data_fetcher.get_stored_klines", mock_klines):
            response = client.post("/backtest", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "capital": "10000", "upper_price": "66000",
                "lower_price": "64000", "grid_size": "500",
                "quantity_per_grid": "0.01",
                "start_time": "2024-01-01", "end_time": "2024-01-02",
            })
            assert response.status_code == 200

    def test_post_missing_field(self, client):
        response = client.post("/backtest", data={
            "symbol": "", "interval": "1h",
            "capital": "10000", "upper_price": "66000",
            "lower_price": "64000", "grid_size": "500",
            "quantity_per_grid": "0.01",
            "start_time": "2024-01-01", "end_time": "2024-01-02",
        })
        assert response.status_code == 200

    def test_post_invalid_time_range(self, client):
        response = client.post("/backtest", data={
            "symbol": "BTCUSDT", "interval": "1h",
            "capital": "10000", "upper_price": "66000",
            "lower_price": "64000", "grid_size": "500",
            "quantity_per_grid": "0.01",
            "start_time": "2024-03-01", "end_time": "2024-01-01",
        })
        assert response.status_code == 200

    def test_post_time_span_too_large(self, client):
        """时间跨度 >2 年不阻塞，只显示警告"""
        with patch("app.backtest.data_fetcher.get_stored_klines") as mock_get:
            mock_get.return_value = [
                {"timestamp": i, "open": "65000", "high": "65500",
                 "low": "64800", "close": "65200", "volume": "100"}
                for i in range(10)
            ]
            response = client.post("/backtest", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "capital": "10000", "upper_price": "66000",
                "lower_price": "64000", "grid_size": "500",
                "quantity_per_grid": "0.01",
                "start_time": "2020-01-01", "end_time": "2026-01-01",
            })
            assert response.status_code == 200
            body = response.data.decode("utf-8")
            # 显示软警告而非拒绝
            assert "耐心等待" in body or "时间跨度较大" in body

    def test_post_no_data_in_db(self, client):
        """数据库无数据 → 提示用户先拉取"""
        mock_klines = MagicMock(return_value=[])
        with patch("app.backtest.data_fetcher.get_stored_klines", mock_klines):
            response = client.post("/backtest", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "capital": "10000", "upper_price": "66000",
                "lower_price": "64000", "grid_size": "500",
                "quantity_per_grid": "0.01",
                "start_time": "2024-01-01", "end_time": "2024-01-02",
            })
            assert response.status_code == 200
            response_data = response.data.decode("utf-8")
            assert "CLI" in response_data or "fetch_data" in response_data or "拉取" in response_data

    def test_available_data_endpoint(self, client):
        """GET /backtest/available_data?symbol=BTCUSDT 返回可用 interval 和时间范围"""
        with patch("app.backtest.routes.list_symbol_intervals") as mock:
            mock.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 1704067200000, "max_ts": 1704153600000},
            ]
            r = client.get("/backtest/available_data?symbol=BTCUSDT")
            assert r.status_code == 200
            data = json.loads(r.data)
            assert "intervals" in data
            assert "1h" in data["intervals"]
            assert data["intervals"]["1h"]["count"] == 100

    def test_available_data_default_intervals(self, client):
        """返回的 intervals 应包含全部 5 种周期，无数据的 count=0"""
        with patch("app.backtest.routes.list_symbol_intervals") as mock:
            mock.return_value = [
                {"interval": "1h", "count": 50, "min_ts": 0, "max_ts": 999},
            ]
            r = client.get("/backtest/available_data?symbol=NEWCOIN")
            data = json.loads(r.data)
            for iv in ["1m", "5m", "15m", "1h", "4h"]:
                assert iv in data["intervals"]
