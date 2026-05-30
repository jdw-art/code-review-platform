# CodeReview 集成设计文档：统一迁入 FastAPI 后端

## 1. 背景

当前仓库已经完成后台基础能力与第二阶段管理域能力建设，具备以下基础：

- 基于 FastAPI 的后端服务框架
- PostgreSQL 持久化模型与 Alembic 迁移体系
- Redis 基础依赖
- 项目、项目模板、模型、通知机器人、审查记录、成员分析等管理能力
- 审查记录列表、详情、原始数据查看与 mock 导入接口

与此同时，仓库中的 `codereview/` 目录已经具备一套可运行的 AI 自动代码审查系统，核心能力包括：

- 接收 GitLab / GitHub / Gitea webhook
- 拉取 Merge Request / Pull Request / Push 变更
- 调用大模型执行代码审查
- 将审查结果回写到代码托管平台评论区
- 将结果推送到钉钉、企业微信、飞书或自定义 webhook
- 将审查日志写入 SQLite
- 生成日报并提供独立 Streamlit Dashboard

现阶段问题在于：

- 审查执行链路与当前 `backend` 是两套独立系统
- 数据分别落在 SQLite 与 PostgreSQL 中，无法统一统计和治理
- webhook 接入、通知、日报、后台展示没有统一到一个后端体系
- 现有后台虽然已经具备审查记录与统计骨架，但尚未接入真实 Git 平台事件和真实审查执行能力

因此，本阶段目标是将 `codereview/` 的核心审查流程真正集成到当前 `backend` 中，使 webhook、审查执行、结果落库、评论回写、通知、日报与后台展示统一归口到 FastAPI + PostgreSQL 体系。

## 2. 目标

本阶段完成后，系统应当能够：

- 接收 GitLab 与 GitHub 的真实 webhook 事件
- 将 webhook 标准化后写入 PostgreSQL 审查记录
- 通过独立 worker 异步执行审查任务
- 调用大模型完成实际代码审查
- 将审查结果回写到 GitLab / GitHub 对应评论位置
- 将审查结果推送到通知渠道
- 将审查记录、commit 明细、原始 webhook 数据、执行轨迹统一落库到 PostgreSQL
- 继续使用现有管理后台查看审查记录、原始数据、成员分析与仪表盘统计
- 将原 `codereview` 日报能力迁入当前后端体系
- 逐步淘汰 `codereview` 的独立 Flask API、SQLite 与 Streamlit Dashboard

## 3. 范围

本阶段纳入范围：

- GitLab webhook 接入
- GitHub webhook 接入
- Push 事件审查
- Merge Request / Pull Request 事件审查
- 审查任务异步执行
- 审查结果落 PostgreSQL
- 评论回写
- IM 通知
- 日报生成与定时发送
- 审查记录、成员分析、仪表盘数据接入真实审查数据
- 历史 `codereview` 数据导入兼容

## 4. 非目标

本阶段明确不做以下内容：

- Gitea 实时接入
- 凭据改造成项目级数据库配置
- 多租户能力
- Deep Review 多轮对话审查能力
- 多 worker 编排、分布式调度平台化建设
- 长期双写或长期并行运行两套审查系统
- 对原 `codereview` UI 的继续维护

## 5. 关键约束与已确认决策

用户已确认以下设计约束：

- 首期支持平台范围为 `GitLab + GitHub`
- 审查执行采用 `独立 worker 队列` 模式，不在 API 请求中同步完成
- 首期沿用 `codereview` 的环境变量凭据方式，不改造成项目级密钥托管
- 首期目标尽量实现 `codereview` 的全量功能迁移
- `日报` 迁入现有后端体系，原 Streamlit Dashboard 下线，统一使用现有管理台
- spec 文档使用中文

## 6. 集成策略

本阶段采用 `兼容层迁移` 策略，而不是整块搬运或纯重写。

### 6.1 方案说明

兼容层迁移指：

- 保留 `codereview` 中已经过验证的平台适配、变更过滤、评论回写、通知格式等核心业务逻辑
- 在当前 `backend` 中新建统一的 webhook 接入层、任务队列层、worker 执行层与 PostgreSQL 持久化层
- 将原 SQLite 日志沉淀与 Streamlit 展示替换为当前后台中的 PostgreSQL 记录与管理台查询能力

### 6.2 选择原因

采用该方案的原因如下：

- 相比整块搬运，可更好统一到当前 `backend` 的服务结构、数据库体系与后台管理域
- 相比纯重写，可最大程度保留 `codereview` 已验证的实际行为，降低首期回归风险
- 有利于后续逐步替换兼容层内部实现，而不影响外层 FastAPI API、数据库和后台展示

## 7. 总体架构

### 7.1 架构原则

- FastAPI 只负责接收、校验、标准化、入库、入队，不执行长耗时审查
- Worker 独立执行真实审查逻辑
- PostgreSQL 作为唯一长期事实库
- Redis 负责队列、短期锁与幂等辅助
- 管理台继续作为唯一展示面
- 原 `codereview` 独立服务不再作为正式运行单元

### 7.2 目标架构

系统由以下组件组成：

- `FastAPI Webhook API`
- `Redis Queue`
- `Review Worker`
- `Platform Adapters`
- `LLM Review Engine`
- `Comment Delivery`
- `Notification Delivery`
- `Daily Report Scheduler`
- `PostgreSQL`
- `现有后台 API 与前端管理台`

### 7.3 数据流

1. GitLab / GitHub 触发 webhook 到 FastAPI。
2. FastAPI 解析 payload、匹配项目、进行幂等检查。
3. FastAPI 创建 `review_records` 记录并将任务写入 Redis 队列。
4. Worker 消费任务，根据平台类型加载对应 adapter。
5. Adapter 拉取 changes 与 commits。
6. Worker 按模板配置过滤文件、组装 prompt、调用 LLM 审查。
7. Worker 解析评分与审查结论，写入 `review_records` 与 `review_commits`。
8. Worker 回写评论并推送通知。
9. 管理台从 PostgreSQL 查询审查记录、统计、成员分析与日报结果。

## 8. 数据模型设计

### 8.1 主键策略

延续现有约束：

- 所有主键使用 `BIGINT`
- 所有外键使用 `BIGINT`
- Python / Pydantic 层统一使用 `int`
- 不引入 UUID 主键

### 8.2 主数据与外部数据分层原则

本次设计需要明确区分两类标识：

- 平台内主数据 ID
- 外部代码平台标识

原则如下：

- `project_id`、`template_id`、`user_id` 等用于关联当前系统内部主数据
- GitLab / GitHub 的仓库、MR/PR、commit、作者信息作为外部标识与快照保留
- 不将外部作者身份在首期强制绑定到平台内 `users.id`

### 8.3 `projects` 关联规则

`review_records.project_id` 必须关联当前系统的 `projects.id`。

webhook 到达后，系统先通过项目匹配规则定位平台内项目，再写入 `project_id`。不允许直接使用外部仓库 ID 作为平台内项目主键。

项目匹配信息首期来自以下字段：

- `projects.repo_url`
- `projects.settings.external_repo_full_name`
- `projects.settings.gitlab_project_path`
- `projects.settings.external_project_id`

### 8.4 `project_templates` 快照规则

项目当前绑定模板仍由 `projects.template_id` 表示。

但 `review_records` 中不直接依赖实时模板外键，而是保留以下快照字段：

- `template_id_snapshot`
- `template_name_snapshot`
- `review_prompt_snapshot`

原因如下：

- 模板内容后续可能发生变化
- 历史审查记录必须保留审查当时的模板与 prompt
- 不能因为模板被修改而影响历史审查结果的可追溯性

### 8.5 `users` 与提交作者关系

`users.id` 仅代表当前管理平台中的用户、管理员与操作者，不直接代表 Git 平台中的提交人。

首期：

- `review_records.author` 继续保存外部平台作者名字符串
- 成员分析主要通过 `project_members.member_name` 或 `member_email` 与审查记录匹配
- 不要求 `review_records` 直接外键 `users.id`

### 8.6 `review_records`

`review_records` 继续作为统一审查主表，承载单次 webhook 事件对应的审查记录。

现有字段继续保留：

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
- `agent_trace`
- `webhook_data`
- `extra_data`
- `created_at`
- `updated_at`

建议扩展字段：

- `platform_type`
- `delivery_status`
- `external_project_id`
- `external_merge_request_id`
- `external_pull_request_id`
- `external_commit_sha`
- `reviewed_at`
- `failed_at`
- `error_message`
- `retry_count`

### 8.7 `review_records.review_status`

首期将 `review_status` 从简单状态扩展为任务生命周期状态：

- `queued`
- `processing`
- `reviewed`
- `skipped`
- `failed`

状态语义如下：

- `queued`：已接收 webhook，等待 worker 处理
- `processing`：worker 正在执行
- `reviewed`：审查成功完成，结果已落库
- `skipped`：命中跳过条件，不执行完整审查
- `failed`：执行失败，达到终态

### 8.8 `review_records.delivery_status`

新增 `delivery_status` 以描述评论回写和通知投递的结果：

- `pending`
- `delivered`
- `comment_failed`
- `notify_failed`
- `partial_failed`

说明：

- 审查成功但评论或通知失败时，不应将 `review_status` 改成 `failed`
- 投递问题通过 `delivery_status` 表达

### 8.9 `review_commits`

`review_commits` 继续作为审查记录对应的 commit 明细表。

保留现有字段：

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

可选扩展字段：

- `url`
- `additions`
- `deletions`

若首期控制变更范围，可暂不新增结构化字段，将上述扩展内容继续保存在 `payload` 中。

### 8.10 `agent_trace` 与 `extra_data`

`agent_trace` 用于保存执行轨迹和调试信息，例如：

- 使用的 provider / model
- prompt 来源
- token 截断信息
- API 耗时
- 平台拉取信息
- 评论回写结果
- 通知投递结果
- 重试记录

`extra_data` 用于保存未结构化但需要保留的兼容字段，例如：

- 原 `codereview` entity 中暂未单独建字段的信息
- 平台差异较大的扩展属性
- 导入兼容使用的来源标识

## 9. Webhook 接入设计

### 9.1 接口入口

新增统一 webhook 路由：

- `POST /api/v1/integrations/webhooks/gitlab`
- `POST /api/v1/integrations/webhooks/github`

这两个接口不走后台用户鉴权，而是走平台 webhook 校验与项目匹配逻辑。

### 9.2 API 层职责

FastAPI webhook 路由只做以下事情：

- 读取原始 payload 和关键请求头
- 校验事件类型是否受支持
- 提取仓库和事件标识
- 匹配平台内项目
- 完成幂等检查
- 创建或复用 `review_records`
- 将任务写入 Redis 队列
- 立即返回 `202 Accepted`

API 层不执行以下动作：

- 不拉取详细 changes
- 不调用 LLM
- 不回写评论
- 不发送通知

### 9.3 支持事件

GitLab 支持：

- `merge_request`
- `push`

GitHub 支持：

- `pull_request`
- `push`

### 9.4 跳过条件

以下场景直接标记为 `skipped` 或在 webhook 层短路返回：

- draft / work in progress 的 MR / PR
- 事件动作不在受支持范围
- 项目 `review_enabled = false`
- 目标分支不满足受保护分支策略
- webhook 匹配不到有效项目
- payload 结构非法

### 9.5 项目匹配规则

匹配优先级建议如下：

1. `projects.repo_url`
2. `projects.settings.external_repo_full_name` 或 `settings.gitlab_project_path`
3. `projects.settings.external_project_id`

平台字段来源：

GitHub 常用字段：

- `repository.full_name`
- `repository.html_url`
- `repository.id`

GitLab 常用字段：

- `project.web_url`
- `project.path_with_namespace`
- `project.id`

## 10. 幂等与去重设计

### 10.1 设计原则

系统需要同时防止：

- 同一个 webhook 重复到达导致重复入库
- 同一个任务被并发 worker 重复执行

### 10.2 双层去重

采用两层机制：

- PostgreSQL 记录级幂等
- Redis 短期锁

### 10.3 审查记录幂等键

幂等优先级如下：

1. 平台事件唯一 ID
2. `project_id + event_type + external_mr/pr id + last_commit_id`
3. Push 场景下 `project_id + branch + after_sha`

### 10.4 命中既有记录的处理

如果已存在记录：

- 状态为 `queued` 或 `processing`：不重复入队
- 状态为 `reviewed` 或 `skipped`：若并非新的 commit，不重复执行
- 状态为 `failed`：允许重新入队

## 11. 队列与 Worker 设计

### 11.1 队列职责

Redis 队列只保存轻量任务消息，不保存完整业务事实。

任务消息建议只包含：

- `review_record_id`
- `platform_type`
- `attempt`

### 11.2 Worker 职责

Worker 是独立进程，负责：

- 从 Redis 消费任务
- 加载审查记录
- 执行真实审查
- 更新任务状态
- 回写评论
- 推送通知
- 更新执行轨迹与错误信息

### 11.3 Worker 执行步骤

1. 获取任务并锁定对应 `review_record`
2. 将状态更新为 `processing`
3. 根据 `platform_type` 加载 adapter
4. 拉取 changes 与 commits
5. 过滤不关注的文件
6. 根据规则判断是否跳过
7. 组装 prompt
8. 调用 LLM
9. 解析分数与审查结果
10. 持久化 `review_records` 与 `review_commits`
11. 回写 Git 平台评论
12. 发送 IM 通知
13. 更新 `delivery_status`
14. 将 `review_status` 更新为 `reviewed`

### 11.4 失败处理

任一阶段失败时：

- 记录 `error_message`
- 累加 `retry_count`
- 写入 `agent_trace`
- 根据错误类别判断是否重试
- 达到重试上限后写为 `failed`

## 12. 平台适配层设计

### 12.1 设计原则

平台差异全部收敛到 adapter 层，业务主链路只依赖统一接口。

### 12.2 统一接口建议

每个平台 adapter 至少提供以下能力：

- `parse_webhook(payload, headers)`
- `fetch_changes(event, credentials)`
- `fetch_commits(event, credentials)`
- `post_review_comment(event, review_result, credentials)`
- `is_target_branch_protected(event, credentials)`

### 12.3 平台覆盖

首期提供：

- `GitLabAdapter`
- `GitHubAdapter`

后续新增 `GiteaAdapter` 时，不应影响主链路设计。

### 12.4 复用策略

优先复用 `codereview` 中以下成熟逻辑：

- webhook 结构处理
- diff 过滤逻辑
- PR / MR / Push 变更拉取逻辑
- 评论回写逻辑
- 平台相关字段解析

## 13. LLM 审查执行设计

### 13.1 模型选择优先级

Worker 调用模型时采用如下优先级：

1. `project.default_model_id`
2. 系统默认 `llm_models.is_default`
3. `codereview` 风格环境变量配置兜底

### 13.2 Prompt 选择优先级

Prompt 选择优先级如下：

1. `review_records.review_prompt_snapshot`
2. `projects.template.review_prompt_template`
3. `codereview/conf/prompt_templates.yml` 默认模板

### 13.3 配置兼容

首期继续兼容以下环境变量：

- `REVIEW_STYLE`
- `REVIEW_MAX_TOKENS`
- `SUPPORTED_EXTENSIONS`
- `LLM_PROVIDER`
- 各 provider 的 API key、base URL 与 model 变量

### 13.4 执行轨迹记录

LLM 执行过程中需写入以下信息到 `agent_trace`：

- provider
- model_code
- prompt 来源
- token 截断前后数量
- LLM 耗时
- 原始错误摘要

## 14. 评论回写设计

### 14.1 回写原则

审查结果首先写入数据库，再执行评论回写。

原因如下：

- 审查结果是核心事实，必须优先持久化
- 评论回写属于外部投递动作，失败不应导致审查事实丢失

### 14.2 平台行为

GitLab：

- MR 审查结果回写到 MR Note
- Push 结果按现有 `codereview` 能力进行提交相关评论

GitHub：

- PR 审查结果回写到 PR 评论区
- Push 结果按现有 `codereview` 能力进行提交相关评论

### 14.3 状态处理

评论回写失败时：

- `review_status` 仍可保持 `reviewed`
- `delivery_status` 标记为 `comment_failed` 或 `partial_failed`
- 详细错误进入 `agent_trace`

## 15. 通知设计

### 15.1 配置来源

通知渠道配置优先级：

1. `project.default_bot_id`
2. 全局环境变量通知配置兜底

### 15.2 支持渠道

首期支持延续 `codereview` 的能力：

- 钉钉
- 企业微信
- 飞书
- 额外自定义 webhook

### 15.3 模板策略

首期消息格式尽量复用 `codereview` 当前 markdown 模板，保持迁移前后的消息风格一致。

### 15.4 错误处理

通知失败时：

- 审查结果不回滚
- `delivery_status` 更新为 `notify_failed` 或 `partial_failed`
- 错误写入 `agent_trace.notifications`

## 16. 日报设计

### 16.1 数据源

日报数据源统一改为 PostgreSQL 中的 `review_records`。

### 16.2 逻辑对齐

日报逻辑尽量与 `codereview` 保持一致：

- 取当天有效审查记录
- 按 `author + commit_messages` 去重
- 按作者排序与聚合
- 生成开发日报文本

### 16.3 执行方式

日报由后端调度任务执行，不再依赖独立 Flask 应用与 Streamlit。

定时表达式首期兼容：

- `REPORT_CRONTAB_EXPRESSION`

### 16.4 投递方式

日报通过统一通知体系发送，不新增独立消息投递系统。

## 17. 与现有后台的集成方式

### 17.1 审查记录

现有 `review_records` 列表、详情、原始数据接口继续保留，并扩展对以下内容的支持：

- 新的 `review_status`
- `platform_type`
- `delivery_status`
- 错误信息
- 重试次数

### 17.2 成员分析

成员分析继续基于 `review_records` 聚合，但数据来源从 mock 数据升级为真实 webhook 审查数据。

### 17.3 仪表盘

仪表盘继续以 `review_records` 为数据源，后续可逐步增加真实趋势、状态分布、失败率等统计项。

### 17.4 原 Streamlit Dashboard

原 `codereview` 的 Streamlit Dashboard 退出正式运行路径，不再作为主要展示入口。

## 18. 错误处理与重试策略

### 18.1 错误分类

错误分三类：

#### 可重试错误

- Git 平台 API 暂时不可用
- 网络抖动
- LLM 超时或限流
- 评论回写临时失败
- 通知投递临时失败

#### 不可重试错误

- 项目匹配失败
- 凭据缺失
- payload 结构非法
- 平台事件不支持

#### 应跳过错误

- draft PR / MR
- 无受支持文件
- review 被禁用
- 保护分支条件不满足

### 18.2 重试策略

建议：

- 最多重试 3 次
- 使用指数退避
- 每次重试信息写入 `agent_trace`

### 18.3 终态要求

任何任务最终必须落入以下之一：

- `reviewed`
- `skipped`
- `failed`

不允许长期停留在 `processing` 而无补偿机制。

## 19. 历史数据迁移

### 19.1 数据来源

历史 SQLite 数据通过现有 `backend/scripts/import_review_logs.py` 思路迁移。

### 19.2 迁移原则

- 历史数据只做补录，不触发评论回写与通知
- 历史记录默认 `review_status = reviewed`
- 无法结构化的字段继续进入 `webhook_data` 或 `extra_data`

### 19.3 兼容要求

导入后的历史记录必须：

- 能出现在审查记录列表中
- 能查看详情与原始数据
- 能参与成员分析与仪表盘统计

## 20. 测试策略

### 20.1 单元测试

覆盖以下模块：

- webhook payload 解析
- 项目匹配
- 幂等键生成
- 文件过滤
- prompt 选择
- token 截断
- 分数解析
- 跳过逻辑
- 状态迁移逻辑

### 20.2 集成测试

覆盖以下场景：

- webhook 接口写入 `queued`
- worker 将记录推进到 `reviewed / skipped / failed`
- `review_commits` 正确写入
- 后台查询接口可正确读取新数据

### 20.3 平台适配器测试

至少覆盖：

- GitLab merge request
- GitLab push
- GitHub pull request
- GitHub push
- 评论回写请求构造
- 保护分支判断

### 20.4 端到端验证

通过真实或回放 payload 验证完整链路：

- webhook 接收
- 入队
- worker 执行
- LLM 调用
- 评论回写
- 通知推送
- PostgreSQL 落库
- 管理台查询

## 21. 实施顺序

建议按以下顺序实施：

1. 扩展数据库模型与迁移
2. 新增 webhook 路由与标准化事件模型
3. 建立 Redis 队列与独立 worker 基础设施
4. 迁入 GitLab / GitHub adapter
5. 接入真实审查执行链
6. 接入评论回写与通知
7. 接入日报任务
8. 扩展后台查询与筛选能力
9. 补齐测试与历史数据迁移
10. 下线旧 `codereview` 独立运行路径

## 22. 上线与切换策略

### 22.1 切换方式

推荐使用 `短期双轨验证，正式单写切换`：

- 开发阶段：新链路使用回放数据验证
- 预发阶段：真实 webhook 指向新后端，同时保留旧系统回滚能力
- 正式阶段：只保留新链路处理真实事件

### 22.2 不推荐方式

不推荐长期双写，原因如下：

- 容易重复评论
- 容易重复通知
- 容易导致统计口径分叉

### 22.3 回滚要求

正式切换前应准备：

- 环境变量清单
- Redis 与 PostgreSQL 启动与健康检查方案
- worker 启动脚本
- 示例 payload 回放脚本
- 回滚步骤说明

## 23. 验收标准

本阶段完成后，以下条件全部满足方可视为验收通过：

- GitLab `merge_request` 与 `push` 事件可真实跑通
- GitHub `pull_request` 与 `push` 事件可真实跑通
- 审查记录统一写入 PostgreSQL
- Worker 可稳定推动状态流转 `queued -> processing -> reviewed/skipped/failed`
- 审查结果可成功回写到对应评论位置
- IM 通知可成功发送
- 日报可定时生成与发送
- 管理台可查看真实审查记录、原始数据、成员分析与仪表盘统计
- 原 `codereview` SQLite 与 Streamlit Dashboard 不再是正式依赖
- 历史数据可导入且不破坏现有后台查询
- 失败场景可定位、可重试、可观测

## 24. 后续演进方向

本阶段完成后，后续可继续演进：

- 将仓库凭据与 webhook secret 下沉为项目级数据库配置
- 增加 Gitea adapter
- 为 review 执行增加更强的任务编排和调度能力
- 增加更细粒度的 delivery、retry 与监控指标
- 提供 webhook 重放与失败任务重试后台操作
- 增加真实日报查看与审查趋势可视化页面
