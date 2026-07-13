## Why

加密货币网格交易中，交易者凭经验设定杠杆、网格间距、上下限等参数，极易因参数组合不当导致爆仓。当前缺乏一个本地化的测算工具来提前评估参数安全性，避免真金白银的试错成本。

## What Changes

- 新建一个 Flask + Jinja2 Web 应用，提供参数输入表单和测算结果展示页
- 实现核心测算引擎（python `decimal` 模块），计算爆仓价、安全边际、网格收益
- 在页面中给出安全性评估结论与参数调整建议
- 建立 `venv` 虚拟环境隔离项目依赖

## Capabilities

### New Capabilities

- `grid-calculator`: 网格交易参数输入、安全性测算（爆仓价、安全边际、最大回撤）、结果展示与建议

### Modified Capabilities

无（从零开始的全新项目）

## Impact

- **代码**：新增完整的 Flask 应用目录结构（`app/`、`templates/`、`requirements.txt`）
- **依赖**：Python 标准库 + Jinja2（`requirements.txt` 声明）
- **系统**：仅本地 `flask run` 运行，无外部服务依赖
- **数据库**：无，纯测算型工具
