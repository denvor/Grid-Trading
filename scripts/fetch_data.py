#!/usr/bin/env python3
"""独立 CLI 工具：从币安获取历史K线数据并存入数据库。

用法:
    python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-03-01
    python fetch_data.py --symbol ETHUSDT --interval 15m --start 2024-06-01 --force
"""
import argparse
import os
import shutil
import sys
import time
from datetime import datetime, timezone

# 把项目根目录加入 path，让 `import app` 在直接运行脚本时可用
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backtest.data_fetcher import (
    fetch_klines_paginated,
    estimate_total_klines,
    SUPPORTED_INTERVALS,
)
from app.backtest.routes import _date_to_ms


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="从币安获取历史K线数据")
    parser.add_argument("--symbol", required=True, help="交易对，如 BTCUSDT")
    parser.add_argument("--interval", required=True,
                        choices=list(SUPPORTED_INTERVALS),
                        help="K线周期")
    parser.add_argument("--start", required=True, help="开始日期, 如 2024-01-01")
    parser.add_argument("--end", required=False, help="结束日期, 默认今天")
    parser.add_argument("--force", action="store_true", help="强制刷新（忽略缓存）")
    return parser.parse_args(argv)


def _progress_callback(fetched: int, estimated_total: int,
                       page: int, total_pages: int,
                       eta: float, last_ts: int,
                       skipped: bool = False):
    """渲染 ASCII 进度条：百分比 / 已获取数 / 当前 K 线时间 / ETA。跳页时单独一行。"""
    if skipped:
        print(f"  ✓ 跳过第 {page}/{total_pages} 页（已在库）")
        return

    # 进度条宽度自适应终端（最小 40 列）
    term_w = max(40, shutil.get_terminal_size().columns)
    bar_max = max(10, term_w - 60)  # 给右侧文字留 60 列
    pct = fetched / max(estimated_total, 1)
    filled = int(bar_max * pct)
    bar = "#" * filled + "." * (bar_max - filled)

    # 当前 K 线时间
    ts_str = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    # ETA 格式化
    eta_str = f"{eta:.0f}s" if eta < 60 else f"{eta / 60:.1f}m"

    print(f"  [{bar}] {pct:4.0%}  {fetched}/{estimated_total}  (当前 {ts_str})  ETA {eta_str}")


def main():
    """CLI 主函数。"""
    args = parse_args()

    # 币安 symbol 全部大写，自动归一化（btcusdt → BTCUSDT）
    args.symbol = args.symbol.upper().strip()

    try:
        start_ts = _date_to_ms(args.start)
        if args.end:
            end_ts = _date_to_ms(args.end)
        else:
            end_ts = int(time.time() * 1000)
    except ValueError:
        print("错误：日期格式无效，请使用 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    if end_ts <= start_ts:
        print("错误：结束时间必须晚于开始时间", file=sys.stderr)
        sys.exit(1)

    estimated = estimate_total_klines(args.symbol, args.interval, start_ts, end_ts)
    print(f"开始获取 {args.symbol} {args.interval} 从 {args.start} 到 {args.end or '今天'}...")
    print(f"[预计 {estimated} 根]")

    total_fetched, total_stored, total_skipped = fetch_klines_paginated(
        symbol=args.symbol,
        interval=args.interval,
        start_ts=start_ts,
        end_ts=end_ts,
        force_refresh=args.force,
        progress_callback=_progress_callback,
    )

    # 完成摘要（实际 vs 预估对照）
    skip_str = f"（跳过 {total_skipped} 页已有数据）" if total_skipped > 0 else ""
    print(f"完成！获取 {total_fetched} 根K线（预估 {estimated}），"
          f"存入数据库 {total_stored} 条{skip_str}。")


if __name__ == "__main__":
    main()
