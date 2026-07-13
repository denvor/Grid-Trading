## Why

Bootstrap 原生组件（扁平卡片、细边框 input、条纹 button）让界面回到"模板感"。原 DeFi 玻璃拟物风格（半透明毛玻璃卡片 + 紫青渐变 + 发光阴影 + 精致圆角）在精致度和品牌感上远超。本变更是为了让 Bootstrap 作为组件骨架、但视觉层次回到原来的高品质质感，同时解决 input/option/button 视觉过长的布局问题。

## What Changes

- **卡片/容器**：Bootstrap `.card` 升级为玻璃拟物（半透明背景 + `backdrop-filter: blur()` + 发光边框），页面主容器也改玻璃拟物
- **输入框/选择器**：去 Bootstrap 默认长条外观，改为圆角胶囊形（`border-radius: 18px`）+ 内阴影聚焦；`form-row` 从整行拉通改为更紧凑的卡片内排版
- **按钮**：全面升级为发光按钮（紫青渐变 + hover 上移 + 流光动画），主操作按钮更突出
- **Badge/Tag**：加阴影和饱和度，不再平
- **分页/表格**：当前分页和表格都太平，添加背景层次和分隔
- **布局间距 & 排版**：收紧表单纵向间距，加大卡片内 padding，指标卡片的数值更突出
- **颜色**：引入紫青渐变跳色，不再全灰蓝
- **不在范围内**：不重写路由、不重构功能、不引入新的第三方 UI 库

**BREAKING**: 无。纯 CSS + 模板 class 替换。

## Capabilities

### New Capabilities

- `glassmorphism-theme`: 玻璃拟物视觉风格系统，涵盖卡片/按钮/表单/表格/导航/分页/徽章全套组件样式重构；同时修复输入框/按钮视觉过长的问题（紧凑卡片内布局）

### Modified Capabilities

（功能需求不变，只改视觉呈现。）

## Impact

- **改动文件**：`app/static/style.css`（样式重构）、`app/templates/base.html`（主题及 class 调整）、`app/templates/index.html` `result.html` `backtest/*.html`（class 替换+布局微调）
- **无后端改动**：不影响任何 engine/route/database
- **无新依赖**：纯 CSS + 现有 Bootstrap
- **风险**：glassmorphism 的 `backdrop-filter` 在老旧浏览器不支持 → 回退到半透明（已兼容）
