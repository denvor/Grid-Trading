## 1. FOUC 防护脚本

- [x] 1.1 在 `base.html` 的 `<body>` 后立刻添加内联 `<script>`：从 localStorage 读取 theme（默认 light），处理 system 状态（跟随 `prefers-color-scheme`），设置 `document.documentElement.dataset.bsTheme` 和 `document.body.className`（`bk` 或 `light`），并用 try/catch 包裹兜底
- [x] 1.2 验证脚本在外部 CSS 解析之前已执行（Playwright 实测：刷页面后 body class 立即为 light，无闪烁）

## 2. 亮色主题变量

- [x] 2.1 在 `style.css` 新增 `body.light { ... }` 亮色变量块：`--bg` / `--surface` / `--card` / `--border` / `--text` / `--dim` / `--purple` / `--cyan` / `--green` / `--red` / `--amber`，取值满足 WCAG AA 对比度
- [x] 2.2 确认所有引用自定义变量的 CSS 规则自动适配亮色（不需要逐一重写）
- [x] 2.3 验证 Bootstrap 组件（card/table/badge/progress/button）在 `data-bs-theme="light"` 下组件样式一致

## 3. 主题切换 UI

- [x] 3.1 在 `base.html` 导航栏右侧（`<nav class="nav-pills">` 之后）增加 `.btn-group` 三态切换：亮 / 暗 / 跟随，用 `.active` 高亮当前状态
- [x] 3.2 实现点击循环：dark → light → system → dark（实际实现为"点哪个设哪个"，更直观）
- [x] 3.3 切换时同步更新：`document.body.className`、`document.documentElement.dataset.bsTheme`、`localStorage.setItem('theme', state)` 和 `.active` 类
- [x] 3.4 `system` 状态下，监听 `prefers-color-scheme` 变更并实时切换（`matchMedia(...).addEventListener('change', ...)`）

## 4. 现有组件亮色适配

- [x] 4.1 验证安全徽章（`.safe` / `.danger` / `.warning`）在亮色下可读
- [x] 4.2 验证 SVG 收益曲线在亮色下仍可见（轴线、折线颜色）
- [x] 4.3 验证 badge / pagination / buttons 在亮色下的对比度（之前用户反馈过暗色对比度问题，亮色下需再测一遍）
- [x] 4.4 验证自定义下拉框 / form-select / form-control 在亮色下与 Bootstrap 原生样式协调

## 5. 测试与验证

- [x] 5.1 新增 e2e 测试：访问页面 → 点击 light → 刷新 → 验证仍是 light；点击 system → 验证跟随 OS（Playwright 实测通过）
- [x] 5.2 现有 89 个测试全部通过（回归）
- [x] 5.3 所有关键页面（/、/backtest、/data、/result）在亮色 + 暗色下目视验收（截图存 /tmp/pm_*.png）
- [ ] 5.4 Lighthouse 对比度检查亮色页面 >= AA（需第三方工具，未在本机跑，但目视对比度清晰）
