# AI Code Review Platform

一个以 AI Code Review 为核心的代码审查平台，当前聚焦 `GitHub + GitLab` 场景，已将 webhook 接入、审查执行、结果落库、评论回写、通知投递与日报能力统一收敛到 `FastAPI backend` 体系中。

这个仓库的目标不是只做一个简单的 LLM 调用脚本，而是提供一条可运营、可扩展、可验证的 review pipeline：

- 接收 GitHub / GitLab webhook
- 将审查事件写入 PostgreSQL
- 通过 Redis queue 异步调度 review worker
- 组装 prompt 并调用 LLM 生成审查结果
- 回写 PR / MR comment
- 投递 Feishu / WeCom / DingTalk / custom webhook 通知
- 生成日报与后续分析能力

## 项目现状

当前主链路已经完成从历史 `codereview` 运行时向 `backend` 的迁移，`backend` 已经是唯一的 review runtime。

现阶段重点能力包括：

- `GitHub` / `GitLab` webhook ingestion
- `PostgreSQL` review record persistence
- `Redis-backed queue` 与异步 worker 消费
- backend native reviewer 与 prompt template 兼容
- review comment delivery
- IM notification delivery
- daily report generation
- 真实 `git push` 全链路验证脚本

## 仓库导航

### `backend/`

项目主后端，基于 `FastAPI + SQLAlchemy + PostgreSQL + Redis`。

这里包含：

- webhook API
- review worker
- review execution service
- reviewer / prompt / reporting 实现
- admin domain 与认证授权
- 数据迁移、测试、验证脚本

详细运行说明见：
[backend/README.md](/Users/jacob/GitProject/ai-code-reviewer/backend/README.md)

### `frontend/`

后台前端应用，基于 `React + Vite + TypeScript`，当前主要承载管理台与平台交互界面。

从依赖与结构来看，前端包含：

- routing
- auth context
- React Query data layer
- admin-oriented UI entry

如果你在看仓库整体能力，建议把它理解为“平台控制台”；核心 review runtime 仍然在 `backend/`。

### `docs/`

沉淀设计、实现计划与验证记录。

重点可看：

- 设计文档：`docs/superpowers/specs/`
- 实施计划：`docs/superpowers/plans/`
- 真实链路验证：`docs/verification/`

建议优先阅读：

- [docs/superpowers/specs/2026-05-30-codereview-fastapi-integration-design.md](/Users/jacob/GitProject/ai-code-reviewer/docs/superpowers/specs/2026-05-30-codereview-fastapi-integration-design.md)
- [docs/superpowers/specs/2026-05-31-backend-single-entry-and-codereview-migration-design.md](/Users/jacob/GitProject/ai-code-reviewer/docs/superpowers/specs/2026-05-31-backend-single-entry-and-codereview-migration-design.md)
- [docs/verification/2026-05-31-backend-single-entry-review-implementation-verification.md](/Users/jacob/GitProject/ai-code-reviewer/docs/verification/2026-05-31-backend-single-entry-review-implementation-verification.md)

## 快速开始

如果你是第一次拉起这个项目，建议先只关注 `backend`。

### 1. 准备基础依赖

- PostgreSQL
- Redis
- Python 3.12+

### 2. 初始化 backend

```bash
cd backend
cp .env.example .env
alembic upgrade head
```

### 3. 启动 backend

```bash
cd backend
uvicorn app.main:app --reload
```

默认推荐的本地开发方式是：

- 只启动 `uvicorn`
- 在 `.env` 中开启 `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1`
- 让 backend 在开发模式下自动托管 review worker

更完整的环境变量、worker 与 webhook 说明，请直接看：
[backend/README.md](/Users/jacob/GitProject/ai-code-reviewer/backend/README.md)

## Review Flow 概览

当前主链路可以概括为：

1. GitHub / GitLab 触发 webhook
2. backend 识别项目并写入 `review_records`
3. 事件进入 Redis review queue
4. review worker 消费任务并拉取变更
5. reviewer 组装 prompt 并调用 LLM
6. 审查结果写回数据库
7. comment 回写到 PR / MR
8. 通知机器人发送 IM 消息

这条链路已经有真实验证脚本覆盖，入口在：

- [backend/scripts/verify_full_review_flow.py](/Users/jacob/GitProject/ai-code-reviewer/backend/scripts/verify_full_review_flow.py)

验证结果记录见：

- [docs/verification/2026-05-31-backend-single-entry-review-implementation-verification.md](/Users/jacob/GitProject/ai-code-reviewer/docs/verification/2026-05-31-backend-single-entry-review-implementation-verification.md)


## 当前边界

当前优先支持：

- GitHub
- GitLab

`Gitea` 后续再补。

另外，根 README 只负责项目导航与快速认知，不重复展开 backend 的所有运行细节；具体配置、命令和运行约束以 [backend/README.md](/Users/jacob/GitProject/ai-code-reviewer/backend/README.md) 为准。
