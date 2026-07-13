## Why

当前项目仅支持暗色（dark）主题，部分用户在明亮环境下阅读困难（文字/背景对比度问题在本项目早期迭代反复出现）。提供日/夜主题切换能显著改善不同光照条件下的可用性和可访问性。

## What Changes

- 新增 `theme.css`（亮色主题变量）与现有 `style.css`（暗色主题变量）分离
- 新增主题切换按钮（导航栏右侧），支持 亮色 / 暗色 / 跟随系统 三态
- 用户选择持久化到 `localStorage`，跨会话保持
- Bootstrap 组件通过 `data-bs-theme` 属性与 CSS 变量双轨适配，不破坏现有组件样式
- 默认为亮色主题（首次访问无 localStorage 时），用户可一键切到暗色

**BREAKING**: 无。纯新增功能，暗色为默认。

## Capabilities

### New Capabilities

- `theme-toggle`: 日/夜主题切换的能力，包含：主题状态管理（localStorage）、三态切换 UI（亮/暗/跟随系统）、CSS 变量驱动的主题化方案、系统偏好监听与回退。

### Modified Capabilities

（无。现有 `backtest-engine`、`backtest-ui`、`data-fetcher` spec 的需求不变，仅新增独立主题能力。）

## Impact

- **前端改动**：`app/static/style.css` 提取暗色变量、新建 `app/static/theme-light.css` 亮色变量、`app/templates/base.html` 增加主题切换按钮与适配脚本
- **无后端改动**：不涉及 engine/routes/database
- **新增依赖**：无。纯 CSS + 少量 vanilla JS
- **影响页面**：所有页面（base.html 是所有模板的父级）
- **测试**：需要新增 e2e 测试验证切换流程和持久化；现有视觉测试需覆盖亮色模式
