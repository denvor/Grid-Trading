# Backtest Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建独立的回测系统：通过 CLI 从币安拉取历史K线到本地 SQLite，Web 端读取数据库模拟网格策略执行，输出收益率/最大回撤/胜率等统计。

**Architecture:** 独立 CLI (`fetch_data.py`) + 包 (`app/backtest/`)。`data_fetcher.py` 是 CLI 和 Web 共用的核心模块，`database.py` 封装 SQLite CRUD，`engine.py` 实现回测模拟。复用现有 `config_loader.py` 的 config.ini 读取模式、`decimal.Decimal` 精度处理、DeFi 玻璃主题 UI。

**Tech Stack:** Python 3.x, Flask, Jinja2, SQLite3（标准库）, urllib（标准库）, decimal（标准库）

---

## File Structure

```
fetch_data.py                 # ← 独立 CLI（项目根目录）
app/backtest/
├── __init__.py               # Blueprint 注册（backtest_bp）
├── database.py               # SQLite 初始化 + CRUD
├── data_fetcher.py           # 币安 API 获取 + DB 读写（CLI + Web 共用）
├── engine.py                 # 回测核心逻辑
└── routes.py                 # /backtest 路由
app/templates/backtest/
├── index.html                # 回测参数表单
└── result.html               # 回测结果
data/
└── klines.db                 # SQLite 数据库（不入 git）
tests/
├── test_database.py
├── test_data_fetcher.py
├── test_fetch_data_cli.py
├── test_backtest_engine.py
└── test_backtest_routes.py
```

---

## Task 1: 数据库模块

**Files:**
- Create: `app/backtest/__init__.py`
- Create: `app/backtest/database.py`
- Create: `tests/test_database.py`
- Modify: `.gitignore`

- [ ] **Step 1: 写失败测试**

`tests/test_database.py`:
```python
import os
import sqlite3
import pytest
from app.backtest.database import init_db, get_connection, upsert_klines, query_klines


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """临时数据库用于测试"""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    init_db(db_path)
    return db_path


class TestDatabase:
    def test_init_creates_table(self, tmp_db):
        conn = get_connection(tmp_db)
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
pytest tests/test_database.py -v
```
预期：`ModuleNotFoundError: No module named 'app.backtest'`

- [ ] **Step 3: 创建 `app/backtest/__init__.py`**

```python
"""回测功能包。"""
from flask import Blueprint

backtest_bp = Blueprint("backtest", __name__, template_folder="templates")

from app.backtest import routes  # noqa: E402
```

- [ ] **Step 4: 实现 `app/backtest/database.py`**

```python
"""SQLite 数据库操作。"""
import sqlite3


def init_db(db_path: str) -> None:
    """初始化数据库,创建 klines 表（如果不存在）。"""
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS klines (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open TEXT NOT NULL,
                high TEXT NOT NULL,
                low TEXT NOT NULL,
                close TEXT NOT NULL,
                volume TEXT NOT NULL,
                PRIMARY KEY (symbol, interval, timestamp)
            )
        """)


def get_connection(db_path: str) -> sqlite3.Connection:
    """获取数据库连接。"""
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_klines(db_path: str, klines: list[dict]) -> int:
    """批量插入/替换K线数据。返回写入条数。"""
    if not klines:
        return 0
    with sqlite3.connect(db_path) as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO klines
            (symbol, interval, timestamp, open, high, low, close, volume)
            VALUES (:symbol, :interval, :timestamp, :open, :high, :low, :close, :volume)
        """, klines)
    return len(klines)


def query_klines(db_path: str, symbol: str, interval: str,
                 start_ts: int, end_ts: int) -> list[dict]:
    """查询指定范围的K线数据。"""
    conn = get_connection(db_path)
    cursor = conn.execute("""
        SELECT symbol, interval, timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
    """, (symbol, interval, start_ts, end_ts))
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def count_klines(db_path: str, symbol: str, interval: str) -> int:
    """统计指定交易对+周期的K线总数。"""
    conn = get_connection(db_path)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM klines WHERE symbol = ? AND interval = ?",
        (symbol, interval)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count
```

- [ ] **Step 5: 更新 `.gitignore`**

追加：
```
data/
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_database.py -v
```
预期：4 个 PASS

- [ ] **Step 7: 提交**

```bash
git add app/backtest/__init__.py app/backtest/database.py tests/test_database.py .gitignore
git commit -m "feat(backtest): add SQLite database module for klines storage"
```

---

## Task 2: 数据获取模块（CLI + Web 共用）

**Files:**
- Create: `app/backtest/data_fetcher.py`
- Create: `tests/test_data_fetcher.py`

- [ ] **Step 1: 写失败测试（mock API 调用）**

`tests/test_data_fetcher.py`:
```python
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
import pytest
from app.backtest.data_fetcher import (
    fetch_klines_from_api,
    fetch_and_store,
    API_BASE,
    SUPPORTED_INTERVALS,
)


class TestFetchKlinesFromApi:
    """测试 API 数据获取（mock urllib）"""

    @patch("app.backtest.data_fetcher._get_proxy")
    @patch("app.backtest.data_fetcher.urlopen")
    def test_fetch_single_page(self, mock_urlopen, mock_proxy):
        mock_proxy.return_value = "http://127.0.0.1:20171"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([
            [1704067200000, "65000.00", "65500.00", "64800.00", "65200.00", "100.5", 0, 0, 0, 0, 0, 0],
        ]).encode()
        mock_urlopen.return_value = mock_response

        result = fetch_klines_from_api("BTCUSDT", "1h", 1704067200000, 1704067200000)
        assert len(result) == 1
        assert result[0]["symbol"] == "BTCUSDT"
        assert result[0]["interval"] == "1h"
        assert result[0]["timestamp"] == 1704067200000
        assert result[0]["close"] == "65200.00"

    @patch("app.backtest.data_fetcher._get_proxy")
    @patch("app.backtest.data_fetcher.urlopen")
    def test_fetch_with_proxy(self, mock_urlopen, mock_proxy):
        mock_proxy.return_value = "http://127.0.0.1:20171"
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value = mock_response

        fetch_klines_from_api("BTCUSDT", "1h", 0, 999)
        # 验证代理被设置
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "api.binance.com" in request.full_url

    def test_invalid_interval_raises(self):
        with pytest.raises(ValueError, match="不支持的周期"):
            fetch_klines_from_api("BTCUSDT", "99x", 0, 999)


class TestApiConstants:
    def test_supported_intervals(self):
        assert "1m" in SUPPORTED_INTERVALS
        assert "5m" in SUPPORTED_INTERVALS
        assert "15m" in SUPPORTED_INTERVALS
        assert "1h" in SUPPORTED_INTERVALS
        assert "4h" in SUPPORTED_INTERVALS

    def test_api_base(self):
        assert "api.binance.com" in API_BASE
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_data_fetcher.py -v
```
预期：`ModuleNotFoundError`

- [ ] **Step 3: 实现 `app/backtest/data_fetcher.py`**

```python
"""币安 API 数据获取 + DB 读写（CLI + Web 共用）。"""
import json
import time
import urllib.request
import urllib.error
import os
from decimal import Decimal

from app.backtest.database import init_db, get_connection, upsert_klines, query_klines, count_klines

API_BASE = "https://api.binance.com/api/v3/klines"
SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "4h"}
MAX_LIMIT = 1000


def _get_db_path() -> str:
    """从 config.ini 读取数据库路径。"""
    from app.backtest.database import _read_config
    return _read_config("database", "path", "data/klines.db")


def _get_proxy() -> str | None:
    """从 config.ini 读取代理地址。"""
    from app.backtest.database import _read_config
    proxy = _read_config("api", "proxy", None)
    return proxy if proxy else None


def _get_request_interval() -> float:
    """从 config.ini 读取请求间隔秒数。"""
    from app.backtest.database import _read_config
    return float(_read_config("api", "request_interval", "1.0"))


def _build_opener(proxy: str | None) -> urllib.request.OpenerDirector:
    """构建带代理的 URL opener。"""
    if proxy:
        handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        return urllib.request.build_opener(handler)
    return urllib.request.build_opener()


def fetch_klines_from_api(symbol: str, interval: str,
                          start_ts: int, end_ts: int) -> list[dict]:
    """从币安 API 获取单页K线数据。

    Args:
        symbol: 交易对，如 BTCUSDT
        interval: K线周期，如 1h
        start_ts: 开始时间戳（毫秒）
        end_ts: 结束时间戳（毫秒）

    Returns:
        K线列表，每项为 dict
    """
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"不支持的周期: {interval}，支持: {SUPPORTED_INTERVALS}")

    url = f"{API_BASE}?symbol={symbol}&interval={interval}&startTime={start_ts}&endTime={end_ts}&limit={MAX_LIMIT}"
    opener = _build_opener(_get_proxy())

    try:
        with opener.open(url, timeout=15) as response:
            raw = json.loads(response.read().decode())
    except (urllib.error.URLError, TimeoutError) as e:
        raise ConnectionError(f"API 请求失败: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"API 返回数据解析失败: {e}") from e

    klines = []
    for item in raw:
        # [timestamp, open, high, low, close, volume, ...]
        klines.append({
            "symbol": symbol,
            "interval": interval,
            "timestamp": item[0],
            "open": item[1],
            "high": item[2],
            "low": item[3],
            "close": item[4],
            "volume": item[5],
        })
    return klines


def fetch_klines_paginated(symbol: str, interval: str,
                           start_ts: int, end_ts: int,
                           force_refresh: bool = False,
                           progress_callback=None) -> tuple[int, int]:
    """分页获取所有K线数据。

    Returns:
        (total_fetched, total_stored) — API 获取条数, 实际存入条数
    """
    db_path = _get_db_path()
    init_db(db_path)

    interval_seconds = _interval_to_seconds(interval)
    page_duration_ms = MAX_LIMIT * interval_seconds * 1000

    total_fetched = 0
    total_stored = 0
    request_interval = _get_request_interval()

    if force_refresh:
        # 强制刷新：直接拉取全部
        current_start = start_ts
        while current_start < end_ts:
            current_end = min(current_start + page_duration_ms, end_ts)
            klines = fetch_klines_from_api(symbol, interval, current_start, current_end)
            if not klines:
                break
            total_fetched += len(klines)
            upsert_klines(db_path, klines)
            total_stored += len(klines)
            if progress_callback:
                progress_callback(total_fetched, current_end, end_ts)
            current_start = klines[-1]["timestamp"] + 1
            time.sleep(request_interval)
    else:
        # 智能增量：先查数据库缺失部分
        existing = query_klines(db_path, symbol, interval, start_ts, end_ts)
        if existing:
            # 已存在直接返回
            return 0, len(existing)
        # 不存在，全量拉取
        current_start = start_ts
        while current_start < end_ts:
            current_end = min(current_start + page_duration_ms, end_ts)
            klines = fetch_klines_from_api(symbol, interval, current_start, current_end)
            if not klines:
                break
            total_fetched += len(klines)
            upsert_klines(db_path, klines)
            total_stored += len(klines)
            if progress_callback:
                progress_callback(total_fetched, current_end, end_ts)
            current_start = klines[-1]["timestamp"] + 1
            time.sleep(request_interval)

    return total_fetched, total_stored


def _interval_to_seconds(interval: str) -> int:
    """周期转秒数。"""
    mapping = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}
    return mapping[interval]


def get_stored_klines(symbol: str, interval: str,
                      start_ts: int, end_ts: int) -> list[dict]:
    """从数据库读取K线数据。"""
    db_path = _get_db_path()
    init_db(db_path)
    return query_klines(db_path, symbol, interval, start_ts, end_ts)


def get_stored_count(symbol: str, interval: str) -> int:
    """获取数据库中某交易对的K线总数。"""
    db_path = _get_db_path()
    init_db(db_path)
    return count_klines(db_path, symbol, interval)
```

- [ ] **Step 4: 更新 `database.py` 添加 `_read_config` 辅助函数**

追加到 `database.py`:

```python
import configparser as _configparser
import os as _os

_CONFIG_PATH = _os.path.join(_os.path.dirname(__file__), "..", "..", "config.ini")
_config_parser = _configparser.ConfigParser()
_config_parser.read(_CONFIG_PATH, encoding="utf-8")


def _read_config(section: str, key: str, default: str | None = None) -> str | None:
    """从 config.ini 读取配置值。"""
    try:
        return _config_parser.get(section, key)
    except (_configparser.NoSectionError, _configparser.NoOptionError):
        return default
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_data_fetcher.py -v
```
预期：全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/backtest/data_fetcher.py app/backtest/database.py tests/test_data_fetcher.py
git commit -m "feat(backtest): add data fetcher with Binance API + proxy support"
```

---

## Task 3: 独立 CLI 工具

**Files:**
- Create: `fetch_data.py`
- Create: `tests/test_fetch_data_cli.py`

- [ ] **Step 1: 写失败测试**

`tests/test_fetch_data_cli.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
import json


class TestFetchDataCLI:
    """测试 CLI 工具。"""

    def test_parse_args_required(self, capsys):
        """缺必填参数应打印用法并退出"""
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

    def test_date_to_timestamp(self):
        """日期字符串转毫秒时间戳"""
        from fetch_data import _date_to_ms
        ts = _date_to_ms("2024-01-01")
        assert isinstance(ts, int)
        assert ts == 1704067200000  # UTC 毫秒时间戳
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_fetch_data_cli.py -v
```
预期：`ModuleNotFoundError`

- [ ] **Step 3: 实现 `fetch_data.py`**

```python
#!/usr/bin/env python3
"""独立 CLI 工具：从币安获取历史K线数据并存入数据库。

用法:
    python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01
    python fetch_data.py --symbol ETHUSDT --interval 15m --start 2024-06-01 --force
"""
import argparse
import sys
import time
from datetime import datetime, timezone

from app.backtest.data_fetcher import (
    fetch_klines_paginated,
    get_stored_count,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="从币安获取历史K线数据")
    parser.add_argument("--symbol", required=True, help="交易对，如 BTCUSDT")
    parser.add_argument("--interval", required=True,
                        choices=["1m", "5m", "15m", "1h", "4h"],
                        help="K线周期")
    parser.add_argument("--start", required=True, help="开始日期, 如 2024-01-01")
    parser.add_argument("--end", required=False, help="结束日期, 默认今天")
    parser.add_argument("--force", action="store_true", help="强制刷新（忽略缓存）")
    return parser.parse_args(argv)


def _date_to_ms(date_str: str) -> int:
    """日期字符串 'YYYY-MM-DD' 转为毫秒时间戳 (UTC)。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _progress_callback(fetched: int, current_end: int, total_end: int):
    """打印进度。"""
    total_ms = total_end - (total_end - fetched * 3600000)  # 近似
    pct = min(100, int((current_end - (total_end - fetched * 3600000)) / max(1, total_end) * 100))
    print(f"  已获取 {fetched} 根K线...", end="\r", flush=True)


def main():
    """CLI 主函数。"""
    args = parse_args()

    start_ts = _date_to_ms(args.start)
    if args.end:
        end_ts = _date_to_ms(args.end)
    else:
        end_ts = int(time.time() * 1000)

    if end_ts <= start_ts:
        print("错误：结束时间必须晚于开始时间", file=sys.stderr)
        sys.exit(1)

    # 检查缓存
    existing_count = get_stored_count(args.symbol, args.interval)
    if existing_count > 0 and not args.force:
        print(f"数据库中已有 {args.symbol} {args.interval} 的 {existing_count} 根K线数据。")
        print("添加 --force 强制刷新。")
        return

    print(f"开始获取 {args.symbol} {args.interval} 从 {args.start} 到 {args.end or '今天'}...")

    total_fetched, total_stored = fetch_klines_paginated(
        symbol=args.symbol,
        interval=args.interval,
        start_ts=start_ts,
        end_ts=end_ts,
        force_refresh=args.force,
        progress_callback=_progress_callback,
    )

    print(f"\n完成！获取 {total_fetched} 根K线，存入数据库 {total_stored} 条。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_fetch_data_cli.py -v
```
预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add fetch_data.py tests/test_fetch_data_cli.py
git commit -m "feat(backtest): add standalone CLI tool for data fetching"
```

---

## Task 4: 回测引擎

**Files:**
- Create: `app/backtest/engine.py`
- Create: `tests/test_backtest_engine.py`

- [ ] **Step 1: 写失败测试**

`tests/test_backtest_engine.py`:
```python
from decimal import Decimal
import pytest
from app.backtest.engine import backtest, generate_equity_curve


def _make_kline(ts: int, open_p: str, high_p: str, low_p: str, close_p: str) -> dict:
    """构造测试用K线。"""
    return {"timestamp": ts, "open": open_p, "high": high_p,
            "low": low_p, "close": close_p, "volume": "100"}


class TestBacktestEngine:
    """测试回测核心逻辑。"""

    def test_no_trades_when_price_flat(self):
        """价格不变 → 无成交。"""
        klines = [_make_kline(i * 3600000, "65000", "65000", "65000", "65000")
                  for i in range(10)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["total_trades"] == 0
        assert result["final_capital"] == Decimal("10000")

    def test_buy_and_sell_profit(self):
        """价格穿越网格 → 有买卖成交。"""
        klines = [
            _make_kline(0, "65000", "65000", "65000", "65000"),     # 入场
            _make_kline(3600000, "65000", "65000", "64500", "64500"),  # 跌到 64500
            _make_kline(7200000, "64500", "65000", "64500", "65000"),  # 涨回 65000 → 卖
        ]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["total_trades"] >= 2  # 至少 1 买 + 1 卖

    def test_total_return_calculation(self):
        """总收益率 = (最终 - 初始) / 初始 × 100。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(100)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        expected_return = ((result["final_capital"] - Decimal("10000")) / Decimal("10000") * Decimal("100")).quantize(Decimal("0.01"))
        assert result["total_return_pct"] == expected_return

    def test_max_drawdown_is_positive(self):
        """最大回撤 ≥ 0。"""
        klines = [_make_kline(i * 3600000, str(65000 - i * 100), "65000", str(64000 - i * 100), str(65000 - i * 100))
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("60000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert result["max_drawdown_pct"] >= Decimal("0")

    def test_win_rate_between_0_and_100(self):
        """胜率在 0-100% 之间。"""
        klines = [_make_kline(i * 3600000, "65000", "65500", "64500", "65000")
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert Decimal("0") <= result["win_rate_pct"] <= Decimal("100")

    def test_capital_insufficient_guard(self):
        """资金不足时不再开新仓。"""
        klines = [_make_kline(i * 3600000, str(65000 - i * 500), "65000", str(64000 - i * 500), str(65000 - i * 500))
                  for i in range(20)]
        result = backtest(
            klines=klines,
            capital=Decimal("100"),  # 极少资金
            upper_price=Decimal("66000"),
            lower_price=Decimal("60000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        # 资金不足，不应亏损超过本金
        assert result["final_capital"] >= Decimal("0")


class TestEquityCurve:
    def test_curve_length_equals_klines_plus_one(self):
        """资金曲线长度 = K线数 + 1（含初始点）。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(10)]
        curve = generate_equity_curve(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert len(curve) == len(klines) + 1

    def test_curve_starts_with_initial_capital(self):
        """资金曲线起点 = 初始资金。"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(5)]
        curve = generate_equity_curve(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert curve[0]["capital"] == Decimal("10000")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_backtest_engine.py -v
```
预期：`ModuleNotFoundError`

- [ ] **Step 3: 实现 `app/backtest/engine.py`**

```python
"""回测核心逻辑。"""
from decimal import Decimal, ROUND_HALF_UP


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def backtest(klines: list[dict], capital: Decimal,
             upper_price: Decimal, lower_price: Decimal,
             grid_size: Decimal, quantity_per_grid: Decimal) -> dict:
    """执行网格策略回测。

    Args:
        klines: 按时间排序的K线列表
        capital: 初始资金
        upper_price: 网格上限
        lower_price: 网格下限
        grid_size: 网格间距
        quantity_per_grid: 单次购买数量

    Returns:
        dict: {total_return_pct, max_drawdown_pct, win_rate_pct, total_trades, final_capital, trades, equity_curve}
    """
    if not klines:
        return {
            "total_return_pct": Decimal("0"),
            "max_drawdown_pct": Decimal("0"),
            "win_rate_pct": Decimal("0"),
            "total_trades": 0,
            "final_capital": capital,
            "trades": [],
            "equity_curve": [{"timestamp": 0, "capital": capital}],
        }

    # 初始化
    balance = capital
    holdings = Decimal("0")
    trades = []
    equity_curve = [{"timestamp": klines[0]["timestamp"], "capital": capital}]

    # 计算网格价格列表
    grid_prices = []
    price = lower_price
    while price <= upper_price:
        grid_prices.append(_quantize(price))
        price += grid_size

    # 跟踪每个网格持仓状态: {price: {"bought": bool, "sold": bool}}
    grid_state = {p: {"has_position": False} for p in grid_prices}

    for kline in klines:
        low = Decimal(kline["low"])
        high = Decimal(kline["high"])

        for gp in grid_prices:
            # 检查价格是否触达此网格
            if low <= gp <= high:
                if not grid_state[gp]["has_position"]:
                    # 买入
                    cost = gp * quantity_per_grid
                    if balance >= cost:
                        balance -= cost
                        holdings += quantity_per_grid
                        grid_state[gp]["has_position"] = True
                        trades.append({
                            "timestamp": kline["timestamp"],
                            "direction": "buy",
                            "price": gp,
                            "quantity": quantity_per_grid,
                            "profit": Decimal("0"),
                        })
                else:
                    # 卖出
                    revenue = gp * quantity_per_grid
                    balance += revenue
                    holdings -= quantity_per_grid
                    profit = grid_size * quantity_per_grid
                    grid_state[gp]["has_position"] = False
                    trades.append({
                        "timestamp": kline["timestamp"],
                        "direction": "sell",
                        "price": gp,
                        "quantity": quantity_per_grid,
                        "profit": profit,
                    })

        # 记录资金曲线
        current_value = balance + holdings * Decimal(kline["close"])
        equity_curve.append({"timestamp": kline["timestamp"], "capital": _quantize(current_value)})

    final_capital = balance + holdings * Decimal(klines[-1]["close"])
    final_capital = _quantize(final_capital)

    # 统计指标
    total_return_pct = _quantize((final_capital - capital) / capital * Decimal("100"))
    max_drawdown_pct = _calc_max_drawdown(equity_curve)
    win_rate_pct = _calc_win_rate(trades)

    return {
        "total_return_pct": total_return_pct,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate_pct": win_rate_pct,
        "total_trades": len(trades),
        "final_capital": final_capital,
        "trades": trades,
        "equity_curve": equity_curve,
    }


def _calc_max_drawdown(equity_curve: list[dict]) -> Decimal:
    """计算最大回撤。"""
    peak = Decimal("0")
    max_dd = Decimal("0")
    for point in equity_curve:
        value = point["capital"]
        if value > peak:
            peak = value
        if peak > 0:
            dd = (peak - value) / peak * Decimal("100")
            if dd > max_dd:
                max_dd = dd
    return _quantize(max_dd)


def _calc_win_rate(trades: list[dict]) -> Decimal:
    """计算胜率 = 盈利卖出 / 总卖出次数。"""
    sell_trades = [t for t in trades if t["direction"] == "sell"]
    if not sell_trades:
        return Decimal("0")
    wins = sum(1 for t in sell_trades if t["profit"] > 0)
    return _quantize(Decimal(wins) / Decimal(len(sell_trades)) * Decimal("100"))


def generate_equity_curve(klines: list[dict], capital: Decimal,
                          upper_price: Decimal, lower_price: Decimal,
                          grid_size: Decimal, quantity_per_grid: Decimal) -> list[dict]:
    """生成独立资金曲线（用于前端绘图）。"""
    result = backtest(klines, capital, upper_price, lower_price, grid_size, quantity_per_grid)
    return result["equity_curve"]
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_backtest_engine.py -v
```
预期：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/backtest/engine.py tests/test_test_backtest_engine.py
git commit -m "feat(backtest): add grid strategy backtest engine"
```

---

## Task 5: 回测路由

**Files:**
- Create: `app/backtest/routes.py`
- Create: `tests/test_backtest_routes.py`
- Modify: `app/__init__.py`

- [ ] **Step 1: 写失败测试**

`tests/test_backtest_routes.py`:
```python
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestBacktestRoutes:
    def test_get_backtest_page(self, client):
        response = client.get("/backtest")
        assert response.status_code == 200

    def test_post_valid_params(self, client):
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
        # 应返回表单页（含错误）

    def test_post_invalid_time_range(self, client):
        response = client.post("/backtest", data={
            "symbol": "BTCUSDT", "interval": "1h",
            "capital": "10000", "upper_price": "66000",
            "lower_price": "64000", "grid_size": "500",
            "quantity_per_grid": "0.01",
            "start_time": "2024-03-01", "end_time": "2024-01-01",
        })
        assert response.status_code == 200
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_backtest_routes.py -v
```
预期：`404 Not Found`

- [ ] **Step 3: 实现 `app/backtest/routes.py`**

```python
"""回测路由。"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from flask import render_template, request

from app.backtest import backtest_bp
from app.backtest.data_fetcher import get_stored_klines, get_stored_count
from app.backtest.engine import backtest
from app.config_loader import get_symbols


def _parse_and_validate(form: dict):
    """解析并校验回测表单参数。"""
    errors = []
    required_fields = [
        "symbol", "interval", "capital", "upper_price", "lower_price",
        "grid_size", "quantity_per_grid", "start_time", "end_time",
    ]
    for field in required_fields:
        if not form.get(field, "").strip():
            errors.append(f"字段 {field} 为必填项")
    if errors:
        return {}, errors

    try:
        params = {
            "symbol": form["symbol"],
            "interval": form["interval"],
            "capital": Decimal(form["capital"]),
            "upper_price": Decimal(form["upper_price"]),
            "lower_price": Decimal(form["lower_price"]),
            "grid_size": Decimal(form["grid_size"]),
            "quantity_per_grid": Decimal(form["quantity_per_grid"]),
            "start_time": form["start_time"],
            "end_time": form["end_time"],
        }
    except (InvalidOperation, ValueError):
        return {}, ["请输入有效的数值"]

    if params["upper_price"] <= params["lower_price"]:
        errors.append("网格上限必须大于下限")
    if params["start_time"] >= params["end_time"]:
        errors.append("开始时间必须早于结束时间")
    if params["grid_size"] <= Decimal("0"):
        errors.append("网格大小必须为正数")
    if params["quantity_per_grid"] <= Decimal("0"):
        errors.append("单次购买数量必须为正数")
    if params["capital"] <= Decimal("0"):
        errors.append("初始资金必须为正数")

    return params, errors


def _date_to_ms(date_str: str) -> int:
    """'YYYY-MM-DD' 转为毫秒时间戳。"""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@backtest_bp.route("/backtest", methods=["GET", "POST"])
def backtest_index():
    symbols = get_symbols()
    if request.method == "POST":
        params, errors = _parse_and_validate(request.form)
        if errors:
            return render_template("backtest/index.html", errors=errors, form=request.form, symbols=symbols)

        start_ts = _date_to_ms(params["start_time"])
        end_ts = _date_to_ms(params["end_time"])

        # 从数据库获取K线
        klines = get_stored_klines(params["symbol"], params["interval"], start_ts, end_ts)
        if not klines:
            errors = [f"数据库中没有 {params['symbol']} {params['interval']} 的数据，请先用 CLI 拉取。"]
            return render_template("backtest/index.html", errors=errors, form=request.form, symbols=symbols)

        # 执行回测
        result = backtest(
            klines=klines,
            capital=params["capital"],
            upper_price=params["upper_price"],
            lower_price=params["lower_price"],
            grid_size=params["grid_size"],
            quantity_per_grid=params["quantity_per_grid"],
        )
        return render_template("backtest/result.html", result=result, params=params, symbols=symbols)

    return render_template("backtest/index.html", errors=None, form=None, symbols=symbols)
```

- [ ] **Step 4: 更新 `app/__init__.py` 注册 backtest Blueprint**

```python
"""Flask 应用工厂。"""
import os
from flask import Flask


def create_app() -> Flask:
    """创建并返回 Flask 应用实例。"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, "templates")

    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

    from app.routes import main_bp
    app.register_blueprint(main_bp)

    from app.backtest import backtest_bp
    app.register_blueprint(backtest_bp)

    return app
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_backtest_routes.py -v
```
预期：全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/backtest/routes.py app/__init__.py tests/test_backtest_routes.py
git commit -m "feat(backtest): add backtest routes and register blueprint"
```

---

## Task 6: 回测前端模板

**Files:**
- Create: `app/templates/backtest/index.html`
- Create: `app/templates/backtest/result.html`
- Modify: `app/templates/base.html`

- [ ] **Step 1: 创建 `app/templates/backtest/index.html`**

```html
{% extends "base.html" %}
{% block title %}回测 — 网格交易测算{% endblock %}
{% block content %}
<form method="POST" action="/backtest" class="glass">
    {% if errors %}
    <div class="errors">
        <ul>{% for error in errors %}<li>{{ error }}</li>{% endfor %}</ul>
    </div>
    {% endif %}

    <div class="form-row" style="margin-bottom: 20px;">
        <div class="form-group" style="margin-bottom:0">
            <label>币种</label>
            <select name="symbol" id="symbol" required>
                {% for s in symbols %}
                <option value="{{ s.symbol }}"
                    {% if form and form.symbol == s.symbol %}selected{% endif %}>
                    {{ s.symbol }} ({{ s.name }})
                </option>
                {% endfor %}
            </select>
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>K线周期</label>
            <select name="interval" id="interval" required>
                {% for iv in ["1m", "5m", "15m", "1h", "4h"] %}
                <option value="{{ iv }}" {% if form and form.interval == iv %}selected{% endif %}>{{ iv }}</option>
                {% endfor %}
            </select>
        </div>
    </div>

    <div class="form-row" style="margin-bottom: 20px;">
        <div class="form-group" style="margin-bottom:0">
            <label>初始资金 (USDT)</label>
            <input type="number" step="0.01" name="capital" id="capital" min="0" required
                   value="{{ form.capital if form else '10000' }}">
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>单次购买数量 (币)</label>
            <input type="number" step="any" name="quantity_per_grid" id="quantity_per_grid" min="0" required
                   value="{{ form.quantity_per_grid if form else '0.01' }}">
        </div>
    </div>

    <div class="form-row" style="margin-bottom: 20px;">
        <div class="form-group" style="margin-bottom:0">
            <label>网格下限 (USDT)</label>
            <input type="number" step="0.01" name="lower_price" id="lower_price" required
                   value="{{ form.lower_price if form else '' }}">
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>网格上限 (USDT)</label>
            <input type="number" step="0.01" name="upper_price" id="upper_price" required
                   value="{{ form.upper_price if form else '' }}">
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>网格间距 (USDT)</label>
            <input type="number" step="0.01" name="grid_size" id="grid_size" required
                   value="{{ form.grid_size if form else '' }}">
        </div>
    </div>

    <div class="form-row" style="margin-bottom: 20px;">
        <div class="form-group" style="margin-bottom:0">
            <label>开始时间</label>
            <input type="date" name="start_time" id="start_time" required
                   value="{{ form.start_time if form else '' }}">
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>结束时间</label>
            <input type="date" name="end_time" id="end_time" required
                   value="{{ form.end_time if form else '' }}">
        </div>
        <div class="form-group" style="margin-bottom:0">
            <label>强制刷新</label>
            <select name="force_refresh">
                <option value="false" {% if not form or form.force_refresh != 'true' %}selected{% endif %}>否（使用缓存）</option>
                <option value="true" {% if form and form.force_refresh == 'true' %}selected{% endif %}>是（重新拉取）</option>
            </select>
        </div>
    </div>

    <button type="submit" class="btn-glow">▶ 开始回测</button>
    <p style="margin-top: 12px; font-size: 12px; color: var(--dim);">
        💡 提示：首次回测前请先运行 CLI 拉取数据 — <code>python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01</code>
    </p>
</form>
{% endblock %}
```

- [ ] **Step 2: 创建 `app/templates/backtest/result.html`**

```html
{% extends "base.html" %}
{% block title %}回测结果 — 网格交易测算{% endblock %}
{% block content %}
<div class="glass">
    <div class="result-header">
        <div class="result-title">{{ params.symbol }} 回测结果</div>
        <div class="mode-tag">{{ params.interval }} · {{ params.start_time }} ~ {{ params.end_time }}</div>
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="v {{ 'green' if result.total_return_pct >= 0 else 'red' }}">{{ result.total_return_pct }}%</div>
            <div class="l">总收益率</div>
        </div>
        <div class="metric">
            <div class="v red">{{ result.max_drawdown_pct }}%</div>
            <div class="l">最大回撤</div>
        </div>
        <div class="metric">
            <div class="v purple">{{ result.win_rate_pct }}%</div>
            <div class="l">胜率</div>
        </div>
        <div class="metric">
            <div class="v green">{{ result.total_trades }}</div>
            <div class="l">交易次数</div>
        </div>
    </div>

    <div class="metrics" style="margin-top: 12px;">
        <div class="metric">
            <div class="v">{{ result.final_capital }} USDT</div>
            <div class="l">最终资金</div>
        </div>
        <div class="metric">
            <div class="v">{{ params.capital }} USDT</div>
            <div class="l">初始资金</div>
        </div>
    </div>

    {% if result.equity_curve|length > 1 %}
    <h3 style="margin: 24px 0 12px; font-size: 14px; color: var(--dim);">收益曲线</h3>
    <svg width="100%" height="200" viewBox="0 0 600 200" preserveAspectRatio="none" style="background: rgba(255,255,255,0.02); border-radius: 8px;">
        <polyline
            points="{% for p in result.equity_curve %}{{ loop.index0 * (600 / (result.equity_curve|length - 1)) }},{{ 200 - (p.capital - result.equity_curve|map(attribute='capital')|min) / (result.equity_curve|map(attribute='capital')|max - result.equity_curve|map(attribute='capital')|min + 0.01) * 180 + 10 }}{% if not loop.last %} {% endif %}{% endfor %}"
            fill="none" stroke="url(#grad)" stroke-width="2"/>
        <defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#a855f7"/>
                <stop offset="100%" style="stop-color:#22d3ee"/>
            </linearGradient>
        </defs>
    </svg>
    {% endif %}

    {% if result.trades %}
    <h3 style="margin: 24px 0 12px; font-size: 14px; color: var(--dim);">交易明细</h3>
    <div class="details">
        <div class="detail-row" style="font-weight: 600; color: var(--dim);">
            <span class="label">时间</span>
            <span class="label">方向</span>
            <span class="label">价格</span>
            <span class="label">数量</span>
            <span class="label">利润</span>
        </div>
        {% for t in result.trades[:50] %}
        <div class="detail-row">
            <span class="label">{{ t.timestamp }}</span>
            <span class="value {{ 'green' if t.direction == 'sell' else 'red' }}">{{ t.direction }}</span>
            <span class="value">{{ t.price }}</span>
            <span class="value">{{ t.quantity }}</span>
            <span class="value {{ 'green' if t.profit > 0 else '' }}">{{ t.profit }}</span>
        </div>
        {% endfor %}
        {% if result.trades|length > 50 %}
        <p style="font-size: 12px; color: var(--dim); margin-top: 8px;">仅显示前 50 笔，共 {{ result.trades|length }} 笔</p>
        {% endif %}
    </div>
    {% endif %}

    <a href="/backtest" class="back-btn">← 重新回测</a>
</div>
{% endblock %}
```

- [ ] **Step 3: 更新 `base.html` 添加导航**

在 `<div class="brand">` 后追加导航：

```html
<nav class="nav">
    <a href="/" class="nav-link">网格测算</a>
    <a href="/backtest" class="nav-link">回测</a>
</nav>
```

并在 `style.css` 追加：

```css
.nav { display: flex; gap: 8px; margin-left: auto; }
.nav-link {
    color: var(--dim); text-decoration: none; padding: 6px 14px;
    border-radius: 6px; border: 1px solid var(--border);
    font-size: 13px; transition: all 0.2s;
}
.nav-link:hover { color: var(--purple); border-color: var(--purple); }
```

- [ ] **Step 4: 提交**

```bash
git add app/templates/backtest/ app/templates/base.html app/static/style.css
git commit -m "feat(backtest): add backtest UI templates with equity curve"
```

---

## Task 7: 集成验证

**Files:**
- 无新文件，验证已有功能

- [ ] **Step 1: 运行全部测试**

```bash
pytest tests/ -v
```
预期：全部 PASS（含新增的 backtest 测试）

- [ ] **Step 2: 启动 Flask 验证路由**

```bash
python -m flask --app app run --host=0.0.0.0
```

验证：
- `GET /backtest` → 200, 表单页渲染正常
- `POST /backtest` 缺参数 → 返回错误提示
- `POST /backtest` 完整参数但无数据 → 提示"请先拉取数据"

- [ ] **Step 3: CLI 验证（需要网络）**

```bash
python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-01-07
```

预期：分页获取数据，存入 `data/klines.db`

- [ ] **Step 4: 端到端验证**

```bash
# 1. 拉取数据
python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01

# 2. 启动 Flask
python -m flask --app app run --host=0.0.0.0

# 3. 浏览器打开 http://localhost:5000/backtest
# 4. 填写参数提交，查看回测结果
```

- [ ] **Step 5: 最终提交**

```bash
git add -A
git commit -m "feat(backtest): complete backtest feature with CLI + Web + engine"
```

---

## Spec Coverage

| Spec 需求 | 对应 Task |
|-----------|-----------|
| CLI 数据拉取工具 | Task 3 |
| 币安 API 获取 | Task 2 |
| 多K线周期 (1m/5m/15m/1h/4h) | Task 2 |
| 自定义时间范围 | Task 3, Task 5 |
| 数据库缓存 + 幂等 | Task 1, Task 2 |
| 数据格式标准化 | Task 2 |
| 配置集中管理 | Task 2 |
| 网格策略回测模拟 | Task 4 |
| 回测统计指标 | Task 4 |
| 资金与持仓管理 | Task 4 |
| 精度保证 | Task 4 |
| 回测参数表单 | Task 5, Task 6 |
| 回测结果展示 | Task 6 |
| 导航集成 | Task 6 |
