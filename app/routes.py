"""Flask 路由：参数表单 + 测算结果。"""
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request

from app.calculator import analyze
from app.config_loader import get_symbols

main_bp = Blueprint("main", __name__)


def _parse_and_validate(form: dict):
    """解析并校验表单参数。返回 (params_dict, errors_list)。"""
    errors = []
    required_fields = [
        "symbol", "capital", "leverage", "entry_price",
        "upper_price", "lower_price", "grid_size", "quantity_per_grid", "margin_mode",
    ]

    for field in required_fields:
        if not form.get(field, "").strip():
            errors.append(f"字段 {field} 为必填项")

    if errors:
        return {}, errors

    try:
        margin_mode = form.get("margin_mode", "cross")
        if margin_mode not in ("cross", "isolated"):
            margin_mode = "cross"
        # 清理千分位逗号，支持 "100,000.00" 格式输入
        def _clean_number(raw: str) -> str:
            return raw.strip().replace(",", "")
        params = {
            "symbol": form["symbol"],
            "capital": Decimal(_clean_number(form["capital"])),
            "leverage": Decimal(_clean_number(form["leverage"])),
            "entry_price": Decimal(_clean_number(form["entry_price"])),
            "upper_price": Decimal(_clean_number(form["upper_price"])),
            "lower_price": Decimal(_clean_number(form["lower_price"])),
            "grid_size": Decimal(_clean_number(form["grid_size"])),
            "quantity_per_grid": Decimal(_clean_number(form["quantity_per_grid"])),
            "margin_mode": margin_mode,
        }
    except (InvalidOperation, ValueError):
        return {}, ["请输入有效的数值"]

    if params["leverage"] < Decimal("1") or params["leverage"] > Decimal("125"):
        errors.append("杠杆必须在 1-125 之间")

    if params["upper_price"] <= params["entry_price"]:
        errors.append("网格上限必须大于入场价")

    if params["lower_price"] >= params["entry_price"]:
        errors.append("网格下限必须小于入场价")

    if params["grid_size"] <= Decimal("0"):
        errors.append("网格大小必须为正数")

    if params["quantity_per_grid"] <= Decimal("0"):
        errors.append("单次购买数量必须为正数")

    if params["capital"] <= Decimal("0"):
        errors.append("初始资金必须为正数")

    return params, errors


@main_bp.route("/", methods=["GET", "POST"])
def index():
    symbols = get_symbols()
    if request.method == "POST":
        params, errors = _parse_and_validate(request.form)
        if errors:
            return render_template("index.html", errors=errors, form=request.form, symbols=symbols)

        result = analyze(
            capital=params["capital"], leverage=params["leverage"],
            entry_price=params["entry_price"], upper_price=params["upper_price"],
            lower_price=params["lower_price"], grid_size=params["grid_size"],
            quantity_per_grid=params["quantity_per_grid"], margin_mode=params["margin_mode"],
        )
        return render_template("result.html", result=result, params=params, symbols=symbols)

    # GET: querystring 恢复用户输入；否则首币种缺省
    form = None
    if request.args.get("symbol"):
        form = {
            "symbol": request.args.get("symbol", ""),
            "capital": request.args.get("capital", ""),
            "leverage": request.args.get("leverage", ""),
            "entry_price": request.args.get("entry_price", ""),
            "upper_price": request.args.get("upper_price", ""),
            "lower_price": request.args.get("lower_price", ""),
            "grid_size": request.args.get("grid_size", ""),
            "quantity_per_grid": request.args.get("quantity_per_grid", ""),
            "margin_mode": request.args.get("margin_mode", "cross"),
        }
    elif symbols:
        s = symbols[0]
        entry = Decimal(s["entry_price"])
        upper_pct = Decimal(s["upper_pct"])
        lower_pct = Decimal(s["lower_pct"])
        form = {
            "symbol": s["symbol"], "capital": s["capital"], "leverage": "1",
            "entry_price": s["entry_price"],
            "upper_price": f"{entry * (1 + upper_pct / 100):.2f}",
            "lower_price": f"{entry * (1 - lower_pct / 100):.2f}",
            "grid_size": s["grid_size"],
            "quantity_per_grid": s["quantity_per_grid"],
            "margin_mode": "cross",
        }

    return render_template("index.html", errors=None, form=form, symbols=symbols)
