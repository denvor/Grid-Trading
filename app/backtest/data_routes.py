"""数据展示路由。"""
from flask import render_template, request, jsonify

from app.backtest import backtest_bp
from app.backtest.database import (
    list_symbol_intervals, query_klines_paginated, count_klines_in_range,
    get_interval_range, get_interval_summary,
)
from app.backtest.routes import _date_to_ms
from app.config_loader import get_symbols

# 每页 K 线数量（前端/后端共用）
PAGE_SIZE = 50


@backtest_bp.route("/data", methods=["GET", "POST"])
def data_index():
    symbols = get_symbols()
    ctx = {
        "symbols": symbols,
        "selected_symbol": None,
        "selected_interval": None,
        "intervals": [],
        "summary": None,
        "total_count": 0,
        "range_min_ts": None,
        "range_max_ts": None,
    }

    if request.method == "POST":
        symbol = request.form.get("symbol", "")
        interval = request.form.get("interval", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")
        view_data = request.form.get("view_data") == "1"
        ctx["selected_symbol"] = symbol
        ctx["selected_interval"] = interval

        # 选 symbol → 显示可用 interval 列表
        if symbol:
            ctx["intervals"] = list_symbol_intervals(None, symbol)
            # 记录选中 interval 的数据时间范围，用于前端自动填充
            if interval:
                for iv in ctx["intervals"]:
                    if iv["interval"] == interval:
                        ctx["range_min_ts"] = iv["min_ts"]
                        ctx["range_max_ts"] = iv["max_ts"]
                        break

        # 选 interval + 点查看 → 仅查询汇总（明细由前端按页 AJAX 拉取）
        if view_data and symbol and interval:
            range_data = get_interval_range(None, symbol, interval)
            if range_data:
                try:
                    start_ts = _date_to_ms(start_time) if start_time else range_data["min_ts"]
                    end_ts = _date_to_ms(end_time) if end_time else range_data["max_ts"]
                except ValueError:
                    ctx["errors"] = ["日期格式无效，请使用 YYYY-MM-DD"]
                    return render_template("backtest/data.html", **ctx)
                ctx["total_count"] = count_klines_in_range(None, symbol, interval, start_ts, end_ts)
                ctx["summary"] = get_interval_summary(None, symbol, interval, start_ts, end_ts)
                # 把时间范围传给前端，作为分页请求的日期参数
                ctx["range_min_ts"] = start_ts
                ctx["range_max_ts"] = end_ts

    return render_template("backtest/data.html", **ctx)


@backtest_bp.route("/data/klines")
def data_klines():
    """按页返回 K 线明细（AJAX JSON API）。"""
    symbol = request.args.get("symbol", "")
    interval = request.args.get("interval", "")
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    page = request.args.get("page", 1, type=int)
    if not symbol or not interval:
        return jsonify({"error": "缺少 symbol 或 interval"}), 400

    range_data = get_interval_range(None, symbol, interval)
    if not range_data:
        return jsonify({"klines": [], "total": 0, "page": page,
                        "page_size": PAGE_SIZE, "total_pages": 0})

    try:
        start_ts = _date_to_ms(start_time) if start_time else range_data["min_ts"]
        end_ts = _date_to_ms(end_time) if end_time else range_data["max_ts"]
    except ValueError:
        return jsonify({"error": "日期格式无效"}), 400
    total = count_klines_in_range(None, symbol, interval, start_ts, end_ts)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(1, min(page, total_pages))

    offset = (page - 1) * PAGE_SIZE
    page_klines = query_klines_paginated(None, symbol, interval, start_ts, end_ts, offset, PAGE_SIZE)

    return jsonify({
        "klines": page_klines,
        "total": total,
        "page": page,
        "page_size": PAGE_SIZE,
        "total_pages": total_pages,
    })
