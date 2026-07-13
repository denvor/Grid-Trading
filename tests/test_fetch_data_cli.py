"""CLI 工具单测。"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestFetchDataCLI:
    """测试 CLI 工具。"""

    def test_parse_args_required(self):
        """缺必填参数应退出"""
        from fetch_data import parse_args
        with pytest.raises(SystemExit):
            parse_args([])

    def test_parse_args_full(self):
        """完整参数解析"""
        from fetch_data import parse_args
        args = parse_args([
            "--symbol", "BTCUSDT",
            "--interval", "1h",
            "--start", "2024-01-01",
            "--end", "2024-03-01",
        ])
        assert args.symbol == "BTCUSDT"
        assert args.interval == "1h"
        assert args.start == "2024-01-01"
        assert args.end == "2024-03-01"
        assert args.force is False

    def test_parse_args_force(self):
        """--force 参数"""
        from fetch_data import parse_args
        args = parse_args(["--symbol", "ETHUSDT", "--interval", "15m",
                          "--start", "2024-01-01", "--force"])
        assert args.force is True

    def test_parse_args_minimal(self):
        """最小参数（无 --end）"""
        from fetch_data import parse_args
        args = parse_args(["--symbol", "BTCUSDT", "--interval", "1h",
                          "--start", "2024-01-01"])
        assert args.symbol == "BTCUSDT"
        assert args.end is None
        assert args.force is False

    def test_date_to_timestamp(self):
        """日期字符串转毫秒时间戳"""
        from fetch_data import _date_to_ms
        ts = _date_to_ms("2024-01-01")
        assert isinstance(ts, int)
        # 2024-01-01 00:00:00 UTC = 1704067200000
        assert ts == 1704067200000

    def test_date_to_timestamp_with_time(self):
        """带时间的日期"""
        from fetch_data import _date_to_ms
        ts = _date_to_ms("2024-06-15")
        # 验证是 13 位毫秒时间戳
        assert len(str(ts)) == 13
