## ADDED Requirements

### Requirement: Glassmorphism card surface
系统 SHALL 使用半透明毛玻璃表面作为主要容器背景（`backdrop-filter: blur` + 低透明度背景 + 发光边框）。

#### Scenario: Dark theme card
- **WHEN** 暗色主题下渲染主容器
- **THEN** 容器背景为半透明深色，有模糊效果和顶部高光条

#### Scenario: Light theme card
- **WHEN** 亮色主题下渲染主容器
- **THEN** 容器背景为半透明白色 + 投影（无模糊也可读）

### Requirement: Glowing buttons
系统 SHALL 主操作按钮使用紫青渐变 + 阴影 + hover lift效果。

#### Scenario: Submit button
- **WHEN** 用户 hover 提交按钮
- **THEN** 按钮上移 2px、阴影加深、流光扫过

### Requirement: Compact form inputs
系统 SHALL 表单输入框采用胶囊形（`border-radius: 18px`），并在紧凑卡片内排版，不再整行拉通过长。

#### Scenario: Form input rendering
- **WHEN** 渲染表单 input / select
- **THEN** 输入框圆角胶囊化，纵向间距收紧

#### Scenario: Input focus
- **WHEN** 用户聚焦输入框
- **THEN** 边框变紫 + 发光阴影

### Requirement: Visual hierarchy restoration
系统 SHALL 恢复原 DeFi 风格的视觉层次：渐变文字标题、色彩跳色（紫青）、指标数值突出。

#### Scenario: Metric card
- **WHEN** 渲染回测结果指标卡
- **THEN** 数值用渐变文字、更大字号、带阴影

### Requirement: Day/night theme compatibility
系统 SHALL 玻璃拟物样式在日/夜两套主题变量下都正确呈现。

#### Scenario: Theme switch
- **WHEN** 用户切换到亮色主题
- **THEN** 玻璃卡片自动切换为白色半透明 + 投影风格

### Requirement: Bootstrap component upgrade
系统 SHALL 将 Bootstrap 默认组件（card / table / badge / pagination / alert）全部升级覆盖为玻璃拟物版本。

#### Scenario: Every component
- **WHEN** 任何页面渲染 Bootstrap 组件
- **THEN** 组件呈现玻璃拟物质感，不带 Bootstrap 默认灰白边

### Requirement: No functional change
系统 SHALL 保持所有现有功能、路由、校验、逻辑不变。

#### Scenario: Backtest execution
- **WHEN** 用户提交回测
- **THEN** 后端逻辑与以前完全一致，只是 UI 不同
