#!/usr/bin/env python3
"""独立 CLI 工具：查看数据库现有数据的概况、详情与空洞检测。

用法:
    python check_data.py                                        # 列出所有 symbol/interval 概况
    python check_data.py --symbol BTCUSDT                       # 只看 BTCUSDT
    python check_data.py --symbol BTCUSDT --interval 1h         # 详情 + 空洞检测
    python check_data.py --gap-threshold 2.0                    # 调整空洞判定阈值
    python check_data.py --json                                 # JSON 输出
"""
import argparse
import json
import os
import statistics
import sys
from datetime import datetime, timezone

# 把项目根目录加入 path，让 `import app` 在直接运行脚本时可用
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backtest.database import (
    init_db, get_db_path,
    list_all_symbols, list_symbol_intervals, count_klines,
    query_klines_paginated,
)

# 每次查询的最大行数（大数据集采样）
_GAP_SCAN_LIMIT = 50000
_PAGE_SIZE = 5000


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="查看数据库现有数据")
    parser.add_argument("--symbol", help="过滤交易对，如 BTCUSDT")
    parser.add_argument("--interval", help="过滤周期，如 1h")
    parser.add_argument("--gap-threshold", type=float, default=1.5,
                        help="空洞判定阈值（间隔 > 中位间隔 × 阈值），默认 1.5")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    return parser.parse_args(argv)


def _ms_to_iso(ms: int) -> str:
    """毫秒时间戳 → ISO 格式 YYYY-MM-DD HH:MM。"""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _scan_gaps(db_path, symbol: str, interval: str, start_ts: int, end_ts: int,
               threshold: float) -> dict:
    """流式扫描时间戳间隔，返回中位数、最小/最大间隔、空洞数。"""
    offset = 0
    prev_ts = None
    intervals = []  # 相邻间隔列表（毫秒）
    gap_count = 0
    scanned = 0

    while offset < _GAP_SCAN_LIMIT:
        rows = query_klines_paginated(db_path, symbol, interval, start_ts, end_ts,
                                      offset, _PAGE_SIZE)
        if not rows:
            break
        for row in rows:
            ts = row["timestamp"]
            if prev_ts is not None:
                dt = ts - prev_ts
                intervals.append(dt)
            prev_ts = ts
        scanned += len(rows)
        offset += _PAGE_SIZE
        if len(rows) < _PAGE_SIZE:
            break

    if not intervals:
        return {"median": 0, "min": 0, "max": 0, "gaps": 0, "scanned": scanned}

    median_iv = statistics.median(intervals)
    min_iv = min(intervals)
    max_iv = max(intervals)
    gap_count = sum(1 for iv in intervals if iv > median_iv * threshold)

    return {"median": median_iv, "min": min_iv, "max": max_iv,
            "gaps": gap_count, "scanned": scanned}


def _all_combinations(db_path) -> list[dict]:
    """列出所有 symbol+interval 的概要行。"""
    symbols = list_all_symbols(db_path)
    rows = []
    for sym in symbols:
        for info in list_symbol_intervals(db_path, sym):
            rows.append({
                "symbol": sym,
                "interval": info["interval"],
                "count": info["count"],
                "min_ts": info["min_ts"],
                "max_ts": info["max_ts"],
            })
    return rows


def _filter_rows(all_rows: list[dict], symbol: str | None, interval: str | None) -> list[dict]:
    """按 symbol / interval 过滤概要行。"""
    rows = all_rows
    if symbol:
        rows = [r for r in rows if r["symbol"] == symbol]
    if interval:
        rows = [r for r in rows if r["interval"] == interval]
    return rows


def _format_duration(ms: int) -> str:
    """毫秒时间跨度 → 人类可读字符串。"""
    days = ms / 86_400_000
    if days >= 1:
        return f"{days:.1f} 天"
    hours = ms / 3_600_000
    if hours >= 1:
        return f"{hours:.1f} 小时"
    minutes = ms / 60_000
    return f"{minutes:.0f} 分钟"


def render_text_summary(rows: list[dict]) -> None:
    """打印汇总表。"""
    header = f"{'symbol':<12} {'interval':<8} {'记录数':>8} {'最早':>18} {'最近':>18} {'跨度':>10}"
    print(header)
    print("-" * len(header))
    for r in rows:
        span = _format_duration(r["max_ts"] - r["min_ts"]) if r["max_ts"] and r["min_ts"] else "-"
        print(f"{r['symbol']:<12} {r['interval']:<8} {r['count']:>8} "
              f"{_ms_to_iso(r['min_ts']):>18} {_ms_to_iso(r['max_ts']):>18} {span:>10}")


def render_text_detail(sym: str, interval: str, info: dict, gap: dict) -> None:
    """打印详情。"""
    print(f"{sym} / {interval} 详情:")
    print(f"  记录数:         {info['count']}")
    print(f"  最早时间:       {_ms_to_iso(info['min_ts'])} (ts={info['min_ts']})")
    print(f"  最近时间:       {_ms_to_iso(info['max_ts'])} (ts={info['max_ts']})")
    print(f"  时间跨度:       {_format_duration(info['max_ts'] - info['min_ts'])}")
    print(f"  间隔中位:       {_format_duration(int(gap['median']))}")
    print(f"  间隔最小/最大:  {_format_duration(gap['min'])} / {_format_duration(gap['max'])}")
    print(f"  空洞数:         {gap['gaps']}")
    if gap["scanned"] < info["count"]:
        print(f"  (统计采样 {gap['scanned']}/{info['count']} 条)")


def render_json_output(data: dict) -> None:
    """打印 JSON。"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    """CLI 主函数。"""
    args = parse_args()
    db_path = get_db_path()
    init_db(db_path)

    all_rows = _all_combinations(db_path)

    # 空库
    if not all_rows:
        print("数据库为空，请先使用 fetch_data.py 拉取数据", file=sys.stderr)
        sys.exit(0)

    rows = _filter_rows(all_rows, args.symbol, args.interval)

    # 找不到匹配
    if not rows:
        available = sorted({r["symbol"] for r in all_rows})
        print(f"未找到匹配的数据 (symbol={args.symbol!r}, interval={args.interval!r})。", file=sys.stderr)
        print(f"已缓存交易对: {', '.join(available)}", file=sys.stderr)
        sys.exit(0)

    # 详情模式（唯一 symbol + interval）
    if args.symbol and args.interval and len(rows) == 1:
        info = rows[0]
        gap = _scan_gaps(db_path, args.symbol, args.interval,
                         info["min_ts"], info["max_ts"], args.gap_threshold)
        if args.json:
            render_json_output({
                "symbol": args.symbol,
                "interval": args.interval,
                "count": info["count"],
                "min_ts": info["min_ts"],
                "max_ts": info["max_ts"],
                "median_interval_ms": gap["median"],
                "min_interval_ms": gap["min"],
                "max_interval_ms": gap["max"],
                "gap_count": gap["gaps"],
                "scanned": gap["scanned"],
            })
        else:
            render_text_detail(args.symbol, args.interval, info, gap)
        return

    # 汇总模式
    if args.json:
        render_json_output(rows)
    else:
        render_text_summary(rows)


if __name__ == "__main__":
    main()
