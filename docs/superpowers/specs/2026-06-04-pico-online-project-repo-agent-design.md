# Pico Online 项目级仓库对话助手设计

## 1. 背景

当前仓库已经具备以 AI Code Review 为核心的平台主链路：FastAPI 后端、PostgreSQL 持久化、Redis 队列、review worker、GitHub/GitLab webhook、审查记录、评论回写、通知与管理台。

与此同时，`pico/` 目录中存在一套轻量本地 coding agent。它的核心价值不是 CLI 外壳，而是围绕本地代码仓库形成的一套 agent 运行模型：

- 基于当前仓库生成稳定的 workspace context。
- 通过受约束工具按需读取仓库信息。
- 使用 `ContextManager` 控制 prompt 结构、预算与裁剪顺序。
- 使用 `LayeredMemory` 保留工作记忆、文件摘要与过程笔记。
- 将 session、run、trace、report 等运行状态持久化到 `.pico/`。
- 在工具执行链路中做工具存在性检查、参数校验、重复调用拦截、脱敏与记忆更新。

本设计目标是把 `pico` 迁移为线上代码审查平台中的“项目级仓库对话助手”，形成类似 ChatGPT / Claude 的持续对话体验，让团队成员可以围绕项目仓库、锁定分支和相关 PR/MR 上下文持续提问、定位模块、理解调用链和降低协作理解成本。

## 2. 目标

本阶段目标如下：

- 在已有 `projects` 体系下新增项目级仓库对话助手。
- 第一版产品形态为独立的 `Project Repo Agent` 页面。
- 创建会话时只选择一个分支，session 生命周期内锁定到该分支。
- 保留 `pico` 的核心设计，包括上下文结构、记忆结构、只读工具执行网关、run state、trace、artifact、workspace fingerprint 思路。
- 将本地文件系统访问替换为 GitHub/GitLab API 与轻量仓库快照。
- 提供只读仓库工具与 PR/MR 元信息工具，不允许写仓库或执行 shell。
- 将 `.pico/` 本地 session 与 artifacts 持久化替换为 PostgreSQL。
- 提供 session、message、run、event、artifact、snapshot 等平台数据模型。
- 提供 SSE 对话流，让前端能够展示 assistant delta、工具状态和最终回答。

## 3. 非目标

本阶段明确不做以下内容：

- 不做线上 shell 执行。
- 不做文件写入、patch 生成、自动提交、自动评论或自动发起 PR/MR 修改。
- 不开放 `delegate` 子 agent。
- 不做 `pico` 的 CLI / REPL 体验迁移。
- 不做完整 RAG、embedding、向量库和跨仓库语义检索。
- 不做多分支热切换或同一 session 下切换 ref。
- 不做 checkpoint / resume 的完整线上化。
- 不做复杂的管理台 trace 可视化后台。
- 不替换现有 review pipeline；`Repo Agent` 与现有 code review 能力并列存在。

## 4. 已确认决策

本设计基于以下已确认方向：

- 产品形态是“项目级仓库对话助手”，不是自动改代码助手。
- 页面入口采用独立页面，而不是先挂在现有项目详情页 tab 中。
- session 创建时只选择分支，不选择 tag 或 commit。
- session 锁定分支，但每次 run 记录实际运行时的 `head_sha`。
- 第一版索引策略为“轻量快照 + 按需读取”，保持 `pico` 现有设计精神。
- 仓库代码与元信息通过 GitHub/GitLab API 获取，而不是第一期 clone 本地 workspace。
- 工具层只保留只读工具，并保留统一工具执行网关。
- 工具层在参数校验、重复调用拦截之外，增加统一敏感信息脱敏。
- 上下文层保留 `pico` 的 prompt section、预算与裁剪顺序。
- 记忆层保留 `pico` 的 layered memory 结构，session memory 以 JSON 落库。
- run / event / artifact 采用“关键索引字段结构化 + 详细内容 JSON 化”的持久化策略。
- `workspace_fingerprint` 与 `runtime_identity_hash` 分层保留，不混成单一状态字段。
- Repo Agent 不单独实现一套 LLM provider/config，而是与 code review 共用一层抽取后的共享 LLM 基础层。
- 第一版 LLM 配置与 code review 保持一致，直接读取 `.env` 中的环境变量，例如：
  - `LLM_PROVIDER=openai`
  - `OPENAI_API_KEY=api-key`
  - `OPENAI_API_BASE_URL=https://xxx/v1`
  - `OPENAI_API_MODEL=gpt-5.4`

## 5. 总体方案

采用“保留 `pico` 核心运行模型，替换本地边界为平台适配层”的方案。

`pico` 不直接以 CLI runtime 形式嵌入 FastAPI，而是拆成两层：

- `pico-core`
  - `ContextManager`
  - `LayeredMemory`
  - read-only `ToolRegistry`
  - `ToolGateway`
  - run state
  - prompt protocol
  - workspace identity logic
- `platform adapter`
  - PostgreSQL session / run / event / artifact store
  - GitHub/GitLab `RepositoryProvider`
  - lightweight `RepositorySnapshotService`
  - FastAPI routes
  - SSE event stream
  - RBAC 与审计
  - shared LLM config / client adapter

这样可以最大程度保留 `pico` 的 agent 行为，同时满足线上平台对权限、流式输出、持久化、脱敏与仓库隔离的要求。

## 6. 目标架构

目标架构如下：

```text
Frontend Project Repo Agent Page
  -> Agent Session API
  -> Agent Message API
  -> Agent SSE Stream

FastAPI Agent Domain
  -> AgentSessionService
  -> AgentMessageService
  -> AgentRunService
  -> AgentToolGateway
  -> AgentEventRecorder
  -> RepositorySnapshotService

Pico-derived Core
  -> ContextManager
  -> LayeredMemory
  -> WorkspaceContextBuilder
  -> ToolRegistry
  -> RuntimeIdentityBuilder
  -> AgentModelClient

Shared LLM Layer
  -> load_llm_config
  -> build_llm_client

Repository Providers
  -> GitHubRepositoryProvider
  -> GitLabRepositoryProvider

Persistence
  -> agent_sessions
  -> agent_messages
  -> agent_runs
  -> agent_run_events
  -> agent_artifacts
  -> repository_snapshots
```

## 7. 保留与替换范围

### 7.1 保留

保留以下 `pico` 设计：

- `ContextManager` 的 prompt section 结构、budget、history 裁剪、relevant memory 选择逻辑。
- `WorkspaceContext` 的“稳定仓库第一印象”思路。
- `LayeredMemory` 的 `working memory`、`recent files`、`file summaries`、`episodic notes` 结构。
- `ToolRegistry` 的工具白名单、schema 校验、`risky` 标记与统一执行出口。
- `TaskState` 的 run 状态语义。
- `trace.jsonl` 的事件流思路与 `report.json` 的结构化运行工件思路。
- 工具执行链路中的重复工具调用拦截。
- 基于内容 freshness 使文件记忆失效的设计。
- prompt / workspace / runtime identity 的分层身份设计。

### 7.2 替换

替换以下本地边界：

- 本地文件系统读取替换为 `RepositoryProvider`。
- 本地 `.pico/sessions/*.json` 替换为 `agent_sessions` 与 `agent_messages`。
- 本地 `.pico/runs/<run_id>/` 替换为 `agent_runs`、`agent_run_events` 与 `agent_artifacts`。
- CLI / REPL 同步输出替换为 FastAPI API 与 SSE。
- 本地 workspace snapshot 替换为基于项目、分支、`head_sha`、轻量快照和工具签名的线上 workspace context。
- 本地 secret env 脱敏扩展为平台配置密钥与仓库内容统一脱敏。
- 本地 `pico` 自带 model client 配置入口替换为平台共享的 LLM 配置解析与客户端构建逻辑，并从 `review` 业务域中解耦出来。

### 7.3 暂缓

暂缓以下能力：

- `run_shell`
- `write_file`
- `patch_file`
- `delegate`
- checkpoint
- resume
- 完整 RAG
- 向量检索
- clone workspace
- 多分支热切换
- 可视化 memory 编辑器

## 8. 数据模型设计

### 8.1 `agent_sessions`

表示一个项目下的一条持续对话，对应 `pico` 的 session。

字段建议：

- `id`
- `project_id`
- `created_by`
- `title`
- `status`: `active`, `archived`
- `branch`
- `provider`
- `model`
- `last_head_sha`
- `last_workspace_fingerprint`
- `last_runtime_identity_hash`
- `memory_state`: JSON
- `settings`: JSON
- `last_message_at`
- `created_at`
- `updated_at`

`memory_state` 第一版直接保留 `pico.memory.default_memory_state()` 的结构，并允许在 `file_summaries` 中补充平台语义字段。

### 8.2 `agent_messages`

表示用户和助手可见消息。它服务 UI 展示，不承载完整运行 trace。

字段建议：

- `id`
- `session_id`
- `run_id`
- `role`: `user`, `assistant`, `system`
- `content`
- `content_format`: `text`, `markdown`
- `status`: `pending`, `streaming`, `completed`, `failed`
- `sequence`
- `metadata`: JSON
- `created_at`

### 8.3 `agent_runs`

表示一次用户请求触发的一轮 agent 执行，对应 `pico` 的一次 `ask()` 运行。

结构化字段建议：

- `id`
- `session_id`
- `project_id`
- `user_message_id`
- `assistant_message_id`
- `status`: `running`, `completed`, `stopped`, `failed`, `cancelled`
- `stop_reason`
- `tool_steps`
- `attempts`
- `last_tool`
- `branch`
- `head_sha`
- `workspace_fingerprint`
- `runtime_identity_hash`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

JSON 字段建议：

- `prompt_metadata`
- `completion_metadata`
- `report_payload`

### 8.4 `agent_run_events`

表示 run 的事件流，对应 `trace.jsonl`，也是 SSE 回放来源。

结构化字段建议：

- `id`
- `run_id`
- `session_id`
- `event_type`
- `sequence`
- `created_at`

JSON 字段建议：

- `payload`

事件类型建议至少包括：

- `run_started`
- `snapshot_resolved`
- `assistant_delta`
- `tool_called`
- `tool_result`
- `memory_invalidated`
- `final_answer`
- `run_failed`

### 8.5 `agent_artifacts`

表示 run 的结构化工件，对应 `report.json` 与其他运行产物。

字段建议：

- `id`
- `run_id`
- `session_id`
- `artifact_type`
- `name`
- `content`: JSON 或 TEXT
- `metadata`: JSON
- `created_at`

第一版建议保留这些 artifact 类型：

- `task_state`
- `prompt_context`
- `run_report`
- `snapshot_summary`
- `memory_delta`

### 8.6 `repository_snapshots`

表示轻量仓库快照，对应线上版 `WorkspaceContext`。

字段建议：

- `id`
- `project_id`
- `branch`
- `head_sha`
- `workspace_fingerprint`
- `snapshot_digest`
- `file_tree_summary`: JSON
- `project_docs_summary`: JSON
- `recent_commits_summary`: JSON
- `metadata`: JSON
- `created_at`

## 9. Repository Provider 设计

当前仓库里的 `GitHubIntegrationAdapter` 与 `GitLabIntegrationAdapter` 主要服务于 webhook、diff、commits 与评论回写，不能直接满足项目级仓库对话工具需求。因此本设计新增面向 agent 的 `RepositoryProvider` 抽象，而不是直接把现有 adapter 扩展成一切能力都混在一起的接口。

建议新增以下能力：

- `resolve_branch_head(project, branch) -> head_sha`
- `build_snapshot(project, branch, head_sha) -> snapshot summary`
- `list_tree(project, branch, path=".")`
- `read_file(project, branch, path, start, end)`
- `search_code(project, branch, query, path=".")`
- `get_change_summary(project, external_id)`
- `list_commits(project, external_id)`
- `list_comment_threads(project, external_id)`
- `get_diff_overview(project, external_id)`

这样可以保留现有 review integration 代码作为 review pipeline 专用层，同时为 `Repo Agent` 引入更清晰的只读仓库访问边界。

## 10. 上下文设计

### 10.1 Prompt Section 结构

线上版尽量按 `pico` 现有 section 结构原样保留：

- `prefix`
- `memory`
- `relevant_memory`
- `history`
- `current_request`

最重要的约束如下：

- 当前用户请求永远不裁剪。
- `prefix`、`memory`、`history` 仍然是不同职责的 section，不混写。
- `relevant_memory` 只放少量最相关记忆，不把全部记忆重复塞回 prompt。

### 10.2 预算与裁剪顺序

第一版默认沿用 `pico` 的预算策略：

- `total_budget = 12000`
- `prefix = 3600`
- `memory = 1600`
- `relevant_memory = 1200`
- `history = 5200`

超预算时的收缩顺序也沿用 `pico`：

1. `relevant_memory`
2. `history`
3. `memory`
4. `prefix`

### 10.3 Platform Prefix

线上版 `prefix` 不再来自本地 git / workspace，而是由以下平台事实组成：

- Agent 身份与规则
  - 你是项目级只读仓库助手
  - 只能调用白名单工具
  - 只能围绕当前项目与锁定分支工作
  - 不得虚构工具结果
- 工具说明
- Workspace 基线
  - `project_id`
  - `platform_type`
  - `branch`
  - `head_sha`
  - `default_branch`
- 轻量快照摘要
- 项目文档摘要
- 最近提交摘要
- 可选 PR/MR 锚点信息

### 10.4 History 设计

`history` 仍然是压缩后的运行历史，而不是数据库里的完整聊天 transcript 全量回灌。

保留以下 `pico` 风格：

- 最近几轮保留更多细节。
- 更早的消息使用更严格裁剪。
- 旧的 `read_file` 结果按路径去重。
- 工具结果只放裁剪后的文本，不直接塞原始大 payload。

## 11. 记忆设计

### 11.1 Layered Memory 结构

第一版保留这些记忆层次：

- `working.task_summary`
- `working.recent_files`
- `episodic_notes`
- `file_summaries`

记忆不改造成“大段摘要”，仍然保持 `pico` 的 layered memory 结构。

### 11.2 `file_summaries`

`file_summaries` 是第一版最关键的记忆层，用于减少重复读文件。

建议每条 file summary 至少包含：

- `path`
- `summary`
- `branch`
- `head_sha`
- `file_version`
- `updated_at`
- `source`

这里 `file_version` 优先使用远端仓库能够提供的文件版本标识；拿不到时退化为文件内容 hash。

### 11.3 `task_summary`

`working.task_summary` 表示当前会话的主线摘要，而不是整条会话永久总结。它应记录：

- 当前讨论主题
- 已确认的重要结论
- 仍未解决的问题

### 11.4 `episodic_notes`

`episodic_notes` 用于保留过程性事实，只保存后续大概率会复用的小结论，不把原始大段材料直接进入记忆。

### 11.5 Relevant Memory

`relevant_memory` 继续使用 `pico` 风格的轻量召回，而不是第一版就引入 embedding：

- 关键词重叠
- 路径重叠
- topic/tag 命中
- recency

### 11.6 PR/MR 元信息与记忆

PR/MR 原始材料不直接长期塞进 `memory_state`。第一版只把提炼后的少量稳定结论沉淀进 `episodic_notes`，例如：

- 当前会话绑定到某个 PR/MR。
- 本次变更主要涉及哪些模块。
- 评论线程中已经出现过哪些关键争议点。

原始 PR/MR 内容仍通过工具按需读取。

## 12. Freshness 与漂移处理

session 锁定的是分支，而不是静态 commit；因此分支推进属于正常现象。

每次 run 开始时必须执行：

1. 解析当前分支最新 `head_sha`
2. 构建或复用该 `head_sha` 对应的轻量 snapshot
3. 对 `memory.file_summaries` 做 freshness 校验

校验规则如下：

- 如果 `path` 在当前快照中不存在，则对应 file summary 失效。
- 如果 `path` 存在但 `file_version` 变化，则对应 file summary 失效。
- 如果 `head_sha` 变化但该文件 `file_version` 未变化，则 summary 可以继续复用。

这样可以保留 `pico` 的“只让变脏的那部分记忆失效”的设计，而不是分支一前进就清空整条 session。

失效后执行两个动作：

- 从可注入 prompt 的 memory 内容里移除失效 file summary。
- 在 `agent_run_events` 中记录结构化事件，例如：
  - `memory_invalidated`
  - `stale_paths`
  - `old_head_sha`
  - `new_head_sha`

## 13. 工具集与 Tool Gateway

### 13.1 第一版工具集

仓库工具：

- `list_files(path=".")`
- `read_file(path, start=1, end=200)`
- `search_code(query, path=".")`
- `read_project_doc(name)`

PR/MR 元信息工具：

- `get_change_summary(external_id)`
- `list_commits(external_id)`
- `list_comment_threads(external_id)`
- `get_diff_overview(external_id)`

### 13.2 Tool Registry

延续 `pico` 当前设计，每个工具都具备：

- 工具名
- schema
- 描述
- `risky` 标记

第一版所有工具均为只读工具，默认 `risky=False`，但不等于无治理。

### 13.3 LLM 输出协议

线上版沿用 `pico` 当前的输出协议，模型在每一轮推理后只能返回以下两种结果之一：

- 一个 `<tool>...</tool>`
- 一个 `<final>...</final>`

不允许在同一轮输出中混写自然语言说明、多个工具调用、多个 `<final>`，或者把解释文字包在工具调用标签之外。

第一版保留 `pico` 的 JSON 工具调用格式：

```xml
<tool>{"name":"tool_name","args":{"key":"value"}}</tool>
```

由于第一版不开放 `write_file`、`patch_file` 等多行写入工具，因此不需要启用 `pico` 本地版中为多行写操作准备的 XML 特殊格式；线上版只保留 JSON 工具调用格式即可。

最终回答必须使用：

```xml
<final>your answer</final>
```

该协议对应的约束如下：

- 每轮输出必须且只能包含一个顶层动作。
- 工具名必须命中 `ToolRegistry` 白名单。
- `args` 必须是 JSON object。
- 必填参数不能为空。
- 空的 `<final>` 视为无效输出。
- 模型不得虚构工具结果或跳过工具直接声称“已经读取了仓库”。

运行时解析策略也尽量贴近 `pico`：

- 优先解析 `<tool>...</tool>`。
- 若未命中合法工具输出，再解析 `<final>...</final>`。
- 如果模型返回格式非法、工具 JSON 损坏、缺少工具名、缺少必填参数或 `<final>` 为空，则本轮记为 malformed response，并返回一条 retry notice 给模型，要求其重新输出合法协议。
- 连续多次 malformed response 后，run 按失败或重试上限处理，并写入 `agent_run_events` 与 `report_payload`。

因此，线上版的 prompt prefix 中也必须明确写入与 `pico` 一致的协议说明，包括：

- 必须使用工具而不是猜测仓库内容。
- 必须返回且只返回一个 `<tool>` 或 `<final>`。
- 工具调用的 JSON 格式示例。
- 最终回答的 `<final>` 格式示例。
- 不得重复相同工具调用。
- 不得对未执行的工具结果进行臆测。

### 13.4 LLM 调用方式

Repo Agent 的 LLM 调用不单独实现新的 provider 体系，而是与 code review 共用一层抽取后的共享 LLM 基础层。

第一版约束如下：

- Repo Agent 与 code review 共用 `LLM_PROVIDER` 配置入口。
- Repo Agent 与 code review 共用 provider-specific 环境变量。
- 第一版不在 session 级别开放自定义 provider、API base URL 或 model。
- `agent_sessions.provider` 与 `agent_sessions.model` 仅记录本次会话创建时的有效配置快照，不作为独立配置源。

第一版建议将当前 code review 已在使用的通用能力抽到共享层：

- `backend/app/llm/provider.py`
  - `load_llm_config()`
- `backend/app/llm/client_factory.py`
  - `build_llm_client(...)`

`code review` 和 `Repo Agent` 都依赖这层共享 LLM 基础层，而不是让 `Repo Agent` 直接 import `backend/app/review/reviewer/backend_reviewer.py` 之类的 review 业务代码。

其中 `.env` 配置方式与现有 code review 完全一致，例如：

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=api-key
OPENAI_API_BASE_URL=https://xxx/v1
OPENAI_API_MODEL=gpt-5.4
```

在运行时，`RunService` 的模型调用链路如下：

1. `ContextManager` 组装 prompt。
2. `RunService` 调用共享的 `build_llm_client(load_llm_config())` 生成客户端。
3. 通过统一的 `complete()` 或等价封装向模型发起请求。
4. 拿到原始文本后按 Pico 协议解析成 `<tool>` 或 `<final>`。

这样既能避免平台中出现“code review 一套 LLM provider，Repo Agent 又一套 provider”的重复实现，也能避免 `Repo Agent` 在模块边界上直接耦合到 review 业务代码。

### 13.5 Tool Gateway 执行顺序

Tool Gateway 建议保留 `pico` 风格的统一执行出口：

1. 检查工具是否存在
2. 校验参数 schema
3. 做 path / id / branch 约束
4. 拦截重复相同调用
5. 调用 Repository Provider
6. 统一脱敏
7. 裁剪与标准化结果
8. 写入 trace
9. 更新 memory / history
10. 将结果返回给模型

### 13.6 脱敏

敏感信息脱敏作为 Tool Gateway 的硬约束，覆盖：

- 平台配置中的 token / secret / password / webhook secret
- 仓库内容中的常见密钥形态
- PR/MR 评论线程中的敏感文本

默认原则：

- 模型看到的是脱敏后的结果
- trace / artifact 落库的也是脱敏后的结果
- 默认不保留未脱敏副本

### 13.7 执行边界

第一版明确限制：

- 不允许自由 HTTP 访问
- 不允许 shell
- 不允许写仓库
- 不允许切换 session 锁定分支
- 不允许读取项目外仓库
- 不允许单次返回过大文本
- 设置单轮工具步数上限、单次文件读取行数上限、单次搜索返回条数上限、总代码上下文预算上限

## 14. Run State / Trace / Artifact

本设计不把全部过程细节强行拆成大量 ORM 字段，而是采用“索引字段结构化、详细内容 JSON 化”的策略。

### 14.1 Run State

`agent_runs` 用结构化字段保存：

- `status`
- `stop_reason`
- `tool_steps`
- `attempts`
- `last_tool`
- `branch`
- `head_sha`
- `workspace_fingerprint`
- `runtime_identity_hash`
- `started_at`
- `finished_at`

其余如 `prompt_metadata`、`completion_metadata`、`report_payload` 保留 JSON。

### 14.2 Trace

`agent_run_events` 负责保存逐事件时间线。事件结构统一为：

- `event_type`
- `sequence`
- `payload`

这样既能支撑 SSE，也能后续回放与调试。

### 14.3 Artifacts

`agent_artifacts` 负责保存结构化运行产物，如：

- 本轮 task state
- prompt 组装摘要
- snapshot 摘要
- run report
- memory delta

## 15. Workspace Fingerprint 与 Runtime Identity

线上版需要区分两层身份，而不是只保留一个 fingerprint。

### 15.1 `workspace_fingerprint`

描述当前这次运行看到的仓库上下文，建议由以下因素组成：

- `project_id`
- `platform_type`
- `branch`
- `head_sha`
- `default_branch`
- `snapshot_digest`
- `project_docs_digest`
- `recent_commits_digest`

它对应 `pico` 里的 workspace snapshot identity。

### 15.2 `runtime_identity_hash`

描述当前这次运行的工具与配置身份，建议由以下因素组成：

- `workspace_fingerprint`
- `tool_signature`
- `model`
- `feature_flags`
- `max_steps`
- `max_new_tokens`
- `read_only=true`

这样可以复用 `pico` 中“workspace identity + tool signature + runtime settings”共同决定上下文身份的设计。

## 16. 会话流转

一次典型流程如下：

1. 用户进入项目级 `Repo Agent` 页面。
2. 用户选择一个分支并创建 session。
3. 后端创建 `agent_session`，初始化 `memory_state`。
4. 用户发送消息。
5. 后端解析该分支当前最新 `head_sha`。
6. 构建或复用 `repository_snapshot`。
7. 对 `memory.file_summaries` 做 freshness 校验。
8. 基于 snapshot、memory、history 和当前请求组装 prompt。
9. agent 进入多步只读运行，按需调用仓库工具与 PR/MR 元信息工具。
10. 每次工具调用先经过脱敏、裁剪，再写入 events、history、memory 和 artifacts。
11. 运行结束后写回 assistant message、run summary、artifacts，并更新 session 的 `last_head_sha`、`last_workspace_fingerprint`、`last_runtime_identity_hash` 和 `memory_state`。

## 17. 前端交互与 SSE

### 17.1 页面

采用独立页面：

- 路由建议：`/projects/:projectId/agent`

页面主要由三部分组成：

- session 列表
- 当前会话消息流
- 输入框与运行状态

### 17.2 创建会话

创建会话时只选择分支，不暴露 tag / commit 选择，也不在第一版暴露高级 agent 参数。

### 17.3 消息体验

主消息流只展示：

- 用户消息
- assistant 最终回答
- 轻量系统状态

工具细节、trace 状态与本轮运行信息以可展开详情形式展示，而不是铺在主消息正文里。

### 17.4 SSE 事件

前端主要消费两类 SSE 信息：

- `assistant_delta`
- `run_event`

建议至少支持：

- `run_started`
- `snapshot_resolved`
- `tool_called`
- `tool_result`
- `assistant_delta`
- `final_answer`
- `run_failed`

### 17.5 本轮详情

每轮 assistant 回答可展开查看：

- 本轮 `branch`
- 本轮 `head_sha`
- 读取了哪些文件
- 调用了哪些工具
- 是否发生 memory invalidation
- 本轮完成状态

### 17.6 分支漂移反馈

如果本轮运行前分支已经前进，前端要明确展示，例如：

- `branch advanced from abc123 to def456`

避免用户误以为整条会话一直围绕静态代码版本。

## 18. 测试与验证

第一版至少需要覆盖以下层次：

- `ContextManager` 的 prompt section 与预算裁剪测试
- `LayeredMemory` 的结构、更新与 freshness 失效测试
- `RepositoryProvider` 的 GitHub/GitLab 行为测试
- `ToolGateway` 的参数校验、重复调用拦截、脱敏与结果裁剪测试
- `RunService` 的事件流与 artifact 产出测试
- `agent API` 的 session/message/run/SSE 集成测试
- 前端 `Repo Agent` 页面基本交互测试

除此之外，建议补充一条真实链路验证：

- 连接一个测试项目
- 创建分支锁定 session
- 发起多轮连续提问
- 验证 branch 漂移、memory invalidation、tool trace 与 SSE 输出是否符合预期

## 19. 风险与后续演进

第一版主要风险包括：

- GitHub/GitLab API 限流与权限不足
- 大仓库下 `search_code` 与 snapshot 成本过高
- 分支持续推进时，用户对“会话稳定性”和“代码版本变化”之间的预期不一致
- PR/MR 评论线程与仓库文件上下文混用时，prompt 膨胀较快

后续演进方向建议如下：

- 增加更精细的 snapshot cache
- 引入 durable memory 的平台化管理
- 为大仓库补充分层索引
- 增加管理台 trace / artifact 浏览能力
- 在能力稳定后，再考虑项目详情页内嵌入口
