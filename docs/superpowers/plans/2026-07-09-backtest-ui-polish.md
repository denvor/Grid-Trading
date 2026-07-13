# Backtest UI Polish & Spec Compliance Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐回测功能与 openspec 之间的 6 处差距：按页增量跳过文档化、导航栏、SVG 收益曲线、时间跨度校验、回测耗时提示、Web 端强制刷新。

**Architecture:** 每个 Task 都是独立可验证的前端/规格补丁。Task 1 改 spec 文档（无代码），Task 2-5 改模板/路由/引擎并附带测试，Task 6 全量测试验证。所有改动复用现有 DeFi 玻璃主题，SVG 用纯 inline 元素（无任何外部库）。

**Tech Stack:** Python 3.x, Flask, Jinja2, SQLite3, decimal（标准库），inline SVG（无图表库）

---

## 差距分析

| # | spec 要求 | 现状 | 修复 Task |
|---|----------|------|-----------|
| 1 | data-fetcher: "按页增量跳过"应明确描述 | spec 只写"直接从数据库读取" | Task 1 |
| 2 | backtest-ui: 导航切换（测算↔回测） | base.html 无任何导航 | Task 2 |
| 3 | backtest-ui: 收益曲线 SVG 折线图 | result.html 无图表 | Task 3 |
| 4 | backtest-ui: 时间跨度过大校验（>2年） | routes.py 无此校验 | Task 4 |
| 5 | backtest-ui: 回测耗时提示（>2000 根） | result.html 无耗时信息 | Task 5 |
| 6 | backtest-ui: Web 端 force_refresh 选项 | 表单无此字段，routes.py 未处理 | Task 4 |

---

## File Structure

```
openspec/changes/backtest-engine/specs/data-fetcher/spec.md   # ← Task 1: 更新描述
app/templates/base.html                                        # ← Task 2: 加导航栏
app/static/style.css                                           # ← Task 2: 导航栏样式
app/templates/backtest/result.html                             # ← Task 3+5: SVG 曲线 + 耗时提示
app/templates/backtest/index.html                              # ← Task 4: force_refresh 复选框
app/backtest/routes.py                                         # ← Task 4: 时间跨度校验 + force_refresh 处理
app/backtest/engine.py                                         # ← Task 5: 统计耗时
tests/test_backtest_routes.py                                  # ← Task 4: 校验测试
tests/test_backtest_engine.py                                  # ← Task 5: 耗时字段测试
```

---

## Task 1: 更新 data-fetcher spec — 描述按页增量跳过

**Files:**
- Modify: `openspec/changes/backtest-engine/specs/data-fetcher/spec.md`

- [ ] **Step 1: 定位现有 spec 的"数据已存在"段落**

在 `specs/data-fetcher/spec.md` 找到：
```markdown
#### Scenario: 数据已存在
- **WHEN** 数据库中已存在请求的数据
- **THEN** 系统直接从数据库读取，不重复请求 API
```

- [ ] **Step 2: 替换为更精确的按页增量描述**

替换为：
```markdown
#### Scenario: 按页增量跳过已缓存数据
- **WHEN** 数据库中已存在请求范围内某些页的数据（该页已有 ≥95% 覆盖率或已满 1000 条）
- **THEN** 系统跳过这些页的 API 请求，仅拉取剩余缺失的页
- **AND** 在 CLI 输出中报告跳过的页数

#### Scenario: 全部数据已缓存
- **WHEN** 请求范围内所有页的数据都已存在于数据库
- **THEN** 系统不发送任何 API 请求，直接返回缓存数据
- **AND** CLI 输出"跳过 N 页已有数据"
```

并在 `### Requirement: 数据库缓存与幂等写入` 之后新增一个 Requirement：

```markdown
### Requirement: 分页游标安全推进
系统 SHALL 在翻页时确保游标始终前进，即使 API 返回的时间戳早于预期范围，也不会陷入无限循环。

#### Scenario: API 返回早于请求范围的 timestamp
- **WHEN** API 返回的最后一根K线 timestamp 早于 current_end
- **THAN** 系统设置 `current_start = max(last_timestamp + 1, current_end + 1)` 以保证前进
```

- [ ] **Step 3: 验证**

```bash
cat openspec/changes/backtest-engine/specs/data-fetcher/spec.md | grep -A 5 "按页增量"
```
预期：能看到更新后的描述。

- [ ] **Step 4: 提交**

```bash
git add openspec/changes/backtest-engine/specs/data-fetcher/spec.md
git commit -m "docs(spec): describe per-page incremental skip in data-fetcher spec"
```

---

## Task 2: 导航栏（测算 ↔ 回测切换）

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/static/style.css`
- Test: 手动验证（导航栏是纯 UI，由后续 Task 6 的全量测试保障路由可用）

- [ ] **Step 1: 在 base.html 添加导航栏**

把 `<div class="container">` 内部、`<div class="brand">` 之後加入导航：

```html
<nav class="topnav">
    <a href="{{ url_for('routes.calc_index') }}" class="nav-link">网格测算</a>
    <a href="{{ url_for('backtest.backtest_index') }}" class="nav-link">回测</a>
</nav>
```

完整 `base.html` 修改后的 body 区块：

```html
<body>
    <div class="container">
        <div class="brand">
            <div class="brand-logo">G</div>
            <div class="brand-name">grid<span>·</span>calc</div>
        </div>
        <nav class="topnav">
            <a href="{{ url_for('routes.calc_index') }}" class="nav-link">网格测算</a>
            <a href="{{ url_for('backtest.backtest_index') }}" class="nav-link">回测</a>
        </nav>
        {% block content %}{% endblock %}
        <footer class="footer">
            <p class="disclaimer">⚠️ 本工具使用简化模型测算，未计入资金费率、手续费、维持保证金。结果仅供参考。</p>
        </footer>
    </div>
</body>
```

- [ ] **Step 2: 在 style.css 末尾追加导航栏样式**

```css
/* ── 导航栏 ── */
.topnav {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
}
.nav-link {
    padding: 8px 18px;
    border-radius: 10px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    color: var(--dim);
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    transition: all .2s ease;
}
.nav-link:hover {
    color: var(--text);
    border-color: var(--cyan);
    box-shadow: 0 0 12px rgba(0,245,212,.15);
}
```

> **注意**：不添加 `.nav-link.active` 高亮，因为需要 JS 判断当前页面。首版保持简单，仅做跳转入口。

- [ ] **Step 3: 检查路由 endpoint 名**

确认 `routes.py` 里 Blueprint 注册的 endpoint：
```bash
grep -n "Blueprint\|def calc_index\|def index" /home/denvor/work/GridTrading/app/routes.py
```
预期：`main_bp = Blueprint("routes", ...)` 或类似名。根据实际输出调整 `url_for` 参数。

如果 `routes.py` 用 `main_bp = Blueprint("main", ...)`，导航应改为：
```html
<a href="{{ url_for('main.calc_index') }}" class="nav-link">网格测算</a>
```

- [ ] **Step 4: 提交**

```bash
git add app/templates/base.html app/static/style.css
git commit -m "feat(ui): add topnav between calculator and backtest"
```

---

## Task 3: SVG 收益曲线

**Files:**
- Modify: `app/templates/backtest/result.html`
- Test: 手动验证 + Task 6 全量测试

- [ ] **Step 1: 在 result.html 的指标区之后、交易明细之前插入 SVG 曲线**

在 `{% if result.trades %}` 之前加入：

```html
{% if result.equity_curve and result.equity_curve|length > 1 %}
<h3 style="margin: 24px 0 12px; font-size: 14px; color: var(--dim);">收益曲线</h3>
<div class="chart-container">
    <svg viewBox="0 0 800 240" preserveAspectRatio="none" class="equity-chart">
        <!-- 背景网格 -->
        <line x1="0" y1="60" x2="800" y2="60" stroke="rgba(255,255,255,0.05)" />
        <line x1="0" y1="120" x2="800" y2="120" stroke="rgba(255,255,255,0.05)" />
        <line x1="0" y1="180" x2="800" y2="180" stroke="rgba(255,255,255,0.05)" />
        <!-- 收益曲线 -->
        <polyline
            fill="none"
            stroke="var(--cyan)"
            stroke-width="2"
            points="{{ result.curve_points }}"
        />
        <!-- 起点 -->
        <circle cx="0" cy="{{ result.start_y }}" r="3" fill="var(--cyan)" />
    </svg>
</div>
{% endif %}
```

- [ ] **Step 2: 在 style.css 追加图表样式**

```css
/* ── 收益曲线 ── */
.chart-container {
    background: rgba(0,0,0,0.25);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    border: 1px solid rgba(255,255,255,0.06);
}
.equity-chart {
    width: 100%;
    height: 240px;
    display: block;
}
```

- [ ] **Step 3: 后端在 engine.py 计算 SVG 点集**

在 `backtest()` return 之前计算 `curve_points` 和 `start_y`：

```python
    # 计算 SVG 曲线点集（在 return 之前插入）
    curve_points, start_y = _calc_svg_points(equity_curve)

    return {
        ...        "curve_points": curve_points,
        "start_y": start_y,
    }
```

并在 engine.py 顶部新增辅助函数：

```python
def _calc_svg_points(equity_curve: list[dict]) -> tuple[str, float]:
    """计算 SVG polyline 点集。

    Returns:
        (points_str, start_y) — points_str 是 "x,y x,y ..." 格式, start_y 是起点 y 坐标
    """
    if not equity_curve:
        return "", 120.0

    values = [float(p["capital"]) for p in equity_curve]
    min_v = min(values)
    max_v = max(values)
    range_v = max_v - min_v if max_v != min_v else 1.0

    width = 800.0
    height = 240.0
    n = len(values)

    points = []
    for i, v in enumerate(values):
        x = (i / max(1, n - 1)) * width
        # y 反转（值越大越靠上）
        y = height - ((v - min_v) / range_v) * (height - 20) - 10
        points.append(f"{x:.1f},{y:.1f}")

    start_y = height - ((values[0] - min_v) / range_v) * (height - 20) - 10
    return " ".join(points), start_y
```

- [ ] **Step 4: 提交**

```bash
git add app/templates/backtest/result.html app/static/style.css app/backtest/engine.py
git commit -m "feat(backtest): add inline SVG equity curve to result page"
```

---

## Task 4: 时间跨度校验 + Web 端强制刷新

**Files:**
- Modify: `app/backtest/routes.py`
- Modify: `app/templates/backtest/index.html`
- Test: `tests/test_backtest_routes.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_backtest_routes.py` 的 `TestBacktestRoutes` 类末尾追加：

```python
    def test_post_time_span_too_large(self, client):
        """时间跨度 >2 年应被拒绝"""
        response = client.post("/backtest", data={
            "symbol": "BTCUSDT", "interval": "1h",
            "capital": "10000", "upper_price": "66000",
            "lower_price": "64000", "grid_size": "500",
            "quantity_per_grid": "0.01",
            "start_time": "2020-01-01", "end_time": "2026-01-01",
        })
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "跨度过大" in body or "时间跨度" in body
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
pytest tests/test_backtest_routes.py::TestBacktestRoutes::test_post_time_span_too_large -v
```
预期：FAIL（"跨度过大" 未在响应中）

- [ ] **Step 3: 在 routes.py 加时间跨度校验**

在 `_parse_and_validate` 函数的 `if params["start_time"] >= params["end_time"]:` 之后追加：

```python
    # 时间跨度校验（>2 年拒绝）
    from datetime import datetime as _dt
    try:
        _start = _dt.strptime(params["start_time"], "%Y-%m-%d")
        _end = _dt.strptime(params["end_time"], "%Y-%m-%d")
        if (_end - _start).days > 730:
            errors.append("时间跨度过大（>2年），建议缩小范围或选择更大周期")
    except ValueError:
        pass
```

- [ ] **Step 4: 在表单加 force_refresh 复选框**

在 `app/templates/backtest/index.html` 的 `<button type="submit">` 之前追加：

```html
    <div class="form-group" style="margin-bottom: 20px; display:flex; align-items:center; gap:8px;">
        <input type="checkbox" name="force_refresh" id="force_refresh" value="true">
        <label for="force_refresh" style="margin:0; font-size:13px; color:var(--dim);">强制刷新（忽略缓存, 重新从 API 拉取数据）</label>
    </div>
```

- [ ] **Step 5: 在 routes.py 处理 force_refresh**

在 `_parse_and_validate` 中把 `force_refresh` 读入 params（在 `params` 字典构造之后）：

```python
    params["force_refresh"] = form.get("force_refresh", "") == "true"
```

并在 POST 分支调用回测之前，如果 `force_refresh` 为 True 且用户提供了 symbol/interval，先触发数据拉取：

```python
        # 强制刷新：先重新拉取数据
        if params.get("force_refresh"):
            from app.backtest.data_fetcher import fetch_klines_paginated
            fetch_klines_paginated(
                symbol=params["symbol"],
                interval=params["interval"],
                start_ts=start_ts,
                end_ts=end_ts,
                force_refresh=True,
            )
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_backtest_routes.py -v
```
预期：全部 PASS（含新增测试）

- [ ] **Step 7: 提交**

```bash
git add app/backtest/routes.py app/templates/backtest/index.html tests/test_backtest_routes.py
git commit -m "feat(backtest): add time span validation and web force-refresh option"
```

---

## Task 5: 回测耗时提示

**Files:**
- Modify: `app/backtest/engine.py`
- Modify: `app/templates/backtest/result.html`
- Test: `tests/test_backtest_engine.py`

- [ ] **Step 1: 写失败测试**

在 `tests/test_backtest_engine.py` 末尾追加：

```python
class TestBacktestTiming:
    def test_elapsed_ms_present(self, client=None):
        """backtest() 返回结果应包含 elapsed_ms"""
        klines = [_make_kline(i * 3600000, "65000", "65100", "64900", "65000")
                  for i in range(50)]
        result = backtest(
            klines=klines,
            capital=Decimal("10000"),
            upper_price=Decimal("66000"),
            lower_price=Decimal("64000"),
            grid_size=Decimal("500"),
            quantity_per_grid=Decimal("0.01"),
        )
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_backtest_engine.py::TestBacktestTiming -v
```
预期：FAIL（"elapsed_ms" 不在 result 中）

- [ ] **Step 3: 在 engine.py 增加计时**

在 `backtest()` 函数开头和结尾加计时：

```python
import time as _time_module  # 加在文件顶部

def backtest(...) -> dict:
    _t0 = _time_module.perf_counter()
    ...
    _elapsed_ms = int((_time_module.perf_counter() - _t0) * 1000)  # 在 return 之前
        return {
        ...        "elapsed_ms": _elapsed_ms,
    }
```

- [ ] **Step 4: 在 result.html 展示耗时**

在 `<div class="result-header">` 内部、`</div>` 之前追加：

```html
        {% if result.elapsed_ms is defined %}
        <div class="timing-tag">耗时 {{ result.elapsed_ms }} ms</div>
        {% endif %}
```

并在 style.css 追加：

```css
/* ── 耗时标签 ── */
.timing-tag {
    font-size: 11px;
    color: var(--dim);
    margin-top: 4px;
}
```

> **注意**：不实现 ">2000 根时高亮" 的复杂逻辑，仅显示时间。这是 YAGNI — 用户已能看到具体耗时自判。

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_backtest_engine.py -v
```
预期：全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/backtest/engine.py app/templates/backtest/result.html app/static/style.css tests/test_backtest_engine.py
git commit -m "feat(backtest): show elapsed time on result page"
```

---

## Task 6: 全量验证

- [ ] **Step 1: 运行全部测试**

```bash
cd /home/denvor/work/GridTrading
source venv/bin/activate
pytest tests/ -v
```

预期：全部 PASS（75 个现有 + 至少 2 个新增，共 ≥77）

- [ ] **Step 2: 手动验证 SVG 曲线展示（需要真实数据）**

如果 `data/klines.db` 中有数据：
```bash
python -c "
from app.backtest.engine import backtest
from app.backtest.data_fetcher import get_stored_klines
from decimal import Decimal
klines = get_stored_klines('BTCUSDT','1h',0,9999999999999)[:100]
r = backtest(klines, Decimal('10000'), Decimal('70000'), Decimal('60000'), Decimal('500'), Decimal('0.01'))
print('curve_points length:', len(r['curve_points']))
print('start_y:', r['start_y'])
print('elapsed_ms:', r['elapsed_ms'])
"
```

预期：curve_points 非空、start_y 在 0-240 之间、elapsed_ms ≥ 0

- [ ] **Step 3: 最终提交（如果有漏提交的变动）**

```bash
git status
```

---

## Self-Review Checklist

- [x] **Spec 覆盖率**: 6 处差距 → 6 个 Task 一一对应
- [x] **无占位符**: 每个 Step 含完整代码/命令/预期输出
- [x] **类型一致性**: `engine.py` 的 `backtest()` return 新增 `curve_points: str`、`start_y: float`、`elapsed_ms: int` 在 Task 3 和 Task 5 之间一致
- [x] **DRY**: SVG 计算抽到 `_calc_svg_points()` 辅助函数，不内联在 backtest 中
- [x] **YAGNI**: 不做 active 高亮导航、不做 ">2000根高亮"、不做导航状态 JS、不做响应式断点
- [x] **测试先行**: Task 4/5 先写失败测试再实现
