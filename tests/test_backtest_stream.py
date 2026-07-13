"""SSE 流式回测路由 + progress_callback 单测。"""
import json
import pytest
from decimal import Decimal

from app import create_app
from app.backtest.database import init_db, upsert_klines
from app.backtest.engine import backtest


def _make_kline(ts, o, h, l, c, sym="BTCUSDT", iv="1h"):
    return {"symbol": sym, "interval": iv, "timestamp": ts,
            "open": o, "high": h, "low": l, "close": c, "volume": "1"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    """构造测试用 Flask app + 临时 DB。"""
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    monkeypatch.setattr("app.backtest.database.get_db_path", lambda: db_path)
    monkeypatch.setattr("app.backtest.data_fetcher.get_db_path", lambda: db_path)
    # 插入测试 K 线
    klines = [_make_kline(i * 3600000, "100", "110", "90", "105") for i in range(50)]
    upsert_klines(db_path, klines)
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestProgressCallback:
    """测试 progress_callback 契约。"""

    def test_progress_callback_called(self, app):
        """progress_callback 被调用、最终 percent==100。"""
        klines = [_make_kline(i * 3600000, "100", "110", "90", "105") for i in range(200)]
        calls = []
        def cb(percent, kline_index, total, elapsed_ms, trades):
            calls.append((percent, kline_index, total, trades))
        backtest(klines=klines, capital=Decimal("10000"),
                  upper_price=Decimal("110"), lower_price=Decimal("90"),
                  grid_size=Decimal("5"), quantity_per_grid=Decimal("0.01"),
                  progress_callback=cb)
        assert len(calls) > 0, "callback 应被调用"
        assert calls[-1][0] == 100, f"最终 percent 应为 100, 实际 {calls[-1][0]}"
        # percent 单调非递减
        percents = [c[0] for c in calls]
        assert percents == sorted(percents), "percent 应单调非递减"

    def test_result_unchanged_with_callback(self, app):
        """with/without callback 最终 result 相同（数学不变）。"""
        klines = [_make_kline(i * 3600000, "100", "110", "90", "105") for i in range(100)]
        def cb(*args): pass
        r1 = backtest(klines=klines, capital=Decimal("10000"),
                      upper_price=Decimal("110"), lower_price=Decimal("90"),
                      grid_size=Decimal("5"), quantity_per_grid=Decimal("0.01"))
        r2 = backtest(klines=klines, capital=Decimal("10000"),
                      upper_price=Decimal("110"), lower_price=Decimal("90"),
                      grid_size=Decimal("5"), quantity_per_grid=Decimal("0.01"),
                      progress_callback=cb)
        assert r1["total_trades"] == r2["total_trades"]
        assert r1["final_capital"] == r2["final_capital"]
        assert r1["total_return_pct"] == r2["total_return_pct"]


class TestStreamRoute:
    """测试 /backtest/stream SSE 路由。"""

    def test_stream_returns_400_on_missing_params(self, client):
        """缺参数返回 400。"""
        r = client.get("/backtest/stream?symbol=BTCUSDT&interval=1h")
        assert r.status_code == 400

    def test_stream_returns_400_on_missing_klines(self, client, monkeypatch, tmp_path):
        """DB 无数据返回 400。"""
        # 用空 DB
        empty = str(tmp_path / "empty.db")
        init_db(empty)
        monkeypatch.setattr("app.backtest.database.get_db_path", lambda: empty)
        monkeypatch.setattr("app.backtest.data_fetcher.get_db_path", lambda: empty)
        r = client.get("/backtest/stream?symbol=BTCUSDT&interval=1h&capital=10000"
                       "&upper_price=110&lower_price=90&grid_size=5"
                       "&quantity_per_grid=0.01&start_time=2024-01-01&end_time=2024-01-05")
        assert r.status_code == 400

    def test_stream_done_event_includes_result(self, client):
        """成功流：done 事件包含 result 字段。"""
        # 测试 K 线时间戳从 0 (1970-01-01) 开始
        r = client.get("/backtest/stream?symbol=BTCUSDT&interval=1h&capital=10000"
                       "&upper_price=110&lower_price=90&grid_size=5"
                       "&quantity_per_grid=0.01&start_time=1970-01-01&end_time=1970-01-03")
        assert r.status_code == 200
        assert "text/event-stream" in r.content_type
        # 解析 SSE 帧
        body = r.data.decode()
        assert "event: done" in body
        # 提取 done 事件的 data JSON
        for line in body.split("\n"):
            if line.startswith("event: done"):
                break
        # 找下一个 data: 行
        lines = body.split("\n")
        done_idx = next(i for i, l in enumerate(lines) if l.startswith("event: done"))
        data_line = lines[done_idx + 1] if done_idx + 1 < len(lines) else ""
        assert data_line.startswith("data: ")
        payload = json.loads(data_line[6:])
        assert "result" in payload
        assert "total_trades" in payload["result"]
