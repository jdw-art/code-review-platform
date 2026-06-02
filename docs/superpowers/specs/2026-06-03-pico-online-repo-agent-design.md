# Pico Online 仓库理解助手设计

## 1. 背景

当前仓库已经具备以 AI Code Review 为核心的平台主链路：FastAPI 后端、PostgreSQL 持久化、Redis 队列、review worker、GitHub/GitLab webhook、审查记录、评论回写、通知与管理台。

与此同时，`pico/` 目录中存在一套轻量本地 coding agent。它的核心价值不是 CLI 外壳，而是围绕本地代码仓库形成的一套 agent 运行模型：

- 基于当前仓库生成稳定的 workspace context。
- 通过受约束工具按需读取仓库信息。
- 使用 context manager 控制 prompt 结构与预算。
- 使用 layered memory 保留工作记忆、文件摘要与跨轮笔记。
- 将 session、run、trace、report 等运行状态持久化到 `.pico/`。
- 在工具执行链路中做工具存在性检查、参数校验、重复调用拦截、审批、执行与记忆更新。

本设计目标是把 `pico` 迁移为线上代码审查平台中的“项目级仓库理解助手”，形成类似网页版 ChatGPT/Claude 的持续对话体验，让团队成员可以围绕复杂仓库持续提问、定位模块、理解调用链和降低协作理解成本。

## 2. 目标

本阶段目标如下：

- 在已有 `projects` 体系下新增项目级仓库助手。
- 保留 `pico` 的大部分核心设计，包括上下文结构、记忆结构、只读工具执行网关、run state 与 trace 思路。
- 将本地文件系统访问替换为 GitHub/GitLab API 与轻量仓库快照。
- 将 `.pico/` 本地 session 与 artifacts 持久化替换为 PostgreSQL。
- 提供 session、message、run、event、artifact、snapshot 等平台数据模型。
- 提供 SSE 对话流，让前端能够展示 assistant delta、工具事件、最终回答和错误。
- 第一版只做仓库理解，不执行 shell、不写文件、不 patch、不生成 PR/MR 修改。

## 3. 非目标

本阶段明确不做以下内容：

- 不做完整 RAG、embedding、向量库和跨仓库语义检索。
- 不做线上 shell 执行。
- 不做文件写入、patch 生成、自动提交或自动评论。
- 不做 `pico` 的 resume/checkpoint 机制。
- 不开放 `delegate` 子 agent。
- 不做多分支长期索引管理。
- 不重做现有 review pipeline。
- 不把 review worker 替换为对话 agent。

## 4. 已确认决策

本设计基于以下已确认方向：

- 第一版产品形态是“仓库理解助手”，不是 PR/MR 修改助手。
- 第一版索引策略为“轻量索引 + 按需读取”，保持 `pico` 现有设计精神。
- 仓库代码与元信息通过 GitHub/GitLab API 获取，而不是在第一期 clone 本地 workspace。
- 工具层只保留只读工具，但保留执行网关基本行为。
- 上下文层保留 workspace fingerprint、prompt section 与 context budget 思路。
- 记忆层保留 `pico` 原设计，session memory 先以 JSON 落库。
- 持久化层由本地文件改为数据库。
- 第一版不做 resume 与 checkpoint。

## 5. 总体方案

采用“保留 `pico` 内核，替换平台边界”的方案。

`pico` 不直接以 CLI runtime 形式嵌入 FastAPI，而是拆成两层：

- `pico-core`
  - context manager
  - layered memory
  - read-only tool registry
  - tool execution gateway
  - run state
  - prompt protocol
  - model client interface
- `platform adapter`
  - PostgreSQL session/run/artifact store
  - GitHub/GitLab repository content provider
  - FastAPI routes
  - SSE event stream
  - RBAC 与审计
  - repository snapshot service

这样可以最大程度保留 `pico` 的 agent 行为，同时满足线上平台对权限、审计、流式输出、持久化和仓库隔离的要求。

## 6. 目标架构

目标架构如下：

```text
Frontend Project Agent Page
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
  -> ModelClient

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
- `WorkspaceContext` 的稳定仓库第一印象思路。
- `LayeredMemory` 的 working memory、recent files、file summaries、episodic notes、durable memory 结构。
- `ToolRegistry` 的工具白名单、schema 校验、risky 标记、统一执行出口。
- `TaskState` 的 run 状态语义。
- `trace.jsonl` 的运行事件记录思路。
- 工具执行链路中的重复工具调用拦截。

### 7.2 替换

替换以下本地边界：

- 本地文件系统读取替换为 `RepositoryContentProvider`。
- 本地 `.pico/sessions/*.json` 替换为 `agent_sessions` 与 `agent_messages`。
- 本地 `.pico/runs/<run_id>/` 替换为 `agent_runs`、`agent_run_events` 与 `agent_artifacts`。
- CLI 同步输出替换为 FastAPI API 与 SSE。
- 本地 workspace fingerprint 替换为基于项目、仓库 ref、head sha、snapshot、工具签名和设置 hash 的平台 fingerprint。

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

## 8. 数据模型设计

### 8.1 `agent_sessions`

表示一个项目下的一条持续对话，对应 `pico` 的 session。

字段建议：

- `id`
- `project_id`
- `created_by`
- `title`
- `status`: `active`, `archived`
- `provider`
- `model`
- `workspace_fingerprint`
- `snapshot_id`
- `memory_state`: JSON
- `settings`: JSON
- `last_message_at`
- `created_at`
- `updated_at`

`memory_state` 第一版直接保留 `pico.memory.default_memory_state()` 的结构。

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

表示一次用户请求触发的一轮 agent 执行，对应 `TaskState`。

字段建议：

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
- `final_answer`
- `prompt_metadata`: JSON
- `completion_metadata`: JSON
- `workspace_fingerprint`
- `snapshot_id`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

### 8.4 `agent_run_events`

表示 run 的事件流，对应 `trace.jsonl`，也是 SSE 回放来源。

字段建议：

- `id`
- `run_id`
- `session_id`
- `event_type`: `run_started`, `assistant_delta`, `tool_start`, `tool_result`, `assistant_message`, `final`, `error`, `snapshot_status`
- `sequence`
- `payload`: JSON
- `created_at`

第一版建议入库前统一脱敏，不维护 `payload` 与 `redacted_payload` 双份结构。

### 8.5 `agent_artifacts`

表示 run 的结构化工件，对应 `report.json` 与其他运行产物。

字段建议：

- `id`
- `run_id`
- `session_id`
- `artifact_type`: `task_state`, `prompt_context`, `run_report`, `tool_cache`
- `name`
- `content`: JSON 或 TEXT
- `metadata`: JSON
- `created_at`

prompt 原文可能包含敏感代码，第一版只在 debug 配置开启时保存。

### 8.6 `repository_snapshots`

表示轻量仓库快照，对应线上版 `WorkspaceContext`。

字段建议：

- `id`
- `project_id`
- `platform_type`
- `repo_url`
- `ref`
- `head_sha`
- `fingerprint`
- `status`: `pending`, `ready`, `failed`, `stale`
- `file_tree`: JSON
- `overview`: JSON 或 TEXT
- `recent_commits`: JSON
- `indexed_paths`: JSON
- `error_message`
- `created_at`
- `updated_at`

`fingerprint` 由以下信息计算：

```text
project_id + platform_type + repo_url + ref + head_sha + tool_signature + settings_hash
```

### 8.7 `agent_memory_notes`

这张表作为可选增强，用于 durable memory。第一版可以先不建，但设计上预留。

字段建议：

- `id`
- `project_id`
- `session_id`
- `topic`
- `text`
- `tags`: JSON
- `source`
- `is_active`
- `created_by`
- `created_at`
- `updated_at`

## 9. API 与 SSE 设计

### 9.1 API 路由

建议新增以下路由：

```text
GET    /api/v1/projects/{project_id}/agent/sessions
POST   /api/v1/projects/{project_id}/agent/sessions
GET    /api/v1/agent/sessions/{session_id}
GET    /api/v1/agent/sessions/{session_id}/messages
POST   /api/v1/agent/sessions/{session_id}/messages
GET    /api/v1/agent/sessions/{session_id}/stream
POST   /api/v1/agent/sessions/{session_id}/snapshot/refresh
GET    /api/v1/agent/runs/{run_id}
```

### 9.2 交互流

一次用户提问的流程：

1. 前端进入项目详情页，请求项目 agent sessions。
2. 没有可用 session 时创建新 session。
3. 用户发送消息。
4. 后端创建 user message、assistant message 与 agent run。
5. 后端返回 `user_message_id`、`assistant_message_id` 与 `run_id`。
6. 前端通过 SSE 订阅 session 或 run 事件。
7. worker 或应用内任务执行 agent run，持续写入 events。
8. SSE 推送 assistant delta、tool events、final 或 error。
9. run 完成后 assistant message 状态更新为 `completed` 或 `failed`。

### 9.3 SSE 事件

第一版事件类型：

- `run_started`
- `assistant_delta`
- `tool_start`
- `tool_result`
- `assistant_message`
- `final`
- `error`
- `snapshot_status`

事件通用结构：

```json
{
  "id": 12345,
  "event": "tool_start",
  "data": {
    "run_id": 3001,
    "session_id": 101,
    "sequence": 7,
    "timestamp": "2026-06-03T10:01:12Z"
  }
}
```

SSE 需要支持 `Last-Event-ID` 或 `since_event_id`，便于断线续传。

## 10. Agent 运行流

### 10.1 核心服务

`AgentRunService` 负责整轮执行编排，对应平台版 `Pico.ask()`。

职责：

- 读取 session、memory、snapshot。
- 通过 `ContextManager` 组装 prompt。
- 调用 model client。
- 解析工具调用或 final answer。
- 驱动多步循环。
- 更新 run、message、event、artifact。
- 结束时持久化新的 memory state。

`AgentToolGateway` 负责工具网关。

职责：

- 工具白名单注册。
- 参数校验。
- 权限与项目范围校验。
- 连续重复调用拦截。
- 同 run 工具结果缓存。
- 调用 repository provider。
- 脱敏。
- 裁剪。
- 记录 event 与 artifact。

`RepositoryContentProvider` 负责仓库读取。

职责：

- `list_files`
- `read_file`
- `search`
- `get_recent_commits`
- `get_project_overview`

`AgentEventRecorder` 负责事件写入与 SSE 通知。

### 10.2 运行流程

```text
POST /agent/sessions/{id}/messages
  -> create user_message
  -> create assistant_message(status=streaming)
  -> create agent_run(status=running)
  -> dispatch run job

AgentRunService.run(run_id)
  -> load session + snapshot + memory
  -> build prompt
  -> record run_started
  -> loop within max_steps:
       call model
       if final answer:
         stream assistant delta/final
         update memory
         persist artifacts
         mark run completed
         stop
       if tool call:
         validate tool
         execute via AgentToolGateway
         record tool_start/tool_result
         append tool result into history
         continue
       else:
         retry malformed response
  -> on failure:
       mark run failed
       emit error
```

### 10.3 停止条件

沿用 `pico` 的状态语义，第一版包含：

- `final_answer_returned`
- `step_limit_reached`
- `retry_limit_reached`
- `model_error`
- `tool_error`
- `cancelled`

不包含 checkpoint 与 resume 相关 stop reason。

## 11. 工具网关设计

### 11.1 第一版工具

第一版只开放只读工具：

```text
list_files(path='.', ref=default_branch)
read_file(path, start=1, end=200, ref=default_branch)
search(pattern, path='.', ref=default_branch)
get_project_overview()
get_recent_commits(limit=10)
```

可选工具：

```text
get_recent_review_records(limit=10)
```

### 11.2 执行链路

工具执行链路保留 `pico` 现有思路，并在线上增强：

1. 工具是否存在。
2. 参数是否合法。
3. 是否命中连续重复调用保护。
4. 是否通过项目权限与 session scope 校验。
5. 是否命中同 run 工具结果缓存。
6. 真正执行。
7. 对输出脱敏。
8. 对输出裁剪。
9. 写入 event 与 artifact。
10. 更新 memory。

### 11.3 重复调用拦截

保留 `pico.repeated_tool_call()` 的 loop guard：

- 从 session history 中取最近的 tool events。
- 如果最近两次工具名和参数都与本次调用一致，则认为 agent 可能陷入无新信息重复调用。
- 网关拒绝本次调用，并把拒绝原因作为工具结果反馈给模型。

这层用于防止坏循环，不等同于结果缓存。

### 11.4 工具结果缓存

新增平台级同 run 缓存：

```text
tool_call_key = sha256(snapshot_id + tool_name + normalized_args)
```

规则：

- 只在同一个 run 内复用。
- 只复用相同 snapshot 下的成功工具结果。
- 命中缓存时仍然记录 `tool_result` event，并标记 `cached=true`。

### 11.5 脱敏规则

工具结果入 prompt、event 或 artifact 前必须脱敏：

- API key。
- token。
- secret。
- password。
- Authorization header。
- 私有环境变量名匹配项。
- 项目 settings 中标记为敏感的字段。

脱敏后再进行裁剪。

## 12. 上下文设计

保留 `pico` prompt 结构：

```text
Prefix:
- agent instructions
- workspace context
- tool specs
- output rules

Memory:
- task summary
- recent files
- file summaries
- episodic notes

Relevant memory:
- retrieved durable notes

History:
- recent conversation/tool events

Current user request:
- user message
```

平台版 `workspace_fingerprint` payload：

```json
{
  "project_id": 1,
  "platform_type": "github",
  "repo_url": "...",
  "default_branch": "main",
  "head_sha": "...",
  "snapshot_id": 88,
  "snapshot_fingerprint": "...",
  "project_settings_hash": "...",
  "tool_signature": "..."
}
```

当 fingerprint 变化时，session 仍可继续，但新 run 应使用新 snapshot 与新 prefix。

## 13. 仓库快照策略

`repository_snapshots` 是线上版 `WorkspaceContext`，不是完整索引。

### 13.1 快照内容

第一版快照包含：

- 默认分支 head sha。
- 文件树。
- README 摘要。
- 关键配置文件摘要，如 `pyproject.toml`、`package.json`、`README.md`。
- 最近提交摘要。
- 少量关键文件摘要。

### 13.2 刷新策略

刷新规则：

- 创建 session 时如果项目没有 ready snapshot，则创建基础 snapshot。
- 发送消息前如果 head sha 变化，则标记旧 snapshot 为 `stale` 并刷新。
- 前端提供手动 refresh。
- 第一版不做后台持续增量同步。

### 13.3 search 策略

考虑到 GitHub/GitLab 搜索 API 的权限、限流和部署差异，第一版 `search` 优先基于 snapshot 中的轻量文本索引与关键文件内容摘要。

`read_file` 仍按需走 GitHub/GitLab 内容 API，确保读取最新且可控的文件片段。

## 14. 前端设计

前端入口挂在项目详情或项目页的“仓库助手”区域，不新增全局聊天中心。

第一版页面包含：

- session 列表。
- 消息流。
- 输入框。
- 当前 snapshot 状态。
- 当前默认分支与 head sha。
- 最近读取文件。
- 最近工具事件。

工具事件展示以简洁可解释为主：

- 正在搜索 `backend`。
- 读取 `backend/app/main.py` 第 1-120 行。
- 使用缓存结果。
- 仓库快照正在刷新。

不在普通用户界面展示完整工具输出。完整输出进入 event/artifact，供调试与审计使用。

## 15. 权限与安全

第一版权限建议：

- 读取 sessions/messages/runs：复用 `project:read`。
- 发送消息：复用 `project:read`，后续可拆成 `project:agent:chat`。
- 刷新 snapshot：复用 `project:update`，后续可拆成 `project:agent:refresh`。

运行约束：

- `read_only = true`
- `approval_policy = never`
- `max_depth = 0`
- `delegate` disabled
- 不暴露 shell/write/patch 工具

所有工具调用必须绑定 project 与 snapshot，不允许模型传入任意仓库 URL。

## 16. 测试计划

第一版测试重点：

- `AgentToolGateway`
  - 工具不存在时拒绝。
  - 参数非法时拒绝。
  - 连续重复调用时拒绝。
  - 同 run 缓存命中时复用结果。
  - 输出脱敏后再返回。
  - 输出超过限制时裁剪。
- `AgentRunService`
  - final answer 正常完成。
  - 多步工具调用后完成。
  - 工具错误被记录并反馈。
  - step limit 到达后停止。
  - memory state 在 run 结束后持久化。
- `RepositorySnapshotService`
  - 创建基础 snapshot。
  - head sha 变化时标记 stale。
  - file tree 与 overview 正确写入。
- API 集成测试
  - 创建 session。
  - 发送消息创建 run。
  - 查询 messages。
  - 查询 run。
- SSE 集成测试
  - 推送 `run_started`。
  - 推送工具事件。
  - 推送 final。
  - 支持 `Last-Event-ID` 或 `since_event_id`。

## 17. 分阶段落地

### 17.1 第一阶段：后端核心与数据模型

- 新增 Alembic 迁移。
- 新增 ORM models。
- 新增 agent schemas。
- 新增 session/message/run/event/artifact services。
- 建立 fake model client 的 `AgentRunService` 单测。

### 17.2 第二阶段：pico-core 抽取与工具网关

- 抽取 `ContextManager` 与 memory 相关代码。
- 建立只读 tool registry。
- 实现 `AgentToolGateway`。
- 实现连续重复调用拦截。
- 实现同 run 工具缓存。
- 实现脱敏与裁剪。

### 17.3 第三阶段：仓库 provider 与 snapshot

- 实现 `RepositoryContentProvider` protocol。
- 实现 GitHub provider。
- 实现 GitLab provider。
- 实现 `RepositorySnapshotService`。
- 接入 `list_files`、`read_file`、`search`、`get_recent_commits`。

### 17.4 第四阶段：API、SSE 与前端

- 新增 agent API routes。
- 新增 SSE stream。
- 前端项目页增加仓库助手入口。
- 展示 session、messages、streaming answer、tool events 与 snapshot 状态。

## 18. 验收标准

第一版完成后应满足：

- 用户可以在项目下创建仓库助手 session。
- 用户可以发送问题并收到流式回答。
- agent 可以基于轻量快照理解仓库基本结构。
- agent 可以通过只读工具搜索和读取仓库文件片段。
- 工具调用经过存在性检查、参数校验、重复调用拦截、权限校验、缓存、脱敏、裁剪和记录。
- session、message、run、event、artifact、snapshot 均落 PostgreSQL。
- 不存在 shell/write/patch/delegate 暴露面。
- API 与 SSE 有集成测试覆盖。

## 19. 后续扩展

本设计为后续能力预留以下方向：

- durable memory 跨 session 项目记忆。
- review record 关联问答。
- PR/MR explain 模式。
- 完整 RAG 与 embedding。
- clone workspace 与更强的本地搜索。
- 受控 patch proposal。
- 多 agent delegation。
- checkpoint/resume。

这些能力不进入第一版，避免影响仓库理解助手的首期稳定交付。
