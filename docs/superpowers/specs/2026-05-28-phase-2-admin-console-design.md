# 第二阶段设计文档：管理后台先行

## 1. 背景

第一阶段已经完成认证、授权、RBAC、JWT access token / refresh token、Redis refresh session 管理，以及用户、角色、权限、菜单等后端基础能力。第二阶段不继续推进真实 Git 平台接入，而是优先建设管理后台，使系统具备可配置、可管理、可查看、可演示的产品能力。

用户已经明确第二阶段采用“管理后台先行”方案，并且优先还原页面所承载的字段与业务能力，而不是优先追求视觉像素级复刻。

## 2. 阶段目标

第二阶段目标分为两个连续子阶段：

- `Phase 2A`：后端管理域落地，包含数据模型、数据库迁移、管理 API、mock 审查事件写入入口、统计与审计能力。
- `Phase 2B`：最小可用管理后台前端落地，包含登录后后台框架、核心列表页、详情页、表单页与基础权限控制。

第二阶段完成后，系统应当能够：

- 登录后台并根据当前用户权限展示菜单与页面。
- 管理项目、项目模板、模型、通知机器人。
- 通过 mock 接口导入 Push / Merge Request 审查记录。
- 在审查记录页查看列表、详情、commit 信息、原始 webhook 数据与 agent trace。
- 在成员分析页查看基于审查记录聚合的轻量统计结果。
- 在系统日志页查看关键后台操作的审计记录。

## 3. 范围

第二阶段纳入范围的模块如下：

- 仪表盘
- 项目管理
- 项目模板管理
- 审查记录
- 成员分析
- 大模型管理
- 通知机器人管理
- 用户管理
- 角色管理
- 系统日志

## 4. 非目标

第二阶段明确不做以下内容：

- GitHub / GitLab / Gitea 真实 webhook 接入
- webhook 签名校验与平台适配层
- 真正的 AI 审查执行引擎
- Deep Review 多轮对话能力
- 复杂 BI、看板大屏与高级钻取分析
- 真实通知投递闭环，仅提供配置管理与测试接口
- 多租户与复杂组织架构
- 一个项目绑定多个模板、多个模型或多个机器人

## 5. 页面与接口设计原则

### 5.1 总体原则

- 页面结构尽量贴合已有产品截图。
- 第二阶段优先还原页面字段和业务能力。
- 后端接口按页面能力直接映射，不追求过度抽象的通用接口。
- 列表页接口应直接返回表格字段、筛选选项、分页结果与状态枚举。
- 详情页接口应直接返回页面所需完整字段，不要求前端自行拼装多个接口。
- 统计页接口应返回可直接渲染的数据，不将聚合逻辑下推给前端。

### 5.2 页面与 API 对应关系

#### 登录页

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/logout-all`
- `POST /api/v1/auth/change-password`
- `GET /api/v1/me/profile`
- `GET /api/v1/me/permissions`
- `GET /api/v1/me/menus`

#### 仪表盘

- `GET /api/v1/dashboard/overview`
- `GET /api/v1/dashboard/review-trends`
- `GET /api/v1/dashboard/project-summary`
- `GET /api/v1/dashboard/member-summary`

#### 项目管理

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{id}`
- `PUT /api/v1/projects/{id}`
- `PATCH /api/v1/projects/{id}/status`
- `GET /api/v1/projects/options`

#### 项目模板管理

- `GET /api/v1/project-templates`
- `POST /api/v1/project-templates`
- `GET /api/v1/project-templates/{id}`
- `PUT /api/v1/project-templates/{id}`
- `PATCH /api/v1/project-templates/{id}/status`
- `GET /api/v1/project-templates/options`

#### 审查记录

- `GET /api/v1/review-records`
- `GET /api/v1/review-records/{id}`
- `GET /api/v1/review-records/{id}/raw`
- `GET /api/v1/review-records/filters`
- `POST /api/v1/review-records/mock-ingest`

#### 成员分析

- `GET /api/v1/member-analytics`
- `GET /api/v1/member-analytics/{member_name}`

#### 大模型管理

- `GET /api/v1/models`
- `POST /api/v1/models`
- `GET /api/v1/models/{id}`
- `PUT /api/v1/models/{id}`
- `PATCH /api/v1/models/{id}/status`
- `PATCH /api/v1/models/{id}/default`
- `POST /api/v1/models/{id}/test`

#### 通知机器人管理

- `GET /api/v1/bots`
- `POST /api/v1/bots`
- `GET /api/v1/bots/{id}`
- `PUT /api/v1/bots/{id}`
- `PATCH /api/v1/bots/{id}/status`
- `POST /api/v1/bots/{id}/test`

#### 用户与角色管理

- 复用第一阶段已有 `/api/v1/users`
- 复用第一阶段已有 `/api/v1/roles`
- 复用第一阶段已有 `/api/v1/permissions`
- 复用第一阶段已有 `/api/v1/menus`

#### 系统日志

- `GET /api/v1/audit-logs`
- `GET /api/v1/audit-logs/{id}`

## 6. 后端模块边界

第二阶段后端继续沿用第一阶段按业务域拆分、由 service 承接核心逻辑的结构，不新增额外 repository 抽象层。

建议新增业务模块：

- `dashboard`
- `projects`
- `project_templates`
- `review_records`
- `review_ingest`
- `member_analytics`
- `llm_models`
- `notification_bots`
- `audit_logs`

目录组织继续保持：

- `app/api/routes`
- `app/schemas`
- `app/services`
- `app/db/models`
- `app/security`
- `app/core`

## 7. 数据模型设计

### 7.1 主键策略

延续第一阶段约束：

- 所有表主键 `id` 必须使用 `BIGINT`
- 所有引用这些主键的外键也必须使用 `BIGINT`
- Python 与 Pydantic 层统一使用 `int`
- 不引入 UUID 主键

### 7.2 `projects`

项目主表，承接后台中的受管代码项目。

核心字段：

- `id`
- `name`
- `key`
- `platform_type`
- `repo_url`
- `default_branch`
- `description`
- `is_active`
- `review_enabled`
- `template_id`
- `default_model_id`
- `default_bot_id`
- `settings`
- `created_by`
- `created_at`
- `updated_at`

约束：

- `key` 全局唯一
- 一个项目在第二阶段只能绑定一个项目模板、一个默认模型、一个默认机器人
- 停用项目不能接收 mock 审查事件写入

### 7.3 `project_templates`

项目模板主表，支撑“项目模板管理”页面及 Review 提示词模板配置。

核心字段：

- `id`
- `name`
- `code`
- `description`
- `file_extensions`
- `review_prompt_template`
- `prompt_metadata`
- `is_system`
- `is_active`
- `created_by`
- `created_at`
- `updated_at`

字段说明：

- `file_extensions` 使用 `JSONB` 数组存储，例如 `[".java", ".xml", ".yml"]`
- `review_prompt_template` 使用文本字段存储模板提示词
- `prompt_metadata` 使用 `JSONB` 存储附加参数，例如评分维度、输出格式与语言约束

约束：

- `code` 全局唯一
- 系统预置模板可编辑展示字段，但不允许删除
- 页面列表中的“Review 提示词”状态由 `review_prompt_template` 是否为空计算得出

### 7.4 `review_records`

审查记录主表，统一承载 `push` 与 `merge_request` 两类事件。

核心字段：

- `id`
- `project_id`
- `event_type`
- `external_event_id`
- `project_name_snapshot`
- `template_id_snapshot`
- `template_name_snapshot`
- `review_prompt_snapshot`
- `author`
- `title`
- `branch`
- `source_branch`
- `target_branch`
- `commit_count`
- `commit_messages`
- `score`
- `review_status`
- `review_result`
- `summary`
- `url`
- `url_slug`
- `last_commit_id`
- `additions`
- `deletions`
- `updated_at`
- `agent_trace`
- `webhook_data`
- `extra_data`
- `created_at`

状态建议：

- `pending`
- `reviewed`
- `failed`
- `ignored`

约束：

- `event_type` 取值限定为 `push` 或 `merge_request`
- 使用 `external_event_id` 或降级唯一键做幂等去重
- 历史记录保留模板与提示词快照，避免后续模板修改影响历史解释

### 7.5 `review_commits`

审查记录下的 commit 明细表，支撑详情页展示和后续更细粒度统计。

核心字段：

- `id`
- `review_record_id`
- `commit_id`
- `short_commit_id`
- `author`
- `message`
- `timestamp`
- `sequence`
- `payload`
- `created_at`

### 7.6 `llm_models`

平台大模型配置表。

核心字段：

- `id`
- `name`
- `provider`
- `model_code`
- `base_url`
- `api_key_encrypted`
- `api_key_masked`
- `temperature`
- `max_tokens`
- `top_p`
- `prompt_template`
- `is_default`
- `is_active`
- `last_test_status`
- `last_test_message`
- `last_test_at`
- `created_at`
- `updated_at`

约束：

- `api_key` 必须加密存储，不允许 hash 存储
- 接口响应只返回 `api_key_masked`
- 同一时刻只允许一个默认模型

### 7.7 `notification_bots`

通知机器人配置表。

核心字段：

- `id`
- `name`
- `bot_type`
- `webhook_url`
- `secret_encrypted`
- `secret_masked`
- `mention_strategy`
- `template_config`
- `is_active`
- `last_test_status`
- `last_test_message`
- `last_test_at`
- `created_at`
- `updated_at`

约束：

- `secret` 必须加密存储，响应仅返回脱敏字段
- 第二阶段 `bot_type` 枚举至少包括企业微信、飞书、钉钉

### 7.8 `project_members`

项目成员关系表，用于成员分析和项目维度管理。

核心字段：

- `id`
- `project_id`
- `user_id`
- `member_name`
- `member_email`
- `role_name`
- `is_active`
- `created_at`
- `updated_at`

说明：

- 第二阶段允许 `user_id` 为空
- `member_name` 与 `member_email` 可先与审查记录中的作者信息做映射

### 7.9 `audit_logs`

后台操作审计日志表，用于系统日志页面。

核心字段：

- `id`
- `user_id`
- `username_snapshot`
- `action`
- `resource_type`
- `resource_id`
- `resource_name_snapshot`
- `request_path`
- `request_method`
- `request_payload`
- `response_status`
- `result`
- `error_message`
- `ip_address`
- `user_agent`
- `created_at`

## 8. Mock 审查事件输入契约

第二阶段不接真实 Git 平台，但必须支持 mock 审查事件导入。输入契约兼容下列两个业务对象，并允许在现有字段基础上扩展：

- `MergeRequestReviewEntity`
- `PushReviewEntity`

导入入口：

- `POST /api/v1/review-records/mock-ingest`

处理流程：

1. 接收 `push` 或 `merge_request` 类型的 mock 事件。
2. 根据 `project_id` 或 `project_key` 定位现有项目。
3. 校验项目是否启用，并读取项目当前绑定的模板、模型、机器人配置。
4. 将输入事件标准化为统一的 `review_records` 主记录。
5. 将 `commits` 明细拆分写入 `review_commits`。
6. 保留原始 `webhook_data`，同时写入项目模板快照与提示词快照。
7. 返回导入结果、记录 ID、事件类型与去重状态。

幂等规则：

- 优先使用 `external_event_id`
- 若无 `external_event_id`，使用 `project_id + event_type + url_slug + last_commit_id` 作为降级唯一键

## 9. 权限模型

第二阶段继续复用第一阶段 RBAC，不新增第二套权限体系。`Menu` 仅用于页面展示，接口鉴权仅依赖 `Permission`。

建议新增权限码：

- `dashboard:read`
- `project:read`
- `project:create`
- `project:update`
- `project:status`
- `project_template:read`
- `project_template:create`
- `project_template:update`
- `project_template:status`
- `review_record:read`
- `review_record:raw`
- `review_record:import`
- `member_analytics:read`
- `model:read`
- `model:create`
- `model:update`
- `model:status`
- `model:test`
- `model:default`
- `bot:read`
- `bot:create`
- `bot:update`
- `bot:status`
- `bot:test`
- `audit_log:read`

建议内置角色：

- `super_admin`
- `platform_admin`
- `review_operator`
- `viewer`

## 10. 错误处理与日志

### 10.1 错误处理

第二阶段继续沿用统一错误响应风格，管理类接口必须返回明确中文错误信息。

重点覆盖的失败场景：

- 参数校验错误
- 业务状态错误
- 资源不存在
- 权限不足
- 模型测试失败
- 机器人测试失败
- mock 审查导入失败

### 10.2 日志分层

保留两层日志：

- 运行日志：继续使用 Python `logging` 记录服务启动、请求异常、外部调用失败等技术日志
- 操作审计日志：写入 `audit_logs`，用于系统日志页面展示

建议纳入审计的动作：

- 登录、退出、修改密码
- 用户、角色、权限、菜单变更
- 项目新增、编辑、启停
- 项目模板新增、编辑、启停
- 模型新增、编辑、测试、设默认
- 机器人新增、编辑、测试
- mock 审查记录导入

## 11. 前端实现边界

第二阶段前端仅建设最小可用后台壳子，但要保证核心页面能力完整。

建议纳入页面：

- 登录页
- 后台布局页
- 仪表盘
- 项目管理
- 项目模板管理
- 审查记录
- 审查详情
- 成员分析
- 大模型管理
- 通知机器人管理
- 用户管理
- 角色管理
- 系统日志

前端实现要求：

- 基于权限动态展示菜单与页面入口
- 列表页优先还原业务字段与筛选能力
- 详情页优先还原信息结构
- 复杂图表只做轻量版本，不做大屏与深度分析

## 12. 开发执行规范

### 12.1 注释规范

第一阶段提出的注释要求纳入第二阶段强制执行规范：

- 新增或明显重构的核心类必须补充类注释，说明职责、边界和主要依赖
- 新增或明显重构的核心方法必须补充方法注释，说明用途、关键参数、返回值与异常场景
- 对于非直观的业务分支、聚合逻辑、状态流转与安全处理，必须补充必要的行间注释
- 注释应解释“为什么这样做”或“这段逻辑在保障什么”，避免无意义的逐行复述
- 注释语言统一使用中文，必要时可保留英文术语

### 12.2 API 文档规范

- 所有新增 API 必须提供中文 `summary`
- 复杂接口必须补充中文 `description`
- 请求体、响应体与重要字段在 Pydantic schema 中应提供中文说明
- 所有新增接口必须在 Swagger / OpenAPI 中可见且中文描述完整

### 12.3 代码与配置规范

- 继续使用 PostgreSQL 与 Redis 本地开发默认配置
- 所有数据库迁移必须可在 `ai_code_reviewer` 数据库中实际落地
- 敏感信息必须遵循“存储加密、展示脱敏、接口不回传明文”原则
- API、服务、模型、测试命名保持与第一阶段风格一致

## 13. 测试策略

后端测试为主，前端做关键链路验证。

后端测试重点：

- 新增表结构、约束与关联关系
- 项目、模板、模型、机器人状态校验
- mock 审查事件标准化与去重逻辑
- 成员分析聚合逻辑
- 权限拦截
- OpenAPI 中文描述完整性
- 敏感字段不明文回传

前端验证重点：

- 登录后菜单权限展示
- 项目管理与项目模板管理页面的列表、编辑、保存
- 审查记录列表与详情展示
- 模型管理与机器人管理的表单提交流程
- 基础异常提示与表单校验

## 14. 验收标准

第二阶段通过验收至少满足以下条件：

- 管理后台可以完成登录并根据权限展示菜单
- 可以管理项目、项目模板、模型与通知机器人
- 可以通过 mock 接口导入 Push / Merge Request 审查记录
- 审查记录页可以查看列表、详情、commit 信息、原始 webhook 数据与 agent trace
- 成员分析页可以展示基于审查记录的基础聚合结果
- 系统日志页可以查询关键操作审计记录
- 所有新增 API 具备中文 Swagger / OpenAPI 描述
- 新增数据库迁移可以在 `ai_code_reviewer` 数据库中成功执行
- 核心后端测试通过

## 15. 后续兼容预留

尽管第二阶段不做真实 Git 接入，但设计必须为后续扩展保留兼容点：

- 上游事件唯一标识
- webhook 原始数据扩展字段
- 模板快照与提示词快照
- 模型与机器人真实调用链路
- 审查记录与未来 AI 执行链路的关联字段
