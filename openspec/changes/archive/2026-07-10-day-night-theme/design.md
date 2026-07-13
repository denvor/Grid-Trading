## Context

当前项目使用单一暗色主题（`:root` CSS 变量 + Bootstrap 5.3 + 少量自定义 `style.css`）。所有模板继承 `base.html`，样式变量集中定义在 `style.css` 顶部。现有颜色在每处硬编码（badge、分页、卡片等），直接替换会大面积破坏视觉一致性。

目标是加入亮色主题、同时支持"跟随系统"和持久化。

## Goals / Non-Goals

**Goals:**
- 日/夜双主题 + "跟随系统" 三态切换
- 主题在会话间持久化
- 切换时无闪烁（FOUC 防护）
- 亮色主题满足 WCAG AA 对比度
- 暗主题保持现样观感不变

**Non-Goals:**
- 不做每用户（DB）级主题存储 — 仅 localStorage
- 不做更细粒度的主题定制（如自定义色相）
- 不老浏览器兼容（IE11 等不支持 CSS 变量的直接放弃）

## Decisions

### D1: CSS 变量分层 + `data-bs-theme` 双轨

做法：
- 把 `style.css` 顶端的 `:root { --bg, --text, ... }` 提为 `body.bk { --bg: ... }`（已有基础，只需补亮色版本）
- 新增 `body.light { --bg: #ffffff; --text: #212529; ... }` 亮色变量块
- 顶层 `<html data-bs-theme="dark|light">` 让 Bootstrap 组件自动跟随
- 自定义 CSS 变量（`--purple`, `--cyan` 等）双轨定义，亮色版本选更高对比度取值

理由：
- 复用 Bootstrap 5.3 原生 `data-bs-theme` 支持，避免重写 100+ 个组件 class
- `body.bk` / `body.light` 类控制自定义样式变量
- 单 class toggle 全局生效，逻辑最简

### D2: FOUC 防护 — `<head>` 内联脚本

在 `base.html` `<head>` 顶部加一段极简内联脚本（< 0.5KB）：
```js
(function(){try{var t=localStorage.getItem('theme')||'dark';if(t==='system')t=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.bsTheme=t;document.body.className=t==='dark'?'bk':'light';}catch(e){}})();
```
浏览器解析外部 CSS 之前先跑这段，主题在 paint 前一帧到位。

### D3: 三态 UI — 导航栏按钮组

导航栏右侧放一组 segmented control（亮 / 暗 / 跟随），用 Bootstrap `.btn-group`。当前选中项加 `.active` 类。点击循环顺序：dark → light → system → dark。

理由：三态并排放比下拉菜单直观；`.active` 指示当前状态比图标更清晰（图标在暗/亮模式下易歧义）。

### D4: 持久化策略

```js
localStorage.setItem('theme', state)  // 'dark' | 'light' | 'system'
```
无加密/敏感信息，无需考虑隐私。

## Risks / Trade-offs

- **[亮色对比度难调]** → 用 Axe/Lighthouse 抽测关键页面，对比度不足时微调变量
- **[自定义组件颜色双轨维护成本]** → 把颜色变量集中在 `:root` / `body.bk` / `body.light` 三处定义，任何改颜色都在这三点同步
- **[FOUC 脚本漏改导致闪烁]** → 把脚本做成独立的 `<script>` 不依赖外部资源，避免加载顺序问题
- **[Bootstrap variable 覆盖不全]** → 先用 `data-bs-theme` 默认值，少量组件用自定义 class 补
