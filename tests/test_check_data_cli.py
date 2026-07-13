"""check_data.py CLI 工具单测。"""
import json
import sqlite3
import pytest

from app.backtest.database import init_db, upsert_klines, count_klines


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """临时数据库用于测试。"""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr("app.backtest.database.get_db_path", lambda: db_path)
    import check_data
    monkeypatch.setattr(check_data, "get_db_path", lambda: db_path)
    return db_path


def _klines(symbol: str, interval: str, start_ts: int, n: int, step_ms: int):
    """构造 n 根等间隔 K 线。"""
    return [
        {"symbol": symbol, "interval": interval,
         "timestamp": start_ts + i * step_ms,
         "open": "100", "high": "110", "low": "90", "close": "105",
         "volume": "1.0"}
        for i in range(n)
    ]


class TestCheckDataCLI:
    """check_data.py CLI 测试。"""

    def test_check_all_lists_symbols_intervals(self, tmp_db, capsys):
        """无参数列出所有 symbol/interval 概况。"""
        from check_data import _all_combinations
        # 2 symbol × 2 interval
        upsert_klines(tmp_db, _klines("BTCUSDT", "1h", 1704067200000, 5, 3600000))
        upsert_klines(tmp_db, _klines("BTCUSDT", "4h", 1704067200000, 3, 14400000))
        upsert_klines(tmp_db, _klines("ETHUSDT", "1h", 1704067200000, 7, 3600000))
        upsert_klines(tmp_db, _klines("ETHUSDT", "15m", 1704067200000, 10, 900000))

        rows = _all_combinations(tmp_db)
        assert len(rows) == 4

        import sys
        from unittest.mock import patch
        from check_data import main
        with patch.object(sys, "argv", ["check_data"]):
            main()
        captured = capsys.readouterr().out
        assert "BTCUSDT" in captured
        assert "ETHUSDT" in captured
        assert "1h" in captured

    def test_check_symbol_filter(self, tmp_db, capsys):
        """--symbol 过滤。"""
        from check_data import _filter_rows, _all_combinations
        upsert_klines(tmp_db, _klines("BTCUSDT", "1h", 1704067200000, 5, 3600000))
        upsert_klines(tmp_db, _klines("ETHUSDT", "1h", 1704067200000, 5, 3600000))

        all_rows = _all_combinations(tmp_db)
        filtered = _filter_rows(all_rows, "BTCUSDT", None)
        assert len(filtered) == 1
        assert filtered[0]["symbol"] == "BTCUSDT"

    def test_check_gap_detection(self, tmp_db):
        """在 100 根后插入 4h 间隔，验证空洞数 ≥ 1。"""
        from check_data import _scan_gaps
        # 前 100 根，间隔 1h
        start = 1704067200000
        klines = _klines("BTCUSDT", "1h", start, 100, 3600000)
        # 后 5 根，间隔从 4h 后开始
        tail_start = start + 100 * 3600000 + 4 * 3600000
        klines += _klines("BTCUSDT", "1h", tail_start, 5, 3600000)
        upsert_klines(tmp_db, klines)

        gap = _scan_gaps(tmp_db, "BTCUSDT", "1h",
                         start, tail_start + 5 * 3600000, 1.5)
        assert gap["gaps"] >= 1

    def test_check_empty_db(self, tmp_db, capsys):
        """空库时打印友好提示。"""
        import sys
        from unittest.mock import patch
        from check_data import main
        with patch.object(sys, "argv", ["check_data"]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr().err
        assert "数据库为空" in captured

    def test_check_no_match(self, tmp_db, capsys):
        """symbol 不存在时提示可用 symbol。"""
        from check_data import main
        upsert_klines(tmp_db, _klines("BTCUSDT", "1h", 1704067200000, 5, 3600000))

        import sys
        from unittest.mock import patch
        with patch.object(sys, "argv", ["check_data", "--symbol", "NOPE"]):
            with pytest.raises(SystemExit):
                main()
        captured = capsys.readouterr().err
        assert "未找到匹配" in captured
        assert "BTCUSDT" in captured

    def test_check_json_output(self, tmp_db):
        """--json 输出可被解析。"""
        from check_data import main
        upsert_klines(tmp_db, _klines("BTCUSDT", "1h", 1704067200000, 5, 3600000))

        import sys
        from unittest.mock import patch
        import io
        buf = io.StringIO()
        with patch.object(sys, "argv", ["check_data", "--json", "--symbol", "BTCUSDT", "--interval", "1h"]):
            with patch("sys.stdout", buf):
                main()
        data = json.loads(buf.getvalue())
        assert data["symbol"] == "BTCUSDT"
        assert data["interval"] == "1h"
        assert data["count"] == 5
