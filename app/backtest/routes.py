"""回测路由。"""
import json
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from flask import render_template, request, jsonify, stream_with_context, Response, redirect, url_for, session

from app.backtest import backtest_bp
from app.backtest.database import list_symbol_intervals, get_interval_summary
from app.backtest.data_fetcher import get_stored_klines
from app.backtest.data_fetcher import SUPPORTED_INTERVALS


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
        # 清理千分位逗号（支持 "100,000" 格式输入）
        def _clean_number(raw: str) -> str:
            return raw.strip().replace(",", "")
        params = {
            "symbol": form["symbol"],
            "interval": form["interval"],
            "capital": Decimal(_clean_number(form["capital"])),
            "upper_price": Decimal(_clean_number(form["upper_price"])),
            "lower_price": Decimal(_clean_number(form["lower_price"])),
            "grid_size": Decimal(_clean_number(form["grid_size"])),
            "quantity_per_grid": Decimal(_clean_number(form["quantity_per_grid"])),
            "start_time": form["start_time"],
            "end_time": form["end_time"],
        }
    except (InvalidOperation, ValueError):
        return {}, ["请输入有效的数值"]

    if params["upper_price"] <= params["lower_price"]:
        errors.append("网格上限必须大于下限")
    if params["start_time"] >= params["end_time"]:
        errors.append("开始时间必须早于结束时间")

    # 时间跨度警告（>2 年提示计算可能较慢）
    try:
        _start = datetime.strptime(params["start_time"], "%Y-%m-%d")
        _end = datetime.strptime(params["end_time"], "%Y-%m-%d")
        if (_end - _start).days > 730:
            params["time_span_warning"] = True
    except ValueError:
        pass
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


# 按从短到长顺序排列，避免 set 迭代顺序漂移
ALL_INTERVALS = sorted(SUPPORTED_INTERVALS, key=lambda s: {"m": 1, "h": 60}[s[-1]] * int(s[:-1]))


@backtest_bp.route("/backtest/available_data")
def available_data():
    """返回某交易对可用的 interval 及其时间范围（供前端联动）。"""
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"intervals": {}})

    db_intervals = list_symbol_intervals(None, symbol)
    interval_map = {iv["interval"]: iv for iv in db_intervals}

    result = {}
    for iv in ALL_INTERVALS:
        if iv in interval_map:
            d = interval_map[iv]
            # 查询该 interval 的价格上下限
            price_info = get_interval_summary(None, symbol, iv, d["min_ts"], d["max_ts"])
            result[iv] = {
                "count": d["count"],
                "min_ts": d["min_ts"],
                "max_ts": d["max_ts"],
                "low_price": price_info["low_min"] if price_info else None,
                "high_price": price_info["high_max"] if price_info else None,
            }
        else:
            result[iv] = {"count": 0, "min_ts": None, "max_ts": None,
                         "low_price": None, "high_price": None}
    return jsonify({"intervals": result})


def _parse_stream_query(args: dict):
    """从 GET query string 解析回测参数，返回 (params, errors)。"""
    errors = []
    for key in ["symbol", "interval", "capital", "upper_price", "lower_price",
                "grid_size", "quantity_per_grid", "start_time", "end_time"]:
        if not args.get(key, "").strip():
            errors.append(f"缺少必填参数 {key}")
    if errors:
        return {}, errors

    def _clean_number(raw: str) -> str:
        return raw.strip().replace(",", "")
    try:
        params = {
            "symbol": args["symbol"].upper().strip(),
            "interval": args["interval"],
            "capital": Decimal(_clean_number(args["capital"])),
            "upper_price": Decimal(_clean_number(args["upper_price"])),
            "lower_price": Decimal(_clean_number(args["lower_price"])),
            "grid_size": Decimal(_clean_number(args["grid_size"])),
            "quantity_per_grid": Decimal(_clean_number(args["quantity_per_grid"])),
            "start_time": args["start_time"],
            "end_time": args["end_time"],
        }
    except (InvalidOperation, ValueError):
        return {}, ["请输入有效的数值"]

    if params["upper_price"] <= params["lower_price"]:
        errors.append("网格上限必须大于下限")
    if params["start_time"] >= params["end_time"]:
        errors.append("开始时间必须早于结束时间")
    try:
        _start = datetime.strptime(params["start_time"], "%Y-%m-%d")
        _end = datetime.strptime(params["end_time"], "%Y-%m-%d")
        if (_end - _start).days > 730:
            params["time_span_warning"] = True
    except ValueError:
        pass
    if params["grid_size"] <= Decimal("0"):
        errors.append("网格大小必须为正数")
    if params["quantity_per_grid"] <= Decimal("0"):
        errors.append("单次购买数量必须为正数")
    if params["capital"] <= Decimal("0"):
        errors.append("初始资金必须为正数")

    return params, errors


def _render_backtest_index(errors=None, form=None, symbols=None,
                          time_span_warning=None):
    """渲染回测入口页（错误/空表单共用模板）。"""
    return render_template("backtest/index.html", errors=errors,
                           form=form, symbols=symbols, all_intervals=ALL_INTERVALS,
                           time_span_warning=time_span_warning)


@backtest_bp.route("/backtest", methods=["GET", "POST"])
def backtest_index():
    # 延迟导入避免循环导入
    from app.backtest.data_fetcher import get_stored_klines
    from app.backtest.engine import backtest
    from app.config_loader import get_symbols, get_symbol

    symbols = get_symbols()
    if request.method == "POST":
        params, errors = _parse_and_validate(request.form)
        tw = params.get("time_span_warning")
        if errors:
            return _render_backtest_index(errors=errors, form=request.form,
                                         symbols=symbols, time_span_warning=tw)

        try:
            start_ts = _date_to_ms(params["start_time"])
            end_ts = _date_to_ms(params["end_time"])
        except ValueError:
            return _render_backtest_index(
                errors=["日期格式无效，请使用 YYYY-MM-DD"], form=request.form,
                symbols=symbols, time_span_warning=tw)

        # 从数据库获取K线
        klines = get_stored_klines(params["symbol"], params["interval"], start_ts, end_ts)
        if not klines:
            errors = [f"数据库中没有 {params['symbol']} {params['interval']} 的数据。"
                      f"请先运行 CLI 拉取：python fetch_data.py --symbol {params['symbol']} "
                      f"--interval {params['interval']} --start {params['start_time']} "
                      f"--end {params['end_time']}"]
            return _render_backtest_index(errors=errors, form=request.form,
                                         symbols=symbols, time_span_warning=tw)

        # 执行回测
        result = backtest(
            klines=klines,
            capital=params["capital"],
            upper_price=params["upper_price"],
            lower_price=params["lower_price"],
            grid_size=params["grid_size"],
            quantity_per_grid=params["quantity_per_grid"],
        )
        return render_template("backtest/result.html", result=result,
                               params=params, symbols=symbols,
                               time_span_warning=tw)

    # GET：读取 config.ini 的初始资本 / 购买数量作为表单默认值
    form = None
    if symbols:
        s = symbols[0]
        sym = get_symbol(s["symbol"])
        if sym:
            form = {
                "capital": sym.get("capital", "1000"),
                "quantity_per_grid": sym.get("quantity_per_grid", "0.01"),
            }

    return _render_backtest_index(symbols=symbols, form=form)


# 内存 job store：jobid → {result, params, time_span_warning}
_backtest_jobs = {}


@backtest_bp.route("/backtest/result")
def backtest_result_page():
    """渲染完整回测结果页（从 job store 读取）。"""
    jobid = request.args.get("jobid", "")
    job = _backtest_jobs.get(jobid)
    if not job:
        return redirect(url_for("backtest.backtest_index"))
    # 取出后立即清理（结果已消费）
    _backtest_jobs.pop(jobid, None)
    return render_template("backtest/result.html", result=job["result"],
                           params=job["params"], symbols=_get_symbols(),
                           time_span_warning=job.get("time_span_warning"))


def _get_symbols():
    from app.config_loader import get_symbols
    return get_symbols()


@backtest_bp.route("/backtest/stream")
def stream_backtest():
    """SSE 流式回测进度。GET 参数同 POST /backtest 表单。"""
    import queue
    import threading

    from app.backtest.engine import backtest

    params, errors = _parse_stream_query(request.args.to_dict())
    if errors:
        return jsonify({"error": errors[0]}), 400

    try:
        start_ts = _date_to_ms(params["start_time"])
        end_ts = _date_to_ms(params["end_time"])
    except ValueError:
        return jsonify({"error": "日期格式无效，请使用 YYYY-MM-DD"}), 400

    # 从数据库获取K线
    klines = get_stored_klines(params["symbol"], params["interval"], start_ts, end_ts)
    if not klines:
        return jsonify({"error": f"数据库中没有 {params['symbol']} {params['interval']} 的数据。"
                               f"请先运行 CLI 拉取：python fetch_data.py --symbol {params['symbol']} "
                               f"--interval {params['interval']} --start {params['start_time']} "
                               f"--end {params['end_time']}"}), 400

    # 线程安全队列：后台回测线程推 progress，generator 实时消费
    q = queue.Queue()
    _SENTINEL = object()  # 结束标记

    def _progress_callback(percent, kline_index, total, elapsed_ms, trades_count):
        eta_ms = int((elapsed_ms / max(percent, 1)) * (100 - percent)) if percent > 0 else 0
        q.put({
            "percent": percent,
            "kline_index": kline_index,
            "total_klines": total,
            "elapsed_ms": elapsed_ms,
            "eta_ms": eta_ms,
            "trades_count": trades_count,
        })

    # 预生成 jobid，worker 完成后把结果存入 job store
    jobid = uuid.uuid4().hex

    def _worker():
        """后台线程跑回测，完成后 put sentinel。"""
        try:
            result = backtest(
                klines=klines,
                capital=params["capital"],
                upper_price=params["upper_price"],
                lower_price=params["lower_price"],
                grid_size=params["grid_size"],
                quantity_per_grid=params["quantity_per_grid"],
                progress_callback=_progress_callback,
            )
            _backtest_jobs[jobid] = {
                "result": result,
                "params": params,
                "time_span_warning": params.get("time_span_warning"),
            }
            q.put(("done", jobid))
        except Exception as e:
            q.put(("error", str(e)))
        finally:
            q.put(_SENTINEL)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    def _generate():
        """Generator: 实时消费队列，推 SSE 帧。"""
        yield "retry: 5000\n\n"
        while True:
            item = q.get()
            if item is _SENTINEL:
                break
            if isinstance(item, tuple):
                # done / error 最终事件
                kind, payload = item
                if kind == "done":
                    # payload 是 jobid，result 存在 _backtest_jobs 中
                    data = json.dumps({"jobid": payload})
                    yield f"event: done\ndata: {data}\n\n"
                else:
                    data = json.dumps({"error": payload})
                    yield f"event: error\ndata: {data}\n\n"
                break
            else:
                # progress 事件
                yield f"event: progress\ndata: {json.dumps(item)}\n\n"

    return Response(stream_with_context(_generate()),
                    mimetype="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "X-Accel-Buffering": "no",
                    })
