## 1. 玻璃拟物基础层

- [x] 1.1 把当前 `style.css` 重构：提取 `:root` / `body.bk` / `body.light` 三层 CSS 变量，新增 `--glow-purple` `--glow-cyan` 发光色、`--radius-card: 20px` `--radius-input: 18px` `--radius-btn: 12px`
- [x] 1.2 新增 `.glass` 玻璃拟物类：半透明背景 + `backdrop-filter: blur(16px)` + 发光边框 + `::before` 顶部高光条 + 20px 圆角
- [x] 1.3 新增 `.glass-dark` / `.glass-light` 两套背景/边框/阴影变量

## 2. 按钮升级

- [x] 2.1 把所有 `btn-glow` 样式提升为 Bootstrap 按钮默认：`.btn-primary` 改为紫青渐变 + 发光阴影 + hover lift + 流光 sheen
- [x] 2.2 新增 `.btn-glow-sm` 小按钮变体（分页按钮、badge 内部按钮）
- [x] 2.3 导航栏主题切换按钮组升级：发光 active 态

## 3. 表单重构（解决"一条条很长"）

- [x] 3.1 `.form-control` / `.form-select` 改为 `border-radius: 18px`，聚焦时紫色光晕
- [x] 3.2 表单容器从整行拉通改为 `.glass` 卡片内 `row g-3`，收紧纵向间距
- [x] 3.3 表单行标签加精致感（小字号、uppercase、字母间距）
- [x] 3.4 暗色/亮色主题下 input 背景都适配

## 4. 组件升级

- [x] 4.1 `.card` 全面改玻璃拟物（覆盖 Bootstrap 默认）
- [x] 4.2 指标卡片 `.metric-value` 加渐变文字 + 字号提升
- [x] 4.3 `.badge` / `.bg-secondary-subtle` 升级：加饱和度、阴影、发光
- [x] 4.4 `.table` 改玻璃拟物：行分隔弱化、hover 高亮
- [x] 4.5 分页按钮升级：发光 + 圆角
- [x] 4.6 建议条 `.suggestion` 升级：发光边框 + 图标

## 5. 模板 class 替换

- [x] 5.1 `base.html`：导航栏改玻璃拟物导航、容器改 `.glass` 包裹
- [x] 5.2 `index.html`（资金计算）：表单外包 `.glass` 卡片
- [x] 5.3 `result.html`（计算结果）：指标卡改玻璃拟物
- [x] 5.4 `backtest/index.html`：表单外包 `.glass` 卡片
- [x] 5.5 `backtest/result.html`：指标卡和资金概览改玻璃拟物
- [x] 5.6 `backtest/data.html`：K线明细容器改玻璃拟物

## 6. 验证

- [x] 6.1 所有关键页面（/、/result、/backtest、/data、/result）暗色下目视验收
- [x] 6.2 切换亮色主题再验收一遍
- [x] 6.3 现有 89 个测试全部通过（回归）
- [x] 6.4 与截图（/tmp/pm_*.png）对比确认质感提升
