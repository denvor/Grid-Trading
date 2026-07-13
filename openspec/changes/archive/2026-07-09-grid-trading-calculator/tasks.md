## 1. 项目初始化

- [x] 1.1 在项目根目录创建 `venv` 虚拟环境并激活
- [x] 1.2 创建 `requirements.txt`，声明依赖（Jinja2）
- [x] 1.3 安装依赖到 venv

## 2. 核心测算引擎

- [x] 2.1 创建 `app/calculator.py`，实现 `calculate_liquidation_price()`（爆仓价）
- [x] 2.2 实现 `assess_safety()`（安全等级评估：安全/警告/危险）
- [x] 2.3 实现 `calculate_grid_distribution()`（网格数量、单次利润）
- [x] 2.4 实现 `calculate_max_drawdown()`（最大回撤）
- [x] 2.5 实现 `generate_suggestions()`（参数调整建议）
- [x] 2.6 实现主入口 `analyze()`，聚合以上结果返回完整测算 JSON

## 3. Web 应用骨架

- [x] 3.1 创建 `app/__init__.py`（Flask 工厂函数，配置 template 路径）
- [x] 3.2 创建 `app/routes.py`，实现 `GET /`（渲染表单）和 `POST /`（接收参数、调用测算、渲染结果）
- [x] 3.3 实现表单参数解析与校验逻辑（必填、范围、上下限逻辑）
- [x] 3.4 创建 `app/templates/base.html`（公共 HTML 骨架）

## 4. 前端模板与样式

- [x] 4.1 创建 `app/templates/index.html`（参数输入表单页）
- [x] 4.2 创建 `app/templates/result.html`（测算结果展示页）
- [x] 4.3 编写 `app/static/style.css`（基础样式：表单布局、安全/警告/危险三级颜色）

## 5. 运行验证

- [x] 5.1 启动 Flask 应用，确认 `/` 可正常访问
- [x] 5.2 填写一组安全参数提交，确认展示正确结果
- [x] 5.3 填写一组危险参数提交，确认红色警告和建议正确触发
- [x] 5.4 验证边界场景：杠杆=1（无杠杆）、下限紧贴爆仓价
- [x] 5.5 验证输入校验：空字段、下限>=入场价、杠杆超范围
