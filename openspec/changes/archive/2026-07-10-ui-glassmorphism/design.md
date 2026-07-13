## Context

当前 Bootstrap 化之后，界面组件直接使用 `.card` / `.form-control` / `.btn` 默认样式，呈现"模板感"：扁平、灰白边框、无视觉层次。原 DeFi 风格特色是半透明毛玻璃 + 紫青渐变 + 发光边框 + 大圆角 + 讲究的 gap 与阴影层次。本设计以 Bootstrap 做组件骨架、用 CSS 变量 + 自定义 class 把玻璃拟物风格叠回去。

同时 Bootstrap 默认 input 宽 100%、四条边独立、纵向堆叠，导致"一条条很长"的观感。设计改为在卡片内部用更紧凑的栅格 + 圆角胶囊 input + 卡片内分组来解决。

## Goals / Non-Goals

**Goals:**
- 容器/卡片改玻璃拟物（半透明 + blur + 发光边框 + `18px` 圆角）
- 输入框改胶囊形（`border-radius: 18px`），聚焦内阴影 + 紫色光晕
- 按钮统一发光（紫青渐变 + hover lift + 流光 sheen）
- 标题/指标数值更突出（渐变文字 + bounce hover）
- 导航栏、徽章、分页、表格、建议条全部升级到玻璃拟物质感
- 修复布局过长的视觉问题：表单输入在紧凑卡片内分组，间距收紧
- 兼容日/夜双主题（day-night-theme 已就绪）

**Non-Goals:**
- 不动路由/engine/database 逻辑
- 不引入第三方 UI 库（纯 CSS + Bootstrap 5.3）
- 不做新的交互动效框架（仅 CSS transition）

## Decisions

| 决策 | 方案 | 理由 |
|------|------|------|
| D1 玻璃拟物 | `background: rgba(255,255,255,0.05) + backdrop-filter: blur(16px) + border: 1px solid rgba(255,255,255,0.08)` | 直接复用原 DeFi CSS 技术，兼容浏览器自动回退 |
| D2 圆角 | 主卡片 `border-radius: 20px`，input `18px`，button `12px` | 比 Bootstrap 默认 `6-8px` 更柔和 |
| D3 发光按钮 | `background: linear-gradient(135deg, var(--purple), var(--cyan))` + `box-shadow: 0 4px 20px rgba(168,85,247,0.3)` + hover `translateY(-2px)` | 与原 `btn-glow` 一致，统一所有主操作按钮 |
| D4 卡片内布局 | 表单行从整行拉通改为 `.glass` 卡片内 `row g-3`，input 不再顶满宽 | 解决"一条条很长"问题 |
| D5 颜色变量 | 保留 CSS 变量体系，亮/暗主题各自定义 | 与 day-night-theme 兼容 |
| D6 发光边框 | `::before` 伪元素做顶部 1px 高光条 | 与原 DeFi 风格一致 |

## Risks / Trade-offs

- **`backdrop-filter` 兼容性** → 回退到半透明背景（已验证）
- **玻璃拟物在亮色底下易过亮** → 亮色模式用更实的背景（`rgba(255,255,255,0.85)`）+ 投影替代
- **长表单视觉** → 通过卡片分组 + 收紧间距解决，不改功能
