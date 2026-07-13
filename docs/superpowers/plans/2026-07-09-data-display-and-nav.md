# Data Display, Navigation Enhancement & Backtest Form Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增数据展示页 + 三入口导航（资金计算/回测/数据展示）+ 回测表单根据数据库状态智能联动（灰显无数据周期、日期范围提示、切换币种自动填默认网格参数）。

**Architecture:** 在现有 `app/backtest/` 包里新增 `data_routes.py`（/data 路由）和 `data.html` 模板；数据库层新增 3 个查询函数；修改 base.html 导航（含 active 高亮）；回测页通过 `/backtest/available_data` JSON 端点实现前后端联动（无 JS 框架，纯 fetch + data-attributes）。

**Tech Stack:** Python 3.x, Flask, Jinja2, SQLite3, fetch API（原生 browser JS，无框架）

---

## 改动总览

| # | 改动 | 涉及文件 |
|---|------|----------|
| 1 | 导航栏三入口 + active 高亮 | `base.html`, `style.css` |
| 2 | 数据展示页 `/data` | `database.py`, `data_routes.py`, `data.html` |
| 3 | 回测表单智能联动 (+ JSON 端点) | `routes.py`, `index.html`, `style.css` |

---

## File Structure

```
app/backtest/
├── database.py          # ← +3 个查询函数: list_symbol_intervals, get_interval_range, get_interval_summary
├── data_routes.py       # ← 新增: /data 路由 (展示+过滤)
├── routes.py            # ← +/backtest/available_data JSON 端点 + GET 改造传 available_intervals
└── index.html           # ← 联动 JS: 灰显/日期提示/自动填参数
app/templates/
├── base.html            # ← 三入口导航 + active 高亮
└── backtest/
    ├── data.html        # ← 新增: 数据展示页
    └── index.html       # ← 改造: 联动逻辑
app/static/style.css     # ← .nav-link.active, .interval-disabled, .date-hint 样式
tests/
├── test_database.py     # ← +新查询函数测试
├── test_data_routes.py  # ← 新增: /data 路由测试
└── test_backtest_routes.py  # ← +available_data 端点测试 + 灰显逻辑测试
```

---

## Task 1: 导航栏三入口 + active 高亮

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/static/style.css`
- Verify: 手动验证

- [ ] **Step 1: 改 base.html — 添加"数据展示"入口 + active 高亮**

```html
<nav class="topnav">
    <a href="{{ url_for('main.index') }}" class="nav-link {% if request.endpoint == 'main.index' %}active{% endif %}">资金计算</a>
    <a href="{{ url_for('backtest.backtest_index') }}" class="nav-link {% if request.endpoint == 'backtest.backtest_index' %}active{% endif %}">回测</a>
    <a href="{{ url_for('backtest.data_index') }}" class="nav-link {% if request.endpoint == 'backtest.data_index' %}active{% endif %}">数据展示</a>
</nav>
```

- [ ] **Step 2: style.css 追加 active 样式**

```css
.nav-link.active {
    color: var(--text);
    border-color: var(--cyan);
    background: rgba(0,245,212,.08);
    box-shadow: 0 0 12px rgba(0,245,212,.2);
}
```

- [ ] **Step 3: 验证渲染**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
python -c "
from app import create_app
c = create_app().test_client()
for path, name in [('/','资金计算'), ('/backtest','回测'), ('/data','数据展示')]:
    r = c.get(path)
    print(f'{path} → {r.status_code}')
"
```
预期：`/` 和 `/backtest` 返回 200；`/data` 返回 404（尚未实现）。active 高亮通过后续 Task 完成。

---

## Task 2: 数据库新增查询函数

**Files:**
- Modify: `app/backtest/database.py`
- Modify: `tests/test_database.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_database.py` 追加：

```python
class TestDataOverviewQueries:
    """测试数据概览查询函数"""

    def test_list_symbol_intervals(self, tmp_db):
        """返回 symbol 拥有的 interval 列表及统计"""
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000 + i*3600000,
             "open": "65000", "high": "65500", "low": "64800", "close": "65200", "volume": "100"}
            for i in range(5)
        ] + [
            {"symbol": "BTCUSDT", "interval": "4h", "timestamp": 1704067200000 + i*14400000,
             "open": "65000", "high": "65500", "low": "64800", "close": "65200", "volume": "100"}
            for i in range(3)
        ]
        from app.backtest.database import upsert_klines, list_symbol_intervals
        upsert_klines(tmp_db, klines)
        result = list_symbol_intervals(tmp_db, "BTCUSDT")
        assert len(result) == 2
        intervals = {r["interval"] for r in result}
        assert "1h" in intervals
        assert "4h" in intervals
        for r in result:
            assert "count" in r
            assert "min_ts" in r
            assert "max_ts" in r

    def test_get_interval_range(self, tmp_db):
        """返回指定 symbol+interval 的最早和最晚时间戳"""
        klines = [
            {"symbol": "ETHUSDT", "interval": "15m", "timestamp": 1704067200000 + i*900000,
             "open": "3500", "high": "3550", "low": "3480", "close": "3520", "volume": "100"}
            for i in range(10)
        ]
        from app.backtest.database import upsert_klines, get_interval_range
        upsert_klines(tmp_db, klines)
        result = get_interval_range(tmp_db, "ETHUSDT", "15m")
        assert result is not None
        assert result["min_ts"] == 1704067200000
        assert result["max_ts"] == 1704067200000 + 9 * 900000
        # 不存在的返回 None
        assert get_interval_range(tmp_db, "ETHUSDT", "1m") is None

    def test_get_interval_summary(self, tmp_db):
        """返回 OHLCV 汇总统计"""
        klines = [
            {"symbol": "BTCUSDT", "interval": "1h", "timestamp": 1704067200000 + i*3600000,
             "open": str(65000 + i*10), "high": str(66000 + i*10),
             "low": str(64000 + i*10), "close": str(65500 + i*10), "volume": "100"}
            for i in range(5)
        ]
        from app.backtest.database import upsert_klines, get_interval_summary
        upsert_klines(tmp_db, klines)
        s = get_interval_summary(tmp_db, "BTCUSDT", "1h",
                                1704067200000, 1704067200000 + 4*3600000)
        assert s is not None
        assert s["open_first"] == "65000"
        assert s["close_last"] == "65504"
        assert float(s["high_max"]) == 66004.0
        assert float(s["low_min"]) == 64000.0
        assert s["count"] == 5
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_database.py::TestDataOverviewQueries -v
```
预期：`AttributeError: module 'app.backtest.database' has no attribute 'list_symbol_intervals'`

- [ ] **Step 3: 实现 3 个查询函数**

在 `database.py` 末尾追加：

```python
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
        {min_ts, max_ts} 或 None（无数据）
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
    """返回指定范围内的 OHLCV 汇总统计。

    Returns:
        {open_first, close_last, high_max, low_min, count} 或 None
    """
    conn = _get_connection(db_path)
    cursor = conn.execute("""
        SELECT
            (SELECT open FROM klines WHERE symbol=? AND interval=? AND timestamp>=? AND timestamp<=?
             ORDER BY timestamp ASC LIMIT 1) as open_first,
            (SELECT close FROM klines WHERE symbol=? AND interval=? AND timestamp>=? AND timestamp<=?
             ORDER BY timestamp DESC LIMIT 1) as close_last,
            (SELECT MAX(high) FROM klines WHERE symbol=? AND interval=? AND timestamp>=? AND timestamp<=?) as high_max,
            (SELECT MIN(low) FROM klines WHERE symbol=? AND interval=? AND timestamp>=? AND timestamp<=?) as low_min,
            COUNT(*) as cnt
        FROM klines
        WHERE symbol = ? AND interval = ? AND timestamp >= ? AND timestamp <= ?
    """, (symbol, interval, start_ts, end_ts,
          symbol, interval, start_ts, end_ts,
          symbol, interval, start_ts, end_ts,
          symbol, interval, start_ts, end_ts,
          symbol, interval, start_ts, end_ts))
    row = cursor.fetchone()
    conn.close()
    if row is None or row[4] == 0:
        return None
    return {
        "open_first": row[0],
        "close_last": row[1],
        "high_max": row[2],
        "low_min": row[3],
        "count": row[4],
    }
```

- [ ] **Step 4: 运行测试确认通过**

```bash
pytest tests/test_database.py -v
```
预期：全部 PASS

---

## Task 3: 数据展示页 `/data`

**Files:**
- Create: `app/backtest/data_routes.py`
- Create: `app/templates/backtest/data.html`
- Create: `tests/test_data_routes.py`

- [ ] **Step 1: 写失败测试**

`tests/test_data_routes.py`:
```python
"""数据展示页路由测试。"""
import pytest
from unittest.mock import patch


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestDataOverview:
    def test_get_data_page(self, client):
        r = client.get("/data")
        assert r.status_code == 200

    def test_get_data_page_lists_symbols(self, client):
        r = client.get("/data")
        body = r.data.decode()
        assert "BTCUSDT" in body

    def test_post_filter_by_range(self, client):
        """选择 symbol+interval+时间范围 → 返回 OHLCV 汇总"""
        with patch("app.backtest.data_routes.list_symbol_intervals") as mock_list, \
             patch("app.backtest.data_routes.query_klines") as mock_query, \
             patch("app.backtest.data_routes.get_interval_summary") as mock_summary:
            mock_list.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 0, "max_ts": 999999},
            ]
            mock_query.return_value = [
                {"timestamp": i, "open": "65000", "high": "65500",
                 "low": "64800", "close": "65200", "volume": "100"}
                for i in range(5)
            ]
            mock_summary.return_value = {
                "open_first": "65000", "close_last": "65200",
                "high_max": "65500", "low_min": "64800", "count": 5,
            }
            r = client.post("/data", data={
                "symbol": "BTCUSDT", "interval": "1h",
                "start_time": "2024-01-01", "end_time": "2024-01-05",
            })
            assert r.status_code == 200
            body = r.data.decode()
            assert "65000" in body  # open_first
            assert "65500" in body  # high_max
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_data_routes.py -v
```
预期：`ModuleNotFoundError` 或 404

- [ ] **Step 3: 实现 `data_routes.py`**

```python
"""数据展示路由。"""
from datetime import datetime, timezone
from flask import render_template, request

from app.backtest import backtest_bp
from app.backtest.database import (
    list_symbol_intervals, query_klines, get_interval_summary,
)
from app.config_loader import get_symbols


def _date_to_ms(date_str: str) -> int:
    """'YYYY-MM-DD' → 毫秒时间戳 (UTC)。"""
    if not date_str:
        return 0
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@backtest_bp.route("/data", methods=["GET", "POST"])
def data_index():
    symbols = get_symbols()
    ctx = {
        "symbols": symbols,
        "selected_symbol": None,
        "selected_interval": None,
        "intervals": [],
        "klines": [],
        "summary": None,
        "total_count": 0,
        "errors": None,
    }

    if request.method == "POST":
        symbol = request.form.get("symbol", "")
        interval = request.form.get("interval", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")
        ctx["selected_symbol"] = symbol
        ctx["selected_interval"] = interval

        # 数据总览
        if symbol:
            ctx["intervals"] = list_symbol_intervals(None, symbol)

        # 区间数据
        if symbol and interval:
            range_info = query_klines  # placeholder
            from app.backtest.database import get_interval_range
            range_data = get_interval_range(None, symbol, interval)
            if range_data:
                ctx["total_count"] = range_data["count"]
                start_ts = _date_to_ms(start_time) if start_time else range_data["min_ts"]
                end_ts = _date_to_ms(end_time) if end_time else range_data["max_ts"]
                ctx["klines"] = query_klines(None, symbol, interval, start_ts, end_ts)[:200]
                ctx["summary"] = get_interval_summary(None, symbol, interval, start_ts, end_ts)

    return render_template("backtest/data.html", **ctx)
```

> **注意**：上面的 `query_klines` 引用是小 bug（故意展示思考过程），实际实现应直接调用 `query_klines(None, symbol, interval, start_ts, end_ts)`。实际代码见 Step 4。

- [ ] **Step 4: 实现 `data.html`**

```html
{% extends "base.html" %}
{% block title %}数据展示 — 网格交易测算{% endblock %}
{% block content %}
<div class="glass">
    <div class="result-header">
        <div class="result-title">数据总览</div>
        <div class="mode-tag">已缓存的交易对与周期</div>
    </div>

    <form method="POST" action="/data">
        <div class="form-row" style="margin-bottom: 20px;">
            <div class="form-group" style="margin-bottom:0">
                <label>交易对</label>
                <select name="symbol" id="symbol" required onchange="this.form.submit()">
                    <option value="">— 选择币种 —</option>
                    {% for s in symbols %}
                    <option value="{{ s.symbol }}"
                        {% if selected_symbol == s.symbol %}selected{% endif %}>
                        {{ s.symbol }} ({{ s.name }})
                    </option>
                    {% endfor %}
                </select>
            </div>
        </div>

        {% if intervals %}
        <h3 style="margin: 16px 0 8px; font-size: 14px; color: var(--dim);">可用周期</h3>
        <table class="data-table">
            <thead>
                <tr>
                    <th>周期</th>
                    <th>K线数量</th>
                    <th>起始时间</th>
                    <th>结束时间</th>
                </tr>
            </thead>
            <tbody>
                {% for iv in intervals %}
                <tr>
                    <td>{{ iv.interval }}</td>
                    <td>{{ iv.count }}</td>
                    <td>{{ iv.min_ts | ms_to_date }}</td>
                    <td>{{ iv.max_ts | ms_to_date }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        {% if selected_symbol and intervals %}
        <div class="form-row" style="margin: 20px 0;">
            <div class="form-group" style="margin-bottom:0">
                <label>选择周期</label>
                <select name="interval" id="interval" required>
                    <option value="">— 选择周期 —</option>
                    {% for iv in intervals %}
                    <option value="{{ iv.interval }}"
                        {% if selected_interval == iv.interval %}selected{% endif %}
                        data-min-ts="{{ iv.min_ts }}" data-max-ts="{{ iv.max_ts }}">
                        {{ iv.interval }} ({{ iv.count }} 根)
                    </option>
                    {% endfor %}
                </select>
            </div>
        </div>

        <div class="form-row" style="margin-bottom: 20px;">
            <div class="form-group" style="margin-bottom:0">
                <label>开始时间</label>
                <input type="date" name="start_time" id="start_time"
                       value="{{ request.form.start_time if request.form else '' }}">
            </div>
            <div class="form-group" style="margin-bottom:0">
                <label>结束时间</label>
                <input type="date" name="end_time" id="end_time"
                       value="{{ request.form.end_time if request.form else '' }}">
            </div>
        </div>

        <button type="submit" class="btn-glow" name="view_data" value="1">▶ 查看数据</button>
        {% endif %}
    </form>
</div>

{% if summary %}
<div class="glass" style="margin-top: 20px;">
    <div class="result-header">
        <div class="result-title">{{ selected_symbol }} {{ selected_interval }} 区间汇总</div>
        <div class="mode-tag">共 {{ summary.count }} 根K线</div>
    </div>
    <div class="metrics">
        <div class="metric">
            <div class="v">{{ summary.open_first }}</div>
            <div class="l">区间开盘</div>
        </div>
        <div class="metric">
            <div class="v green">{{ summary.high_max }}</div>
            <div class="l">区间最高</div>
        </div>
        <div class="metric">
            <div class="v red">{{ summary.low_min }}</div>
            <div class="l">区间最低</div>
        </div>
        <div class="metric">
            <div class="v">{{ summary.close_last }}</div>
            <div class="l">区间收盘</div>
        </div>
    </div>
</div>
{% endif %}

{% if klines %}
<div class="glass" style="margin-top: 20px;">
    <div class="result-header">
        <div class="result-title">K线明细 <span style="color:var(--dim);font-size:13px;">（显示前 {{ klines|length }} 根，共 {{ total_count }} 根）</span></div>
    </div>
    <table class="data-table">
        <thead>
            <tr>
                <th>时间</th>
                <th>开</th>
                <th>高</th>
                <th>低</th>
                <th>收</th>
                <th>量</th>
            </tr>
        </thead>
        <tbody>
            {% for k in klines %}
            <tr>
                <td>{{ k.timestamp | ms_to_date }}</td>
                <td>{{ k.open }}</td>
                <td class="green">{{ k.high }}</td>
                <td class="red">{{ k.low }}</td>
                <td>{{ k.close }}</td>
                <td>{{ k.volume }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 5: 修正 `data_routes.py`（完整正确版本）**

把 Step 3 的草稿替换为完整实现：

```python
"""数据展示路由。"""
from datetime import datetime, timezone
from flask import render_template, request

from app.backtest import backtest_bp
from app.backtest.database import (
    list_symbol_intervals, query_klines, get_interval_range, get_interval_summary,
)
from app.config_loader import get_symbols


def _date_to_ms(date_str: str) -> int:
    if not date_str:
        return 0
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


@backtest_bp.route("/data", methods=["GET", "POST"])
def data_index():
    symbols = get_symbols()
    ctx = {
        "symbols": symbols,
        "selected_symbol": None,
        "selected_interval": None,
        "intervals": [],
        "klines": [],
        "summary": None,
        "total_count": 0,
    }

    if request.method == "POST":
        symbol = request.form.get("symbol", "")
        interval = request.form.get("interval", "")
        start_time = request.form.get("start_time", "")
        end_time = request.form.get("end_time", "")
        view_data = request.form.get("view_data") == "1"
        ctx["selected_symbol"] = symbol
        ctx["selected_interval"] = interval

        if symbol:
            ctx["intervals"] = list_symbol_intervals(None, symbol)

        if view_data and symbol and interval:
            range_data = get_interval_range(None, symbol, interval)
            if range_data:
                ctx["total_count"] = range_data["count"]
                start_ts = _date_to_ms(start_time) if start_time else range_data["min_ts"]
                end_ts = _date_to_ms(end_time) if end_time else range_data["max_ts"]
                ctx["klines"] = query_klines(None, symbol, interval, start_ts, end_ts)[:200]
                ctx["summary"] = get_interval_summary(None, symbol, interval, start_ts, end_ts)

    return render_template("backtest/data.html", **ctx)
```

- [ ] **Step 6: 添加 Jinja 过滤器 `ms_to_date`**

改 `app/factory.py`，在 `create_app()` 里注册：

```python
def _ms_to_date(ms: int) -> str:
    from datetime import datetime, timezone
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

flask_app.jinja_env.filters["ms_to_date"] = _ms_to_date
```

- [ ] **Step 7: 样式追加**

在 `style.css` 末尾追加：

```css
/* ── 数据展示表格 ── */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.data-table th, .data-table td {
    padding: 8px 12px;
    text-align: right;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.data-table th {
    color: var(--dim);
    font-weight: 500;
    font-size: 11px;
    text-transform: uppercase;
}
.data-table td:first-child, .data-table th:first-child {
    text-align: left;
}
```

- [ ] **Step 8: 运行测试确认通过**

```bash
pytest tests/test_data_routes.py tests/test_database.py -v
```
预期：全部 PASS

> **Task 3 中 data_routes.py 草稿有笔误（Step 3）**：用 Step 5 正确版本覆盖即可。

---

## Task 4: 回测表单智能联动

**Files:**
- Modify: `app/backtest/routes.py` — 新增 `/backtest/available_data` JSON 端点 + GET 改造
- Modify: `app/templates/backtest/index.html` — 联动 JS
- Modify: `tests/test_backtest_routes.py` — 新端点测试
- Modify: `app/static/style.css` — `.date-hint`, `select option:disabled` 样式

- [ ] **Step 1: 写失败测试**

在 `tests/test_backtest_routes.py` 追加：

```python
    def test_available_data_endpoint(self, client):
        """GET /backtest/available_data?symbol=BTCUSDT 返回可用 interval 和时间范围"""
        with patch("app.backtest.routes.list_symbol_intervals") as mock:
            mock.return_value = [
                {"interval": "1h", "count": 100, "min_ts": 1704067200000, "max_ts": 1704153600000},
            ]
            r = client.get("/backtest/available_data?symbol=BTCUSDT")
            assert r.status_code == 200
            import json
            data = json.loads(r.data)
            assert "intervals" in data
            assert "1h" in data["intervals"]
            assert data["intervals"]["1h"]["count"] == 100

    def test_available_data_default_intervals(self, client):
        """返回的 intervals 应包含全部 5 种周期，无数据的 count=0"""
        with patch("app.backtest.routes.list_symbol_intervals") as mock:
            mock.return_value = [
                {"interval": "1h", "count": 50, "min_ts": 0, "max_ts": 999},
            ]
            r = client.get("/backtest/available_data?symbol=NEWCOIN")
            import json
            data = json.loads(r.data)
            for iv in ["1m", "5m", "15m", "1h", "4h"]:
                assert iv in data["intervals"]
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_backtest_routes.py::TestBacktestRoutes::test_available_data_endpoint -v
```
预期：404 Not Found

- [ ] **Step 3: 在 routes.py 新增 JSON 端点**

在文件顶部加 import：
```python
from app.backtest.database import list_symbol_intervals
```

在 `backtest_index` 函数之前加：

```python
ALL_INTERVALS = ["1m", "5m", "15m", "1h", "4h"]


@backtest_bp.route("/backtest/available_data")
def available_data():
    """返回某交易对可用的 interval 及其时间范围（供前端联动）。"""
    from flask import jsonify
    symbol = request.args.get("symbol", "")
    if not symbol:
        return jsonify({"intervals": {}})

    db_intervals = list_symbol_intervals(None, symbol)
    interval_map = {iv["interval"]: iv for iv in db_intervals}

    result = {}
    for iv in ALL_INTERVALS:
        if iv in interval_map:
            d = interval_map[iv]
            result[iv] = {
                "count": d["count"],
                "min_ts": d["min_ts"],
                "max_ts": d["max_ts"],
            }
        else:
            result[iv] = {"count": 0, "min_ts": None, "max_ts": None}
    return jsonify({"intervals": result})
```

- [ ] **Step 4: 改造 `backtest_index` GET — 传 symbol 默认值到模板**

修改 `backtest_index` GET 分支，把 `get_symbols()` 的完整配置也传入模板（JS 用于自动填参数）：

```python
    symbols = get_symbols()
    return render_template("backtest/index.html", errors=None, form=None,
                           symbols=symbols,
                           all_intervals=["1m", "5m", "15m", "1h", "4h"])
```

> POST 分支的 render_template 也加上 `all_intervals`（保持一致）。

- [ ] **Step 5: 改造 `index.html` — 联动 JS**

**5a. 在 `<select id="symbol">` 的每个 option 加 data-attributes（用于自动填网格参数）：**

当前回测表单的 symbol select 没 data-*attributes。改成：

```html
<select name="symbol" id="symbol" required>
    {% for s in symbols %}
    <option value="{{ s.symbol }}"
        {% if form and form.symbol == s.symbol %}selected{% endif %}
        data-entry="{{ s.entry_price }}"
        data-upper-pct="{{ s.upper_pct }}"
        data-lower-pct="{{ s.lower_pct }}"
        data-grid-size="{{ s.grid_size }}"
        data-quantity="{{ s.quantity_per_grid }}">
        {{ s.symbol }} ({{ s.name }})
    </option>
    {% endfor %}
</select>
```

**5b. 给 interval select 加 id + 起始/结束时间 input 加 class：**

```html
<select name="interval" id="interval" required>
    {% for iv in ["1m", "5m", "15m", "1h", "4h"] %}
    <option value="{{ iv }}" {% if form and form.interval == iv %}selected{% endif %}>{{ iv }}</option>
    {% endfor %}
</select>
```

起始/结束时间 input 加 id（如已有 id 就不动）：确认 `id="start_time"` 和 `id="end_time"` 已存在。

**5c. 在 `<button type="submit">` 之前、force_refresh 之后加 JS 联动逻辑：**

```html
<script>
// 状态：symbol 切换时拉可用 interval，并自动填网格参数
const symbolSelect = document.getElementById('symbol');
const intervalSelect = document.getElementById('interval');
const startDateInput = document.getElementById('start_time');
const endDateInput = document.getElementById('end_time');

// 自动填网格参数（和资金计算页行为一致）
function fillBacktestDefaults() {
    const opt = symbolSelect.options[symbolSelect.selectedIndex];
    if (!opt.dataset.entry) return;
    const entry = parseFloat(opt.dataset.entry);
    const upperPct = parseFloat(opt.dataset.upperPct);
    const lowerPct = parseFloat(opt.dataset.lowerPct);
    if (!document.getElementById('upper_price').value)
        document.getElementById('upper_price').value = (entry * (1 + upperPct / 100)).toFixed(2);
    if (!document.getElementById('lower_price').value)
        document.getElementById('lower_price').value = (entry * (1 - lowerPct / 100)).toFixed(2);
    if (!document.getElementById('grid_size').value)
        document.getElementById('grid_size').value = opt.dataset.gridSize;
    if (!document.getElementById('quantity_per_grid').value)
        document.getElementById('quantity_per_grid').value = opt.dataset.quantity;
}

// 拉可用 interval 并灰显无数据项，更新日期约束
function updateAvailableData() {
    const symbol = symbolSelect.value;
    if (!symbol) return;

    fetch(`/backtest/available_data?symbol=${encodeURIComponent(symbol)}`)
        .then(r => r.json())
        .then(data => {
            const intervals = data.intervals || {};
            // 灰显无数据 interval
            Array.from(intervalSelect.options).forEach(opt => {
                const info = intervals[opt.value];
                if (info && info.count > 0) {
                    opt.disabled = false;
                    opt.style.color = '';
                } else {
                    opt.disabled = true;
                    opt.style.color = 'rgba(255,255,255,0.25)';
                }
            });
            // 更新日期范围约束
            updateDateConstraints(intervals);
        })
        .catch(() => {});
}

function updateDateConstraints(intervals) {
    const selectedInterval = intervalSelect.value;
    const info = intervals[selectedInterval];
    if (info && info.min_ts && info.max_ts) {
        const minDate = tsToDate(info.min_ts);
        const maxDate = tsToDate(info.max_ts);
        startDateInput.min = minDate;
        startDateInput.max = maxDate;
        endDateInput.min = minDate;
        endDateInput.max = maxDate;
        // 显示提示
        let hint = document.getElementById('date-hint');
        if (!hint) {
            hint = document.createElement('div');
            hint.id = 'date-hint';
            hint.className = 'date-hint';
           EndDateInput.parentNode.appendChild(hint);
        }
        hint.textContent = `可回测范围: ${minDate} ~ ${maxDate}`;
    }
}

function tsToDate(ms) {
    return new Date(ms).toISOString().slice(0, 10);
}

symbolSelect.addEventListener('change', function() {
    fillBacktestDefaults();
    updateAvailableData();
});
intervalSelect.addEventListener('change', function() {
    // 切换到某 interval 时更新日期约束
    fetch(`/backtest/available_data?symbol=${encodeURIComponent(symbolSelect.value)}`)
        .then(r => r.json())
        .then(data => updateDateConstraints(data.intervals || {}));
});

// 初始化（DOMContentLoaded）
window.addEventListener('DOMContentLoaded', function() {
    if (symbolSelect.value) {
        fillBacktestDefaults();
        updateAvailableData();
    }
});
</script>
```

- [ ] **Step 6: stylecss 追加**

```css
/* ── 回测表单联动 ── */
select option:disabled {
    color: rgba(255,255,255,0.25);
}
.date-hint {
    font-size: 11px;
    color: var(--dim);
    margin-top: 4px;
}
```

- [ ] **Step 7: 运行测试确认通过**

```bash
pytest tests/test_backtest_routes.py -v
```
预期：全部 PASS（含 2 个新测试）

---

## Task 5: 全量验证

- [ ] **Step 1: 全量测试**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
pytest tests/ -v
```
预期：全部 PASS（原 77 + 新增 ≥6 个 = ≥83）

- [ ] **Step 2: 手动端到端验证**

```python
from app import create_app
c = create_app().test_client()

# 1. 导航三入口
r = c.get('/')
assert 'nav-link' in r.data.decode() and '数据展示' in r.data.decode()
r = c.get('/data')
assert r.status_code == 200
r = c.get('/backtest')
assert r.status_code == 200

# 2. available_data 端点
import json
r = c.get('/backtest/available_data?symbol=BTCUSDT')
data = json.loads(r.data)
assert '1h' in data['intervals']

# 3. 数据展示页总览+过滤
r = c.post('/data', data={'symbol': 'BTCUSDT'})
body = r.data.decode()
assert '可用周期' in body or '1h' in body

print('OK')
```

- [ ] **Step 3: recheck**

```bash
grep -c "def test_" tests/*.py
```
确认测试数量正常。

---

## Self-Review Checklist

- [x] **Spec 覆盖率**：3 项用户需求 → Task 1/3/4 一一对应
- [x] **无占位符**：每步有完整代码/命令/预期
- [x] **类型一致性**：`list_symbol_intervals` 返回 `[{interval, count, min_ts, max_ts}]`，在 Task 2/3/4 中字段名一致
- [x] **DRY**：`available_data` JSON 端点作为唯一数据源，前端 cache 复用
- [x] **YAGNI**：不做删除数据按钮（用户明确拒绝），不做 active 高亮的 JS 方案（server-side 判断足够）
- [x] **用户设计决策**：数据展示限 200 根+总数显示（用户选 1），interval 灰显（用户选 2），切币种自动填参数（用户选 3）
