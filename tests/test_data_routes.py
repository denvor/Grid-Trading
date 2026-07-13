"""数据展示页路由测试。"""
import pytest
from unittest.mock import patch


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestDataOverview:
    def test_get_data_page(self, client):
        r = client.get("/data")
        assert r.status_code == 200

    def test_get_data_page_lists_symbols(self, client):
        r = client.get("/data")
        body = r.data.decode()
        assert "BTCUSDT" in body

    def test_post_select_symbol_shows_intervals(self, client):
        """选 symbol → 显示可用周期表"""
        with patch("app.backtest.data_routes.list_symbol_intervals") as mock_list:
            mock_list.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 0, "max_ts": 999999},
                {"interval": "4h", "count": 50, "min_ts": 0, "max_ts": 999999},
            ]
            r = client.post("/data", data={"symbol": "BTCUSDT"})
            assert r.status_code == 200
            body = r.data.decode()
            assert "可用周期" in body
            assert "1h" in body
            assert "4h" in body

    def test_post_view_data_shows_summary(self, client):
        """选择 symbol+interval+点击查看 → 返回 OHLCV 汇总"""
        with patch("app.backtest.data_routes.list_symbol_intervals") as mock_list, \
             patch("app.backtest.data_routes.count_klines_in_range") as mock_cnt, \
             patch("app.backtest.data_routes.get_interval_range") as mock_range, \
             patch("app.backtest.data_routes.get_interval_summary") as mock_summary:
            mock_list.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 0, "max_ts": 999999},
            ]
            mock_range.return_value = {"min_ts": 0, "max_ts": 999999, "count": 100}
            mock_cnt.return_value = 5
            mock_summary.return_value = {
                "open_first": "65000", "close_last": "65200",
                "high_max": "65500", "low_min": "64800", "count": 5,
            }
            r = client.post("/data", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "start_time": "2024-01-01", "end_time": "2024-01-05",
                "view_data": "1",
            })
            assert r.status_code == 200
            body = r.data.decode()
            assert "65000" in body  # open_first
            assert "65500" in body  # high_max
            assert "64800" in body  # low_min

    def test_post_view_data_shows_summary_only(self, client):
        """点查看 → 返回汇总（K线明细走 AJAX，不再嵌入）"""
        with patch("app.backtest.data_routes.list_symbol_intervals") as mock_list, \
             patch("app.backtest.data_routes.count_klines_in_range") as mock_cnt, \
             patch("app.backtest.data_routes.get_interval_range") as mock_range, \
             patch("app.backtest.data_routes.get_interval_summary") as mock_summary:
            mock_list.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 0, "max_ts": 999999},
            ]
            mock_range.return_value = {"min_ts": 0, "max_ts": 999999, "count": 100}
            mock_cnt.return_value = 3
            mock_summary.return_value = {
                "open_first": "65000", "close_last": "65200",
                "high_max": "65500", "low_min": "64800", "count": 3,
            }
            r = client.post("/data", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "view_data": "1",
            })
            body = r.data.decode()
            assert "K线明细" in body
            # summary 中显示总数
            assert "3" in body
            # K 线明细容器存在
            assert 'id="klines-section"' in body

    def test_data_klines_endpoint(self, client):
        """AJAX 分页接口 /data/klines 返回正确页"""
        with patch("app.backtest.data_routes.query_klines_paginated") as mock_query, \
             patch("app.backtest.data_routes.count_klines_in_range") as mock_cnt, \
             patch("app.backtest.data_routes.get_interval_range") as mock_range:
            mock_range.return_value = {"min_ts": 0, "max_ts": 999999, "count": 120}
            mock_cnt.return_value = 120
            def query_side_effect(db, sym, iv, s, e, offset, limit):
                start = offset
                end = min(offset + limit, 120)
                return [
                    {"timestamp": i, "open": "65000", "high": "65500",
                     "low": "64800", "close": "65200", "volume": "100"}
                    for i in range(start, end)
                ]
            mock_query.side_effect = query_side_effect

            r = client.get("/data/klines?symbol=BTCUSDT&interval=1h&page=1")
            assert r.status_code == 200
            d = r.get_json()
            assert d["total"] == 120
            assert d["page"] == 1
            assert d["page_size"] == 50
            assert d["total_pages"] == 3
            assert len(d["klines"]) == 50
            # 第 2 页
            r2 = client.get("/data/klines?symbol=BTCUSDT&interval=1h&page=2")
            d2 = r2.get_json()
            assert len(d2["klines"]) == 50
            # 第 3 页（余 20 条）
            r3 = client.get("/data/klines?symbol=BTCUSDT&interval=1h&page=3")
            d3 = r3.get_json()
            assert len(d3["klines"]) == 20
            # 越界 → 夹到最后一页
            r4 = client.get("/data/klines?symbol=BTCUSDT&interval=1h&page=99")
            d4 = r4.get_json()
            assert d4["page"] == 3

    def test_base_html_uses_url_for_data(self, client):
        """base.html 数据展示入口用 url_for（不再是硬编码 /data）"""
        import os
        base_dir = os.path.abspath(os.path.dirname(__file__))
        tpl = os.path.join(base_dir, "..", "app", "templates", "base.html")
        with open(tpl, "r", encoding="utf-8") as f:
            source = f.read()
        assert "url_for('backtest.data_index')" in source
        assert 'href="/data"' not in source
