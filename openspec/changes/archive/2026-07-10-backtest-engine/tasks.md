## 1. 数据库与数据获取基础设施

- [x] 1.1 更新 `config.ini`，新增 `[api]` 节（proxy + request_interval）和 `[database]` 节（path）
- [x] 1.2 创建 `app/backtest/__init__.py`（Blueprint 注册）
- [x] 1.3 创建 `app/backtest/database.py`，实现 SQLite 初始化 + CRUD（建表、查询、插入/替换）
- [x] 1.4 创建 `app/backtest/data_fetcher.py`，实现核心函数：
  - `fetch_klines(symbol, interval, start_time, end_time, force_refresh=False)` — CLI + Web 共用
  - 从 `config.ini` 自动读取 proxy 和 request_interval
  - 分页逻辑（单次 ≤1000 根，按 endTime 翻页）
  - 请求间隔 sleep（避免限流）
  - 错误处理（网络超时、API 错误、无效交易对、代理不可达）
  - 数据库缓存命中逻辑
- [x] 1.5 数据格式标准化（OHLCV + Decimal 价格）+ 数据库幂等写入

## 2. 独立 CLI 工具

- [x] 2.1 创建 `fetch_data.py`（项目根目录），独立可执行
- [x] 2.2 实现命令行参数解析（argparse）：--symbol, --interval, --start, --end, --force
- [x] 2.3 实现进度打印（已获取/总数/百分比）
- [x] 2.4 实现结果汇总（"共获取 X 根K线，存入数据库 Y 条（新增 Z 条）"）

## 3. 回测引擎

- [x] 3.1 创建 `app/backtest/engine.py`，实现 `backtest()` 主函数
- [x] 3.2 实现网格挂单/成交逻辑（遍历K线，用 high/low 判断是否触达网格线）
- [x] 3.3 实现买入后挂卖单、卖出后挂买单的逻辑
- [x] 3.4 实现资金与持仓状态管理（Decimal 精度）
- [x] 3.5 实现统计指标计算（总收益率、最大回撤、胜率、交易次数、资金曲线）
- [x] 3.6 资金不足时自动停止新开网格的 guard

## 4. Web 路由与前端

- [x] 4.1 创建 `app/backtest/routes.py`，实现 `GET /backtest`（表单）和 `POST /backtest`（执行回测）
- [x] 4.2 实现参数解析与校验逻辑（时间格式、范围校验、逻辑校验）
- [x] 4.3 创建 `app/templates/backtest/index.html`（参数输入表单，含时间选择器，复用 DeFi 主题）
- [x] 4.4 创建 `app/templates/backtest/result.html`（回测结果展示）
- [x] 4.5 实现 SVG 收益曲线绘制（纯前端，无外部库）
- [x] 4.6 在现有 `base.html` 中添加导航（测算 / 回测切换）

## 5. 单元测试

- [x] 5.1 编写 `tests/test_database.py`（SQLite CRUD + 幂等性测试）
- [x] 5.2 编写 `tests/test_data_fetcher.py`（API mock 测试 + 缓存命中测试 + 限流间隔测试）
- [x] 5.3 编写 `tests/test_fetch_data_cli.py`（CLI 参数解析和集成测试）
- [x] 5.4 编写 `tests/test_backtest_engine.py`（核心回测逻辑 + 统计指标验证）
- [x] 5.5 编写 `tests/test_backtest_routes.py`（路由集成测试）

## 6. 运行验证

- [x] 6.1 运行 CLI：`python fetch_data.py --symbol BTCUSDT --interval 1h --start 2024-01-01 --end 2024-01-31`，确认数据入库
- [x] 6.2 运行 CLI 二次：相同参数应提示"数据已存在 X 条"，秒完成
- [x] 6.3 运行 CLI 强制刷新：`--force` 应重新拉取
- [x] 6.4 启动 Flask `/backtest`，用刚拉取的数据执行回测
- [x] 6.5 验证边界场景：资金不足、极端行情、零成交
- [x] 6.6 验证精度：所有金额为 2 位小数
