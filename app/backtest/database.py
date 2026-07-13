"""SQLite 数据库操作。"""
import sqlite3
import configparser
import os

# 复用现有 config.ini 读取模式（与 config_loader.py 一致）
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.ini")
_config_parser = configparser.ConfigParser()
_config_parser.read(_CONFIG_PATH, encoding="utf-8")


def _read_config(section: str, key: str, default: str | None = None) -> str | None:
    """从 config.ini 读取配置值。"""
    try:
        return _config_parser.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default


def get_db_path() -> str:
    """获取数据库路径（默认 data/klines.db）。"""
    return _read_config("database", "path", "data/klines.db")


def init_db(db_path: str | None = None) -> None:
    """初始化数据库,创建 klines 表（如果不存在）。"""
    if db_path is None:
        db_path = get_db_path()
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
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


def _get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """获取数据库连接。"""
    if db_path is None:
        db_path = get_db_path()
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def upsert_klines(db_path: str | None, klines: list[dict]) -> int:
    """批量插入/替换K线数据。返回写入条数。"""
    if not klines:
        return 0
    if db_path is None:
        db_path = get_db_path()
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO klines
            (symbol, interval, timestamp, open, high, low, close, volume)
            VALUES (:symbol, :interval, :timestamp, :open, :high, :low, :close, :volume)
        """, klines)
    return len(klines)


def query_klines(db_path: str | None, symbol: str, interval: str,
                 start_ts: int, end_ts: int) -> list[dict]:
    """查询指定范围的K线数据,按时间升序。"""
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT symbol, interval, timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
    """, (symbol, interval, start_ts, end_ts))
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def query_klines_paginated(db_path: str | None, symbol: str, interval: str,
                           start_ts: int, end_ts: int,
                           offset: int, limit: int) -> list[dict]:
    """按页查询 K 线（真分页，避免全量加载）。"""
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT symbol, interval, timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
        LIMIT ? OFFSET ?
    """, (symbol, interval, start_ts, end_ts, limit, offset))
    result = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return result


def count_klines_in_range(db_path: str | None, symbol: str, interval: str,
                          start_ts: int, end_ts: int) -> int:
    """统计指定 symbol+interval+时间范围内的 K 线数量。"""
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT COUNT(*) FROM klines
        WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
    """, (symbol, interval, start_ts, end_ts))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def count_klines(db_path: str | None, symbol: str, interval: str) -> int:
    """统计指定交易对+周期的K线总数。"""
    conn = _get_connection(db_path)
    cursor = conn.execute(
        "SELECT COUNT(*) FROM klines WHERE symbol = ? AND interval = ?",
        (symbol, interval)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def list_all_symbols(db_path: str | None = None) -> list[str]:
    """列出数据库中所有 symbol（去重排序）。"""
    conn = _get_connection(db_path)
    cursor = conn.execute("SELECT DISTINCT symbol FROM klines ORDER BY symbol")
    result = [row[0] for row in cursor.fetchall()]
    conn.close()
    return result


def list_symbol_intervals(db_path: str | None, symbol: str) -> list[dict]:
    """列出某交易对拥有的 interval 及其统计。

    Returns:
        [{interval, count, min_ts, max_ts}, ...] 按 interval 排序
    """
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT interval, COUNT(*) as cnt, MIN(timestamp) as min_ts, MAX(timestamp) as max_ts
        FROM klines
        WHERE symbol = ?
        GROUP BY interval
        ORDER BY interval
    """, (symbol,))
    result = [{"interval": row[0], "count": row[1], "min_ts": row[2], "max_ts": row[3]}
              for row in cursor.fetchall()]
    conn.close()
    return result


def get_interval_range(db_path: str | None, symbol: str, interval: str) -> dict | None:
    """返回指定 symbol+interval 的时间范围。

    Returns:
        {min_ts, max_ts, count} 或 None（无数据）
    """
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM klines
        WHERE symbol = ? AND interval = ?
    """, (symbol, interval))
    row = cursor.fetchone()
    conn.close()
    if row is None or row[2] == 0:
        return None
    return {"min_ts": row[0], "max_ts": row[1], "count": row[2]}


def get_interval_summary(db_path: str | None, symbol: str, interval: str,
                        start_ts: int, end_ts: int) -> dict | None:
    """返回指定范围内的 OHLCV 汇总统计（单次扫描）。

    Returns:
        {open_first, close_last, high_max, low_min, count} 或 None
    """
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        WITH filtered AS (
            SELECT open, close, high, low, timestamp
            FROM klines
            WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
        )
        SELECT
            (SELECT open FROM filtered ORDER BY timestamp ASC LIMIT 1) as open_first,
            (SELECT close FROM filtered ORDER BY timestamp DESC LIMIT 1) as close_last,
            MAX(CAST(high AS REAL)) as high_max,
            MIN(CAST(low AS REAL)) as low_min,
            COUNT(*) as cnt
        FROM filtered
    """, (symbol, interval, start_ts, end_ts))
    row = cursor.fetchone()
    conn.close()
    if row is None or row[4] == 0:
        return None
    return {
        "open_first": row[0],
        "close_last": row[1],
        "high_max": str(row[2]),
        "low_min": str(row[3]),
        "count": row[4],
    }
