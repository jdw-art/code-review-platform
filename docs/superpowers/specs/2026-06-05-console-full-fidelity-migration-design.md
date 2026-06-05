# 控制台 1:1 高保真迁移与真实联调设计

## 1. 背景

仓库当前同时存在两套相关前端资产：

- `ai-code-review-console/`：一套高保真管理台原型，已经覆盖登录、仪表盘、项目管理、模板、模型、机器人、审查记录、成员分析、RBAC、系统日志、项目对话工作区等页面，并定义了明确的视觉与交互表达。
- `frontend/`：当前正式前端工程，已经具备真实路由、认证体系、HTTP client、API 分层、部分后台页面与测试基础设施。

后端 `backend/` 已经具备大部分后台业务域接口与 agent 基础能力，但接口字段、聚合粒度和部分交互型动作尚未完全对齐 `ai-code-review-console` 原型。

本阶段目标不是继续维护两套体验，而是把 `ai-code-review-console` 的页面和交互完整迁移进 `frontend`，并完成与 `backend` 的真实联调。

## 2. 已确认决策

以下决策已经由用户明确确认：

- 迁移策略采用“双轨过渡”。
- 页面与交互目标为 `ai-code-review-console` 的 `1:1` 高保真复刻。
- 当原型与现有后端能力不一致时，以前端原型为准。
- 数据与副作用全部真实化，不保留随机分数、假测试、假日志、假 trace 或本地模拟成功提示。
- 第一阶段范围同时包含：
  - 登录
  - 仪表盘
  - 项目管理
  - 项目模板管理
  - 模型管理
  - 通知机器人
  - 审查记录
  - 成员分析
  - 用户管理
  - 角色管理
  - 系统日志
  - 项目对话流

## 3. 目标

本阶段完成后，`frontend` 应满足以下目标：

- 登录后整体视觉、文案、信息密度和交互顺序与 `ai-code-review-console` 保持一致。
- 继续使用正式前端工程的路由、认证、API client 和测试体系，不额外维护一套平行应用。
- 所有列表、详情、表单、切换、删除、测试、审查触发和对话流均调用真实后端。
- 后端接口在能复用时复用，在语义或字段不兼容时进行兼容扩展；缺失能力则新增正式接口。
- 项目对话工作区基于真实 session、message 与 SSE 事件流工作，支持历史恢复。

## 4. 非目标

本阶段明确不做以下内容：

- 不保留 `ai-code-review-console` 作为长期运行的第二套正式前端。
- 不推翻 `frontend` 的现有路由、认证上下文、token 刷新或 HTTP client 实现。
- 不为了贴合原型而整体重命名现有后端领域模型字段。
- 不引入新的全局前端状态管理框架。
- 不重写后端所有已有管理域接口，只在必要处扩展或新增。
- 不在 Repo Agent 中开放写文件、执行 shell、自动提交或自动发起 PR/MR 修改。

## 5. 当前工程现状

### 5.1 前端现状

`frontend` 已存在正式管理台路由与页面入口，核心位置包括：

- 路由：`frontend/src/routes/router.tsx`
- 壳子：`frontend/src/components/layout/AppShell.tsx`
- 登录：`frontend/src/pages/auth/LoginPage.tsx`
- 业务页：
  - `frontend/src/pages/dashboard/DashboardPage.tsx`
  - `frontend/src/pages/projects/ProjectListPage.tsx`
  - `frontend/src/pages/projects/ProjectAgentPage.tsx`
  - `frontend/src/pages/projects/ProjectTemplateListPage.tsx`
  - `frontend/src/pages/models/ModelListPage.tsx`
  - `frontend/src/pages/bots/BotListPage.tsx`
  - `frontend/src/pages/reviews/ReviewRecordListPage.tsx`
  - `frontend/src/pages/analytics/MemberAnalyticsPage.tsx`
  - `frontend/src/pages/system/UserListPage.tsx`
  - `frontend/src/pages/system/RoleListPage.tsx`
  - `frontend/src/pages/system/AuditLogPage.tsx`
- API 分层：
  - `frontend/src/features/dashboard/api.ts`
  - `frontend/src/features/projects/api.ts`
  - `frontend/src/features/project-templates/api.ts`
  - `frontend/src/features/models/api.ts`
  - `frontend/src/features/bots/api.ts`
  - `frontend/src/features/reviews/api.ts`
  - `frontend/src/features/member-analytics/api.ts`
  - `frontend/src/features/system/api.ts`
  - `frontend/src/features/agent/api.ts`

### 5.2 后端现状

`backend` 已存在大部分后台管理域接口与服务：

- 认证与访问上下文：`auth.py`、`me.py`
- 仪表盘：`dashboard.py`
- 项目：`projects.py`
- 项目模板：`project_templates.py`
- 模型：`llm_models.py`
- 通知机器人：`notification_bots.py`
- 审查记录：`review_records.py`
- 成员分析：`member_analytics.py`
- 用户 / 角色 / 权限 / 菜单：`users.py`、`roles.py`、`permissions.py`、`menus.py`
- 审计日志：`audit_logs.py`
- Repo Agent：`agent.py`

因此本阶段核心不是从零建设，而是“视觉与交互迁移 + 契约补齐 + 动作真实化”。

## 6. 总体方案

采用“保留正式工程骨架，在页面层迁入原型体验，在接口层做兼容和补齐”的方案。

### 6.1 保留的基础设施

以下基础设施继续保留并复用：

- `frontend` 现有 `react-router` 路由体系
- `auth-context` 与 token store
- `http` client 与 API 模块分层
- 现有 Vitest / React Testing Library 测试基础设施
- `backend` 现有业务域 service、schema、route 组织方式

### 6.2 新增的前端兼容层

在 `frontend` 中新增一层控制台兼容 UI 结构，职责如下：

- 共享视觉壳子与原型级页面组件
- view-model / serializer
- 页面动作编排层

建议新增目录：

- `frontend/src/components/console/`
- `frontend/src/features/*/serializers.ts`
- `frontend/src/features/*/view-models.ts`

其中：

- `components/console/` 负责 1:1 复刻 `ai-code-review-console` 的视觉表达。
- `serializers.ts` 负责把真实接口字段映射到原型页面字段。
- `view-models.ts` 负责组织页面所需的聚合展示结构和动作状态。

### 6.3 双轨过渡的含义

“双轨过渡”在本项目中的落地定义如下：

- 不新建一套平行的正式路由树。
- 不复制一套新的前端认证或 API 基建。
- 在现有页面入口上逐页替换为高保真版本。
- 允许一段过渡期内保留现有 feature/api 模块，但逐步把页面表达切换为 `ai-code-review-console` 风格。
- 允许前端存在“接口字段”和“页面字段”的双轨，但必须通过 serializer 隔离，不允许页面直接散落兼容逻辑。

## 7. 页面映射与迁移落位

页面迁移全部落在现有正式路由地址中：

- `/login` -> 迁移为 `ai-code-review-console` 登录页体验
- `/dashboard` -> 迁移为仪表盘
- `/projects` -> 迁移为项目管理
- `/projects/:projectId/agent` -> 迁移为项目对话工作区
- `/project-templates` -> 迁移为项目模板管理
- `/models` -> 迁移为模型管理
- `/notification-bots` -> 迁移为通知机器人管理
- `/review-records` -> 迁移为审查记录列表
- `/review-records/:reviewRecordId` -> 迁移为审查记录详情，并承接原型中详细摘要表达
- `/member-analytics` -> 迁移为成员分析
- `/system/users` -> 迁移为用户管理
- `/system/roles` -> 迁移为角色管理
- `/audit-logs` -> 迁移为系统日志

迁移完成后，用户在 `frontend` 中看到的页面应与 `ai-code-review-console` 一致，但 URL 保持正式系统现有设计。

## 8. 接口兼容策略

### 8.1 直接复用并做前端字段适配

以下业务域优先复用现有接口，通过前端 serializer 做字段兼容：

- 登录与访问上下文
- 项目模板管理
- 模型管理
- 通知机器人
- 审查记录
- 成员分析
- 用户管理
- 角色管理
- 权限与菜单
- 审计日志

适配重点包括：

- `PageResponse<T>` 到原型分页控件的映射
- `is_active`、`is_default`、`last_test_status` 等字段到状态标签与按钮文案的映射
- 后端结构化详情到原型卡片化信息展示的映射

### 8.2 扩展现有接口

以下业务域应优先扩展已有接口，而不是新开平行接口：

#### 仪表盘

沿用 `GET /api/v1/dashboard/overview`，但扩展返回结构，使其一次返回：

- KPI 统计
- 最近审查记录
- 当前活跃模型摘要
- 仓库健康摘要
- 项目提交与评分图表数据
- 成员提交与评分图表数据

第一版不额外拆 `charts` 子接口，避免前端为一个页面拼装多次请求。

#### 项目管理

沿用：

- `GET /api/v1/projects`
- `GET /api/v1/projects/options`
- `POST /api/v1/projects`
- `PUT /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}/status`

扩展列表字段以满足原型卡片所需信息：

- 默认模板摘要
- 默认模型摘要
- 默认机器人摘要
- 最近审查时间
- 平均评分
- 主要语言显示字段

#### 审查记录

沿用：

- `GET /api/v1/review-records`
- `GET /api/v1/review-records/{review_record_id}`
- `GET /api/v1/review-records/filters`

扩展列表与详情，使其能直接支撑：

- 分值状态
- diff 统计
- 通知派发状态
- 原型中“AI 报告诊断意见”的摘要表达

#### 成员分析

沿用：

- `GET /api/v1/member-analytics`
- `GET /api/v1/member-analytics/{project_member_id}`

扩展聚合字段，以支撑原型中的成员排名、质量概览和风险摘要。

#### 审计日志

沿用：

- `GET /api/v1/audit-logs`
- `GET /api/v1/audit-logs/{log_id}`

扩展筛选与字段返回，以支撑原型中的：

- 成功 / 失败筛选
- 操作人快照
- 请求路径 / 方法
- IP 与详细说明展示

### 8.3 新增正式接口

以下能力不应再由前端模拟，必须新增或明确增强正式接口。

#### 8.3.1 项目触发审查

新增：

- `POST /api/v1/projects/{project_id}/review-executions`

用途：

- 由用户手动触发一次真实审查执行。
- 创建审查任务并返回受理结果。
- 后续由现有执行链路更新审查记录、项目最近审查时间、平均分和通知状态。

说明：

- `ai-code-review-console` 中项目页的“立即监测”在第一版仍保持“进入项目对话工作区”的视觉与主交互。
- 真实“触发审查”动作放在项目工作区页头或项目操作区，并写入审计日志。

#### 8.3.2 通知机器人测试

新增：

- `POST /api/v1/notification-bots/{bot_id}/test`

用途：

- 真实调用 webhook 测试目标通道。
- 返回测试结果、错误摘要和测试时间。
- 同步更新 `last_test_status`、`last_test_message`、`last_test_at`。

#### 8.3.3 审计日志清理

新增：

- `POST /api/v1/audit-logs/purge`

请求约束：

- 仅允许超管或新增的 `audit_log:purge` 权限调用。
- 第一版固定只清理业务审计日志，不清理系统保底安全日志。

用途：

- 支撑原型中的“清空审计日志”按钮。
- 真实操作必须落一条不可被本次 purge 清除的系统审计记录。

#### 8.3.4 Agent 历史恢复与事件补齐

在现有 Repo Agent 基础上新增或扩展：

- `GET /api/v1/projects/{project_id}/agent/sessions/{session_id}`
- `GET /api/v1/projects/{project_id}/agent/sessions/{session_id}/messages`

并扩展 SSE 事件模型，至少支持：

- `session.synced`
- `context.loaded`
- `run.started`
- `tool.started`
- `tool.completed`
- `assistant.delta`
- `assistant.completed`
- `run.completed`
- `run.failed`

前端基于这些真实事件渲染原型中的 trace 和流式消息状态。

## 9. 真实化交互设计

### 9.1 登录

- 使用正式 `/auth/login`、`/me/access-context`。
- 登录成功后按真实权限构建菜单。
- 前端保留原型的默认账号切换 UI，但仅作为输入快捷方式，不嵌入假登录逻辑。

### 9.2 仪表盘刷新

- 保留原型的“同步状态”按钮位置与文案。
- 行为定义为重新拉取仪表盘数据，不触发重型后台任务。
- 如果后端存在聚合缓存，允许在 service 内刷新，但不额外暴露重型刷新任务接口。

### 9.3 项目管理

- 新建、编辑、启停、删除全部调用真实接口。
- “立即监测”保持进入工作区语义。
- 工作区内新增真实“触发审查”按钮，使用 `POST /projects/{project_id}/review-executions`。

### 9.4 模板 / 模型 / 机器人 / 用户 / 角色 / 日志

- 所有弹窗、抽屉、切换、删除、保存均落真实接口。
- 成功后刷新列表或做局部更新。
- 失败展示真实错误信息。
- 关键动作写真实审计日志。

### 9.5 机器人测试

- 点击测试后调用真实测试接口。
- 前端不再随机生成成功或失败。
- 返回结果直接映射为原型中的提示条与状态展示。

### 9.6 项目对话流

- 创建会话、发送消息、拉取历史、订阅 SSE 全部真实。
- 会话按项目与分支锁定。
- 前端保留原型中的会话侧栏、消息块、trace 面板和流式效果。
- trace 面板严格基于真实 SSE 阶段事件，不保留前端打字机伪步骤。

## 10. 前端实现边界

### 10.1 共享 UI

优先抽出以下共享组件，供多个高保真页面复用：

- 侧边栏导航
- 顶栏
- 页面头卡片
- KPI 卡片
- 卡片式列表项
- 原型风格分页器
- 原型风格抽屉 / 模态框
- 状态 badge
- toast / inline banner
- trace 展示块

### 10.2 页面实现原则

- 页面入口继续保留在 `frontend/src/pages/*`。
- 页面内部优先使用控制台共享组件，而不是散落写样式。
- API 调用只通过 `frontend/src/features/*/api.ts` 发出。
- 字段兼容只放在 serializer / view-model 层，不散落在 JSX 中。
- 不在页面组件里持有长期 mock 数据。

## 11. 后端实现边界

### 11.1 组织方式

继续沿用现有后端结构：

- `app/api/routes`
- `app/schemas`
- `app/services`
- `app/db/models`

不额外引入新的 repository 抽象层。

### 11.2 新增或扩展的核心服务职责

- `DashboardService`：返回完整仪表盘聚合结构
- `ProjectService`：扩展项目摘要与选项返回
- `ReviewExecutionService`：承接手动触发审查
- `NotificationBotService`：新增真实测试动作
- `AuditLogService`：新增受控 purge 能力
- `AgentSessionService`：补齐历史恢复与 richer SSE 事件

### 11.3 权限

沿用现有权限体系，并新增：

- `audit_log:purge`
- 如需要，可新增 `project:trigger-review`

若不新增 `project:trigger-review`，则手动触发审查默认归属 `project:update` 或单独由 service 限制。第一版推荐显式新增 `project:trigger-review`，避免语义混淆。

## 12. 实施顺序

第一版实施按以下顺序推进：

### 阶段 0：共享壳子与视觉底座

- 登录页
- 侧边栏
- 顶栏
- 共享页面组件

目标：

- `frontend` 一进入后台后，整体观感已经与 `ai-code-review-console` 一致。

### 阶段 1：基础数据管理域

- 项目模板管理
- 模型管理
- 通知机器人
- 审查记录
- 成员分析
- 用户管理
- 角色管理
- 系统日志

目标：

- 优先稳定高保真列表、表单、分页、状态切换与审计链路。

### 阶段 2：仪表盘与项目管理

- 仪表盘完整聚合
- 项目管理高保真改造
- 项目触发审查真实化

### 阶段 3：项目对话流

- 会话列表
- 分支锁定会话创建
- 历史消息恢复
- SSE trace 与流式回答

### 阶段 4：联调收口与回归

- 全量页面联调
- 权限回归
- 视觉比对
- 错误路径回归

## 13. 测试与验收标准

### 13.1 视觉验收

以下内容必须与 `ai-code-review-console` 达到 1:1 高保真：

- 页面布局
- 文案
- 信息密度
- 状态标签
- 弹窗和抽屉结构
- 分页和筛选位置
- 对话工作区排版

允许实现细节不同，但不允许用户可见体验明显偏离。

### 13.2 数据验收

- 不存在前端硬编码随机结果。
- 刷新页面后数据可恢复。
- 所有按钮均落真实接口。
- 关键副作用可在数据库与日志中追溯。

### 13.3 权限验收

- 菜单显示与真实权限一致。
- 未授权操作由前后端共同拦截。
- 超管与普通用户在页面可见性和可操作性上符合 RBAC 预期。

### 13.4 测试要求

前端至少补齐：

- 页面渲染测试
- 关键交互测试
- 失败提示测试
- Agent SSE 事件渲染测试

后端至少补齐：

- 仪表盘聚合接口测试
- 项目触发审查接口测试
- 机器人测试接口测试
- 审计日志 purge 接口测试
- Agent 历史恢复与 SSE 事件测试

## 14. 风险与约束

- 高保真复刻会放大页面组件复用与样式一致性要求，必须先稳住共享壳子。
- 若把字段兼容逻辑散落在页面 JSX 中，后续维护成本会迅速上升，因此 serializer 是硬性边界。
- 仪表盘与项目页存在较多聚合字段，后端返回结构必须直接面向页面消费，避免前端大量拼装。
- Agent 工作区是复杂度最高的页面，必须建立在稳定 session / message / SSE 协议之上，不能先用假 trace 占位。

## 15. 最终结果定义

本阶段完成的定义如下：

- `frontend` 成为唯一正式管理台前端入口。
- `ai-code-review-console` 不再承担正式产品前端职责，只保留为历史原型参考。
- 用户在 `frontend` 中完成的后台操作、通知测试、审查触发和对话流均为真实业务行为。
- 页面体验与 `ai-code-review-console` 保持一致，而工程体系继续建立在现有 `frontend + backend` 基础上。
