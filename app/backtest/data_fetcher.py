"""币安 API 数据获取 + DB 读写（CLI + Web 共用）。"""
import json
import math
import sys
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from app.backtest.database import (
    init_db, get_db_path, upsert_klines, query_klines, count_klines, _read_config,
)

API_BASE = "https://api.binance.com/api/v3/klines"
SUPPORTED_INTERVALS = {"1m", "5m", "15m", "1h", "4h"}
MAX_LIMIT = 1000

# 网络类错误（连接超时、SSL 握手超时、连接被重置等）的重试配置
_MAX_API_RETRIES = 3
_RETRY_BACKOFF_S = [1, 2, 4]  # 指数退避秒数

# 线程本地存储：每个线程维护独立 opener，避免全局 install_opener 的并发副作用
_thread_local = threading.local()


def _get_proxy() -> str | None:
    """从 config.ini 读取代理地址。"""
    proxy = _read_config("api", "proxy", None)
    return proxy if proxy else None


def _get_request_interval() -> float:
    """从 config.ini 读取请求间隔秒数。"""
    return float(_read_config("api", "request_interval", "1.0"))


def _get_thread_opener() -> urllib.request.OpenerDirector:
    """获取当前线程的 URL opener（带代理，线程安全）。"""
    opener = getattr(_thread_local, "opener", None)
    if opener is None:
        proxy = _get_proxy()
        if proxy:
            handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            opener = urllib.request.build_opener(handler)
        else:
            opener = urllib.request.build_opener()
        _thread_local.opener = opener
    return opener


def fetch_klines_from_api(symbol: str, interval: str,
                          start_ts: int, end_ts: int) -> list[dict]:
    """从币安 API 获取单页K线数据。"""
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"不支持的周期: {interval}，支持: {SUPPORTED_INTERVALS}")

    url = (f"{API_BASE}?symbol={symbol}&interval={interval}"
           f"&startTime={start_ts}&endTime={end_ts}&limit={MAX_LIMIT}")

    # 使用线程本地 opener（非全局 install_opener），线程安全
    opener = _get_thread_opener()

    try:
        with opener.open(url, timeout=15) as response:
            raw = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        # HTTP 400 通常是 symbol 不存在 / 大小写错误 / 参数不合法
        hint = ""
        if e.code == 400:
            hint = f"（symbol 应为全大写，如 BTCUSDT，当前 {symbol!r}）"
        raise ConnectionError(f"API 请求失败: HTTP {e.code} {hint}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise ConnectionError(f"API 请求失败: {e}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"API 返回数据解析失败: {e}") from e

    return [{
        "symbol": symbol,
        "interval": interval,
        "timestamp": item[0],
        "open": item[1],
        "high": item[2],
        "low": item[3],
        "close": item[4],
        "volume": item[5],
    } for item in raw]


def _interval_to_seconds(interval: str) -> int:
    """周期转秒数。"""
    return {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}[interval]


def estimate_total_klines(symbol: str, interval: str,
                          start_ts: int, end_ts: int) -> int:
    """预判给定参数下预计拉取的 K 线总数（上限）。"""
    interval_seconds = _interval_to_seconds(interval)
    return max(1, (end_ts - start_ts) // (interval_seconds * 1000) + 1)


def _default_progress_callback(fetched: int, estimated_total: int,
                               page: int, total_pages: int,
                               eta: float, last_ts: int,
                               skipped: bool = False) -> None:
    """默认进度回调：打印 ASCII 进度条（供测试与直接调用参考）。"""
    if skipped:
        print(f"  ✓ 跳过第 {page}/{total_pages} 页（已在库）")
        return
    pct = fetched / max(estimated_total, 1)
    bar_len = 20
    filled = int(bar_len * pct)
    bar = "#" * filled + "." * (bar_len - filled)
    eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta / 60:.1f}m"
    ts_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    print(f"\r  [{bar}] {pct:4.0%}  {fetched}/{estimated_total}  (当前 {ts_str})  ETA {eta_str}    ",
          end="", flush=True)


def fetch_klines_paginated(symbol: str, interval: str,
                           start_ts: int, end_ts: int,
                           force_refresh: bool = False,
                           progress_callback=None) -> tuple[int, int, int]:
    """分页获取所有K线数据。

    Returns:
        (total_fetched, total_stored, total_skipped) — API 获取条数, 存入条数, 跳过条数

    progress_callback 签名：
        新风格 (7 参数): callback(fetched, estimated_total, page, total_pages, eta, last_ts, skipped=False)
        旧风格 (3 参数): callback(fetched, current_end, total_end) — 自动回退
    """
    if interval not in SUPPORTED_INTERVALS:
        raise ValueError(f"不支持的周期: {interval}，支持: {SUPPORTED_INTERVALS}")

    db_path = get_db_path()
    interval_seconds = _interval_to_seconds(interval)
    page_duration_ms = MAX_LIMIT * interval_seconds * 1000
    request_interval = _get_request_interval()
    total_fetched = 0
    total_stored = 0
    total_skipped = 0

    estimated_total = estimate_total_klines(symbol, interval, start_ts, end_ts)
    total_pages = max(1, math.ceil((end_ts - start_ts) / page_duration_ms))
    t0 = time.perf_counter()
    last_ts = start_ts  # 已拉取到的最新一根 K 线的毫秒时间戳

    def _notify(page: int, current_end: int, *, skipped: bool = False) -> None:
        """统一进度通知，自动适配新旧回调签名。"""
        if not progress_callback:
            return
        elapsed = time.perf_counter() - t0
        eta = (elapsed / max(total_fetched, 1)) * max(estimated_total - total_fetched, 0)
        try:
            progress_callback(total_fetched, estimated_total, page, total_pages,
                              eta, last_ts, skipped)
        except TypeError:
            # 旧风格 3 参数回调回退
            progress_callback(total_fetched, current_end, end_ts)

    current_start = start_ts
    page = 0
    while current_start < end_ts:
        page += 1
        current_end = min(current_start + page_duration_ms, end_ts)

        # 检查此页数据是否已存在（按页粒度增量跳过）
        if not force_refresh:
            existing = query_klines(db_path, symbol, interval, current_start, current_end)
            if len(existing) >= MAX_LIMIT or (len(existing) > 0 and len(existing) >= (current_end - current_start) / (interval_seconds * 1000) * 0.95):
                # 此页已有足够数据, 跳过请求
                total_skipped += 1
                last_ts = current_end  # 跳页时用 page 末点作为 last_ts
                current_start = current_end + 1
                _notify(page, current_end, skipped=True)
                continue

        # --- 网络错误指数退避重试（SSL 握手超时 / 连接超时 / 连接重置） ---
        klines = None
        for attempt in range(_MAX_API_RETRIES):
            try:
                klines = fetch_klines_from_api(symbol, interval, current_start, current_end)
                break
            except ConnectionError:
                wait = _RETRY_BACKOFF_S[min(attempt, len(_RETRY_BACKOFF_S) - 1)]
                if attempt == _MAX_API_RETRIES - 1:
                    raise  # 最后一次仍失败 → 抛给外层
                print(f"  ⚠ 第 {attempt + 1}/{_MAX_API_RETRIES} 次网络超时，{wait}s 后重试…",
                      file=sys.stderr, flush=True)
                time.sleep(wait)

        if klines is None:
            raise ConnectionError(
                f"获取 K 线失败（{_MAX_API_RETRIES} 次重试均失败）页 {page} "
                f"时间 {current_start}-{current_end}")
        if not klines:
            break
        total_fetched += len(klines)
        upsert_klines(db_path, klines)
        total_stored += len(klines)
        last_ts = klines[-1]["timestamp"]
        _notify(page, current_end)
        # 确保 current_start 始终前进, 避免无限循环
        next_start = klines[-1]["timestamp"] + 1
        current_start = max(next_start, current_end + 1)
        time.sleep(request_interval)

    return total_fetched, total_stored, total_skipped


def get_stored_klines(symbol: str, interval: str,
                      start_ts: int, end_ts: int) -> list[dict]:
    """从数据库读取K线数据。"""
    db_path = get_db_path()
    init_db(db_path)
    return query_klines(db_path, symbol, interval, start_ts, end_ts)


def get_stored_count(symbol: str, interval: str) -> int:
    """获取数据库中某交易对的K线总数。"""
    db_path = get_db_path()
    init_db(db_path)
    return count_klines(db_path, symbol, interval)
