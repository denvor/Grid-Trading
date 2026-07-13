"""Flask 应用工厂。"""
import os
from flask import Flask


def create_app() -> Flask:
    """创建并返回 Flask 应用实例。"""
    base_dir = os.path.abspath(os.path.dirname(__file__))
    template_dir = os.path.join(base_dir, "templates")

    flask_app = Flask(__name__, template_folder=template_dir)
    flask_app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32).hex()

    # 注册 blueprint（from ... import bp 即触发路由装饰器绑定）
    from app.routes import main_bp
    flask_app.register_blueprint(main_bp)

    from app.backtest import backtest_bp
    flask_app.register_blueprint(backtest_bp)

    def _ms_to_date(ms: int) -> str:
        from datetime import datetime, timezone
        if not ms:
            return ""
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    flask_app.jinja_env.filters["ms_to_date"] = _ms_to_date

    def _price2(value) -> str:
        """价格格式化为 2 位小数。"""
        try:
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return str(value)

    flask_app.jinja_env.filters["price2"] = _price2

    # 跨域：仅允许本机 / 私有网络（开发预览 + 局域网设备），生产应缩紧
    from urllib.parse import urlparse
    _CORS_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "192.168.199.171"}

    def _is_allowed_origin(origin: str) -> bool:
        """白名单校验 origin 的 host（非前缀匹配，防 DNS rebinding 绕过）。"""
        try:
            parsed = urlparse(origin)
            return parsed.hostname in _CORS_ALLOWED_HOSTS
        except (ValueError, AttributeError):
            return False

    @flask_app.after_request
    def _add_cors(response):
        from flask import request
        origin = request.headers.get("Origin", "")
        if _is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    return flask_app
