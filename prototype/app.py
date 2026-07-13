"""Flask 应用入口。"""
import os
from decimal import Decimal, InvalidOperation
from flask import Flask, render_template, request

from calculator import analyze
from config_loader import get_symbols


def create_app() -> Flask:
    """创建并返回 Flask 应用实例。"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, "templates")

    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

    def _parse_and_validate(form: dict):
        """解析并校验表单参数。返回 (params_dict, errors_list)。"""
        errors = []
        required_fields = [
            "symbol", "capital", "leverage", "entry_price",
            "upper_price", "lower_price", "grid_size", "quantity_per_grid",
        ]

        for field in required_fields:
            if not form.get(field, "").strip():
                errors.append(f"字段 {field} 为必填项")

        if errors:
            return {}, errors

        try:
            params = {
                "symbol": form["symbol"],
                "capital": Decimal(form["capital"]),
                "leverage": Decimal(form["leverage"]),
                "entry_price": Decimal(form["entry_price"]),
                "upper_price": Decimal(form["upper_price"]),
                "lower_price": Decimal(form["lower_price"]),
                "grid_size": Decimal(form["grid_size"]),
                "quantity_per_grid": Decimal(form["quantity_per_grid"]),
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

    @app.route("/", methods=["GET", "POST"])
    def index():
        symbols = get_symbols()
        if request.method == "POST":
            params, errors = _parse_and_validate(request.form)
            if errors:
                return render_template(
                    "index.html", errors=errors, form=request.form, symbols=symbols
                )

            result = analyze(
                leverage=params["leverage"],
                entry_price=params["entry_price"],
                upper_price=params["upper_price"],
                lower_price=params["lower_price"],
                grid_size=params["grid_size"],
                quantity_per_grid=params["quantity_per_grid"],
                capital=params["capital"],
            )
            return render_template(
                "result.html", result=result, params=params, symbols=symbols
            )

        # GET 请求：有 querystring 则恢复用户上次输入；否则用首币种的缺省配置填充
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
            }
        elif symbols:
            s = symbols[0]
            entry = float(s["entry_price"])
            upper_pct = float(s["upper_pct"])
            lower_pct = float(s["lower_pct"])
            form = {
                "symbol": s["symbol"],
                "capital": s["capital"],
                "leverage": "1",
                "entry_price": s["entry_price"],
                "upper_price": f"{entry * (1 + upper_pct / 100):.2f}",
                "lower_price": f"{entry * (1 - lower_pct / 100):.2f}",
                "grid_size": s["grid_size"],
                "quantity_per_grid": s["quantity_per_grid"],
            }

        return render_template("index.html", errors=None, form=form, symbols=symbols)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
