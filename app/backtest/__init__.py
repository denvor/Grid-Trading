"""回测功能包。"""
from flask import Blueprint

backtest_bp = Blueprint("backtest", __name__, template_folder="templates")

import app.backtest.data_routes  # noqa: F401 — 注册数据展示路由
