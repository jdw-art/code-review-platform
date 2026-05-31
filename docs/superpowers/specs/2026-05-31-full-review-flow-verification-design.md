# 全链路验证脚本设计

## 背景
当前 backend 已接管 webhook 入库、Redis 入队、worker 执行、评论回写和通知投递，但需要一套**真实 `git push`** 的验证脚本，来检查整条链路是否可跑通，并在执行过程中产出可复盘文档。

本设计只做验证，不修改现有业务代码。

## 目标
- 通过一次真实的 GitHub `git push` 触发完整链路。
- 检查数据库是否新增 `review_records`，以及 `review_status`、`delivery_status`、`score`、`review_result`、`error_message` 等字段是否按预期变化。
- 检查 Redis 队列是否正常入队、消费、清空。
- 检查 `review_worker` 是否能正常执行。
- 检查 Git comment 是否回写成功。
- 将执行过程、已确认通过项、未通过项、卡点写入 Markdown 文档。

## 非目标
- 不修改现有 webhook / worker / adapter 业务代码。
- 不自动拉起 PostgreSQL、Redis、uvicorn。
- 不自动修复链路问题。
- 不删除测试分支或测试提交。

## 用户约束
- 必须是真实 `git push`。
- 可以修改 `README.md` 触发一次最小变更。
- 脚本可以自动提交并 push。
- 验证完成后保留测试分支和测试提交。
- 运行方式采用半自动：脚本自动拉起 `review_worker`，但不接管 `uvicorn` / PostgreSQL / Redis。
- 结果采用分级判定：
  - `核心通过`
  - `完整通过`

## 方案选择
### 方案 A
Shell 脚本。
- 优点：启动快。
- 缺点：状态采集、JSON 处理、报告生成弱。

### 方案 B
Python 单文件 CLI 验证器。
- 优点：能统一处理 git、HTTP、数据库、Redis、worker、报告。
- 缺点：脚本会比较长。

### 方案 C
Python CLI + 场景配置。
- 优点：扩展性最好。
- 缺点：对当前阶段略重。

### 选型
采用 **方案 B**。它最适合当前目标：真实 `git push`、统一证据采集、保留执行文档，同时不会引入过多抽象。

## 总体架构
脚本建议放在：
- `backend/scripts/verify_full_review_flow.py`

内部按职责拆成四段：
- `PreflightChecker`：做前置检查。
- `PushTrigger`：生成 README 最小变更、提交、push。
- `FlowObserver`：轮询数据库、Redis、worker、GitHub comment。
- `ReportWriter`：输出 Markdown 执行文档。

## 执行流程
### 1. Preflight
采集并记录：
- 当前时间
- git 分支、HEAD commit
- PostgreSQL / Redis 可用性
- FastAPI 健康状态
- 关键环境变量存在性
- `review_records` 基线
- Redis 队列基线

### 2. 启动 worker
脚本自动拉起一个短生命周期 `review_worker` 子进程，并记录：
- PID
- 启动时间
- stdout / stderr
- 是否存活

### 3. 生成真实 push
在专用测试分支上修改 `README.md` 一处可识别标记，生成一次真实 commit 并 push 到 GitHub。

### 4. 观测链路
按固定轮询窗口采集：
- 数据库是否新增匹配本次 push 的 `review_record`
- `review_status` 是否流转
- `delivery_status` 是否变化
- `score`、`review_result`、`error_message`、`retry_count` 是否更新
- Redis 队列长度和队首消息
- worker 输出
- GitHub comment 是否出现

### 5. 判定并出报告
输出分级结论并生成 Markdown 文档。

## 判定标准
### 核心通过
满足以下条件：
- 真实 `git push` 成功。
- 出现匹配本次验证的 `review_record`。
- `review_status` 有有效流转，不永久停在 `queued`。
- worker 实际执行了任务。
- 数据库字段发生合理变化。

### 完整通过
在核心通过基础上，还满足：
- GitHub comment 成功出现。

### 失败
任一关键环节失败：
- 没有新增记录。
- 记录新增但卡在 `queued`。
- worker 未启动或中途退出。
- 任务执行失败且可识别。
- GitHub comment 明确失败。

### 未判定
证据不足或权限不足时使用：
- 无法唯一定位记录。
- comment API 无权限但后端链路已通。
- 轮询超时。

## 观测点
### 数据库
重点字段：
- `id`
- `project_id`
- `platform_type`
- `event_type`
- `external_event_id`
- `external_pull_request_id`
- `external_commit_sha`
- `branch`
- `source_branch`
- `target_branch`
- `last_commit_id`
- `review_status`
- `delivery_status`
- `score`
- `review_result`
- `error_message`
- `retry_count`
- `created_at`
- `reviewed_at`
- `failed_at`
- `agent_trace`

### Redis
记录：
- 队列名
- push 前长度
- push 后长度
- 轮询期间长度变化
- 队首消息样本
- 最终长度

### worker
记录：
- 启动命令
- PID
- 存活状态
- 退出码
- stdout / stderr 摘录
- 关键异常栈

### GitHub comment
记录：
- 是否出现
- 目标对象是 PR 还是 commit
- 时间
- 评论摘要
- 失败原因或权限问题

## CLI 设计
建议参数：
- `--repo-root`
- `--backend-root`
- `--base-branch`
- `--branch-prefix`
- `--project-id`
- `--project-key`
- `--timeout-seconds`
- `--poll-interval`
- `--readme-path`
- `--report-path`
- `--skip-comment-check`

示例：

```bash
cd /Users/jacob/GitProject/ai-code-reviewer/backend
python scripts/verify_full_review_flow.py \
  --repo-root /Users/jacob/GitProject/ai-code-reviewer \
  --backend-root /Users/jacob/GitProject/ai-code-reviewer/backend \
  --base-branch feature/review-agent-access \
  --project-id 5
```

## 执行文档
建议输出到：
- `docs/verification/`

文档内容：
- 执行摘要
- 执行参数
- 前置检查结果
- push 触发信息
- 数据库时间线
- Redis 时间线
- worker 执行结果
- GitHub comment 检查结果
- 分级判定
- 已确认通过
- 未通过项
- 卡点与怀疑原因
- 附录快照

## 失败策略
- 前置检查失败：终止，但也要写文档。
- `git commit` / `git push` 失败：终止真实链路观测，保留 git 输出。
- webhook 未入库：继续轮询到超时，标记为核心失败。
- worker 启动失败：直接记录为核心失败。
- worker 执行失败：记录数据库最终状态和异常。
- comment 检查失败：不影响核心通过，但影响完整通过。

## 测试策略
- 验证 run id / 分支名生成。
- 验证 README 标记写入与恢复策略。
- 验证状态判定器。
- 验证 Markdown 报告输出。
- 验证前置检查失败时也会产出报告。

## 风险与限制
- 真实 GitHub comment 可能受 token 权限影响。
- Redis 异步客户端需要单一事件循环复用。
- 如果本地已有积压任务，脚本需要用时间窗口和 branch / commit 关联本次记录。
- 当前阶段不做自动修复，只做观测和记录。

## 验收标准
- 能真实触发一次 GitHub `git push`。
- 能记录完整的数据库 / Redis / worker / comment 证据。
- 能产出 Markdown 执行文档。
- 能给出 `核心通过` / `完整通过` / `失败` / `未判定` 中的明确结论。
