## Context

`fetch_data.py` 调用 `fetch_klines_paginated()` 时传入一个 `progress_callback(fetched, current_end, total_end)`。回调每秒跑好几回，在同一行打印 `已获取 X 根...`（`\r` 覆盖）。两个缺陷：

1. `total_end` 是毫秒时间戳，不是行数，CLI 无法据此推算百分比和 ETA
2. 没有"预期总量"——用户不知道还会拉多久

`app/backtest/data_fetcher.py:fetch_klines_paginated()` 内部已能算出 `page_duration_ms`、`interval_seconds`，加一条除法即可得到预估总量。当前代码无独立的数据库查看工具，用户只能用 `sqlite3 data/klines.db` 看原始表。

## Goals / Non-Goals

**Goals:**

- CLI 拉取前先打印一次 `[预计 N 根]` 量级提示
- 每页完打一行可累加的进度 `[#####.....] 60% 已获取 18318/30647  用时 12s  预计剩余 8s`
- 新增独立 CLI `check_data.py`：列出各 symbol/interval 记录数、时间跨度、检测间隔异常
- 进度回调扩展为 `(fetched, estimated_total, page, total_pages, eta_seconds)` 以适应渲染需求，同时**向下兼容**旧的 3 参数回调：`delta-fetcher` 内部封装一层 adapter

**Non-Goals:**

- 不引入第三方进度条库（tqdm 等），保持只用 stdlib
- 不做 Web UI 进度实时推送（SSE）——那是后话
- 估算允许偏差 ±5%——币安实际返回受维护窗口影响可能少几根，summary 阶段显示 `获取 30640 根（预估 30647）` 即可

## Decisions

### D1：预估总量放在 `fetch_klines_paginated` 入口，每页回调时同步下去

- CLI 调用方能通过 `progress_callback` 的第二个参数直接拿到 `estimated_total`，无需重复算一次。
- 实现：`estimated_total = (end_ts - start_ts) // (interval_seconds * 1000) + 1`，传给回调。

### D2：进度条选择纯 ASCII 渲染（`[####.....]`）+ 当前 K 线时间

- 无第三方依赖；80 列内自适应宽度
- 兼容中文环境终端（`#` / `.` 不依赖 Unicode 块字符）
- 每页强制换行：已完成的页累加到底部，与跳页的 `✓` / `✗` 提示互不干扰
- **当前 K 线时间单独一列**：`last_kline_ts` 毫秒时间戳格式化为 `YYYY-MM-DD HH:MM`，置于 X/Y 计数之后

```
[#####.....] 60%  已获取 18318/30647  (当前 2024-07-01 12:00)  用时 12s  预计剩余 8s
```

- 字段顺序：进度条 | 百分比 | 已获取/预估 | (当前 YYYY-MM-DD HH:MM) | 用时 | 预计剩余
- `last_kline_ts` 通过 `datetime.fromtimestamp(ms/1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")` 格式化；当该页是跳页（cache hit）时，`last_kline_ts` 取 `current_end` 区间的末点

### D3：回调签名扩展方案——通过 **adapter 保持兼容**（含当前 K 线时间）

```python
def fetch_klines_paginated(..., progress_callback=None):
    estimated_total = (end_ts - start_ts) // (interval_seconds * 1000) + 1
    total_pages = math.ceil((end_ts - start_ts) / page_duration_ms)
    last_ts = start_ts  # 已拉取到的最新一根 K 线的毫秒时间戳
    def _notify(fetched, current_end, elapsed):
        page = ... # 当前在第几页
        eta = (elapsed / max(fetched, 1)) * max(estimated_total - fetched, 0) if progress else 0
        if progress_callback:
            try:
                progress_callback(fetched, estimated_total, page, total_pages, eta, last_ts)  # 新 6 参数
            except TypeError:
                progress_callback(fetched, current_end, end_ts)  # 退回 3 参数
    ...
```

- 新回调签名：`(fetched, estimated_total, page, total_pages, eta_seconds, last_kline_ts)`
- 使用 `try/except TypeError` 检测旧回调（不想强求 Python 3.12 `inspect.signature` 检查）
- 文档注明"新回调 6 参数，旧回调 3 参数仍可工作"
- `last_kline_ts` 在每页完成时刷新为 `klines[-1]["timestamp"]`

### D4：`check_data.py` 命令结构

```
python check_data.py [OPTIONS]

Options:
  --symbol TEXT      过滤交易对（可选）
  --interval TEXT    过滤周期（可选，与 symbol 搭配）
  --gap-threshold FLOAT  空洞检测阈值（默认 1.5，即间隔超过中位间隔 1.5 倍算作空洞）
  --json             以 JSON 格式输出（便于脚本消费）
```

- 内部调用 `list_symbol_intervals` / `count_klines` / `query_klines_paginated`
- 空洞检测：扫一遍相邻 ts 间隔，标记 > `gap_threshold × median_interval` 的断点
- JSON 模式把 `datetime` 字段格式化为 `YYYY-MM-DD HH:MM` 或保留原始毫秒

### D5：命名

CLI 命名为 `check_data.py`（与 `fetch_data.py` 对齐），内部函数入口 `main()`。

## Risks / Trade-offs

| 风险 | 应对 |
|------|------|
| 预估总量偏差大导致"60%"实际是"55%" | 摘要阶段打印 `(获取 30640，预估 30647)`，让用户看到偏差极小 |
| `try/except TypeError` 检测方法签名过于宽松 | TypeError 只在实参数量不匹配时触发，误检概率极低；同时文档标注接口 |
| 空洞检测在大数据集扫全表 O(N) | 默认 `--gap-threshold` 阈值不会减少扫描，仅做流式中位数；大数据集加 `--limit-rows` 或默认采样（每页 500 条）| 
| 终端宽度不一致导致进度条换行 | 通过 `shutil.get_terminal_size()` 回退，最小宽度 40 字符 |

## Migration Plan

1. 改 `data_fetcher.py`：回调 5 参数 + adapter
2. 跑 `test_data_fetcher.py`：更新 mock 断言适配 5 参数
3. 改 `fetch_data.py`：新进度渲染 + 估算输出
4. 跑 `test_fetch_data_cli.py`：新增断言覆盖新输出
5. 新增 `check_data.py` + `tests/test_check_data_cli.py`
6. 全量测试回归

## Open Questions

- 空洞检测要不要输出空洞的起止时间（目前默认输出"检测到 N 处空洞"，加 `--verbose` 才列出） → 默认简洁列数即可
- `--json` 输出要不要给 Web 端复用 → 暂不，CLI 够用
