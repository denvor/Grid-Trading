"""数据库模块单测。"""
import os
import sqlite3
import pytest
from app.backtest.database import init_db, upsert_klines, query_klines, count_klines


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """临时数据库用于测试"""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


class TestDatabase:
    def test_init_creates_table(self, tmp_db):
        conn = sqlite3.connect(tmp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='klines'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_upsert_and_query(self, tmp_db):
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000,
             "open": "65000.00", "high": "65500.00", "low": "64800.00",
             "close": "65200.00", "volume": "100.5"},
        ]
        upsert_klines(tmp_db, klines)
        result = query_klines(tmp_db, "BTCUSDT", "1h", 1704067200000, 1704067200000)
        assert len(result) == 1
        assert result[0]["close"] == "65200.00"

    def test_upsert_is_idempotent(self, tmp_db):
        kline = {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000,
                 "open": "65000.00", "high": "65500.00", "low": "64800.00",
                 "close": "65200.00", "volume": "100.5"}
        upsert_klines(tmp_db, [kline])
        # 用新价格 upsert 同一条 → 应覆盖
        kline["close"] = "66000.00"
        upsert_klines(tmp_db, [kline])
        result = query_klines(tmp_db, "BTCUSDT", "1h", 1704067200000, 1704067200000)
        assert len(result) == 1
        assert result[0]["close"] == "66000.00"

    def test_query_empty_result(self, tmp_db):
        result = query_klines(tmp_db, "NOTEXIST", "1h", 0, 9999999999999)
        assert result == []

    def test_count_klines(self, tmp_db):
        assert count_klines(tmp_db, "BTCUSDT", "1h") == 0
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": i * 3600000,
             "open": "65000", "high": "65500", "low": "64800",
             "close": "65200", "volume": "100"}
            for i in range(5)
        ]
        upsert_klines(tmp_db, klines)
        assert count_klines(tmp_db, "BTCUSDT", "1h") == 5


class TestDataOverviewQueries:
    """测试数据概览查询函数"""

    def test_list_symbol_intervals(self, tmp_db):
        """返回 symbol 拥有的 interval 列表及统计"""
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000 + i*3600000,
             "open": "65000", "high": "65500", "low": "64800", "close": "65200", "volume": "100"}
            for i in range(5)
        ] + [
            {"symbol": "BTCUSDT", "interval": "4h", "timestamp": 1704067200000 + i*14400000,
             "open": "65000", "high": "65500", "low": "64800", "close": "65200", "volume": "100"}
            for i in range(3)
        ]
        from app.backtest.database import upsert_klines, list_symbol_intervals
        upsert_klines(tmp_db, klines)
        result = list_symbol_intervals(tmp_db, "BTCUSDT")
        assert len(result) == 2
        intervals = {r["interval"] for r in result}
        assert "1h" in intervals
        assert "4h" in intervals
        for r in result:
            assert "count" in r
            assert "min_ts" in r
            assert "max_ts" in r

    def test_get_interval_range(self, tmp_db):
        """返回指定 symbol+interval 的最早和最晚时间戳"""
        klines = [
            {"symbol": "ETHUSDT", "interval": "15m", "timestamp": 1704067200000 + i*900000,
             "open": "3500", "high": "3550", "low": "3480", "close": "3520", "volume": "100"}
            for i in range(10)
        ]
        from app.backtest.database import upsert_klines, get_interval_range
        upsert_klines(tmp_db, klines)
        result = get_interval_range(tmp_db, "ETHUSDT", "15m")
        assert result is not None
        assert result["min_ts"] == 1704067200000
        assert result["max_ts"] == 1704067200000 + 9 * 900000
        # 不存在的返回 None
        assert get_interval_range(tmp_db, "ETHUSDT", "1m") is None

    def test_get_interval_summary(self, tmp_db):
        """返回 OHLCV 汇总统计"""
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000 + i*3600000,
             "open": str(65000 + i*10), "high": str(66000 + i*10),
             "low": str(64000 + i*10), "close": str(65500 + i*10), "volume": "100"}
            for i in range(5)
        ]
        from app.backtest.database import upsert_klines, get_interval_summary
        upsert_klines(tmp_db, klines)
        s = get_interval_summary(tmp_db, "BTCUSDT", "1h",
                                1704067200000, 1704067200000 + 4*3600000)
        assert s is not None
        assert s["open_first"] == "65000"
        assert s["close_last"] == "65540"
        assert float(s["high_max"]) == 66040.0
        assert float(s["low_min"]) == 64000.0
        assert s["count"] == 5
        # 不存在的 symbol 返回 None
        assert get_interval_summary(tmp_db, "NOPE", "1h", 0, 99999) is None
