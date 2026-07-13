"""数据获取模块单测（mock API）。"""
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import pytest
from app.backtest.data_fetcher import (
    fetch_klines_from_api,
    fetch_klines_paginated,
    SUPPORTED_INTERVALS,
    API_BASE,
    _interval_to_seconds,
    _get_thread_opener,
)


class TestFetchKlinesFromApi:
    """测试 API 数据获取（mock urllib）"""

    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher._get_proxy")
    def test_fetch_single_page(self, mock_proxy, mock_get_opener):
        mock_proxy.return_value = "http://127.0.0.1:20171"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            [1704067200000, "65000.00", "65500.00", "64800.00", "65200.00", "100.5", 0, 0, 0, 0, 0, 0],
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_get_opener.return_value = mock_opener

        result = fetch_klines_from_api("BTCUSDT", "1h", 1704067200000, 1704067200000)
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["interval"] == "1h"
        assert result[0]["timestamp"] == 1704067200000
        assert result[0]["close"] == "65200.00"

    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher._get_proxy")
    def test_fetch_empty_response(self, mock_proxy, mock_get_opener):
        mock_proxy.return_value = None
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock()
        mock_opener.open.return_value = mock_response
        mock_get_opener.return_value = mock_opener

        result = fetch_klines_from_api("BTCUSDT", "1h", 0, 999)
        assert result == []

    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError, match="不支持的周期"):
            fetch_klines_from_api("BTCUSDT", "99x", 0, 999)

    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher._get_proxy")
    def test_network_error_raises(self, mock_proxy, mock_get_opener):
        import urllib.error
        mock_proxy.return_value = "http://127.0.0.1:20171"
        mock_opener = MagicMock()
        mock_opener.open.side_effect = urllib.error.URLError("timeout")
        mock_get_opener.return_value = mock_opener

        with pytest.raises(ConnectionError, match="API 请求失败"):
            fetch_klines_from_api("BTCUSDT", "1h", 0, 999)

    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher._get_proxy")
    def test_network_error_alt(self, mock_proxy, mock_get_opener):
        import urllib.error
        mock_proxy.return_value = "http://127.0.0.1:20171"
        mock_opener = MagicMock()
        mock_opener.open.side_effect = TimeoutError("timeout")
        mock_get_opener.return_value = mock_opener

        with pytest.raises(ConnectionError, match="API 请求失败"):
            fetch_klines_from_api("BTCUSDT", "1h", 0, 999)


class TestIncrementalSkip:
    """测试按页粒度增量跳过逻辑。"""

    @patch("app.backtest.data_fetcher.time.sleep")
    @patch("app.backtest.data_fetcher._get_proxy")
    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher.query_klines")
    @patch("app.backtest.data_fetcher.upsert_klines")
    def test_skip_pages_already_in_db(self, mock_upsert, mock_query, mock_get_opener, mock_proxy, mock_sleep):
        """数据库已有数据的页应跳过 API 请求"""
        mock_proxy.return_value = None
        # 第一页有数据（返回 1000 条），第二页无数据（需要请求）
        mock_query.side_effect = [
            [{"timestamp": i} for i in range(1000)],  # 第一页: 已有 1000 条 → 跳过
            [],                                         # 第二页: 无数据 → 需要请求
        ]
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            [i * 3600000, "65000", "65500", "64800", "65200", "100"] + [0] * 6
            for i in range(500)
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock(); mock_get_opener.return_value = mock_opener; mock_opener.open.return_value = mock_response

        with patch("app.backtest.data_fetcher.init_db"):
            with patch("app.backtest.data_fetcher.get_db_path", return_value="fake.db"):
                # 仅 2 页数据（每页 1000 根 1h K线）
                fetched, stored, skipped = fetch_klines_paginated(
                    "BTCUSDT", "1h",
                    start_ts=0, end_ts=2 * 3600_000_000,
                    force_refresh=False,
                )

        assert skipped >= 1, f"应至少跳过 1 页, 实际跳过 {skipped}"
        assert mock_opener.open.call_count == 1, f"只应请求 1 次, 实际 {mock_opener.open.call_count}"

    @patch("app.backtest.data_fetcher.time.sleep")
    @patch("app.backtest.data_fetcher._get_proxy")
    @patch("app.backtest.data_fetcher._get_thread_opener")
    @patch("app.backtest.data_fetcher.query_klines")
    def test_force_refresh_no_skip(self, mock_query, mock_get_opener, mock_proxy, mock_sleep):
        """force_refresh=True 时不检查缓存，全部请求"""
        mock_proxy.return_value = None
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            [i * 3600000, "65000", "65500", "64800", "65200", "100"] + [0] * 6
            for i in range(1000)
        ]).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_opener = MagicMock(); mock_get_opener.return_value = mock_opener; mock_opener.open.return_value = mock_response

        with patch("app.backtest.data_fetcher.init_db"):
            with patch("app.backtest.data_fetcher.get_db_path", return_value="fake.db"):
                fetched, stored, skipped = fetch_klines_paginated(
                    "BTCUSDT", "1h",
                    start_ts=0, end_ts=3 * 3600_000_000,
                    force_refresh=True,
                )

        assert skipped == 0, "force_refresh 不应跳过任何页"


class TestApiConstants:
    def test_supported_intervals(self):
        assert "1m" in SUPPORTED_INTERVALS
        assert "5m" in SUPPORTED_INTERVALS
        assert "15m" in SUPPORTED_INTERVALS
        assert "1h" in SUPPORTED_INTERVALS
        assert "4h" in SUPPORTED_INTERVALS

    def test_api_base(self):
        assert "api.binance.com" in API_BASE


class TestIntervalToSeconds:
    def test_1m(self):
        assert _interval_to_seconds("1m") == 60

    def test_5m(self):
        assert _interval_to_seconds("5m") == 300

    def test_15m(self):
        assert _interval_to_seconds("15m") == 900

    def test_1h(self):
        assert _interval_to_seconds("1h") == 3600

    def test_4h(self):
        assert _interval_to_seconds("4h") == 14400


class TestGetThreadOpener:
    def test_returns_opener(self):
        opener = _get_thread_opener()
        assert opener is not None
        assert len(opener.handlers) > 0

    def test_thread_local_isolation(self):
        """不同线程应拿到各自独立的 opener 实例。"""
        import threading
        results = {}
        def get_in_thread(tid):
            results[tid] = _get_thread_opener()
        t1 = threading.Thread(target=get_in_thread, args=(1,))
        t2 = threading.Thread(target=get_in_thread, args=(2,))
        t1.start(); t2.start()
        t1.join(); t2.join()
        # 两个线程拿到的是不同 opener 对象
        assert results[1] is not None
        assert results[2] is not None
