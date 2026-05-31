# Backend 单入口与 CodeReview 全量迁移设计

## 1. 背景

当前仓库已经完成 webhook 接入、审查记录入库、Redis 队列、worker 执行、评论回写、通知投递与真实链路验证，`backend` 已经具备承接统一审查平台的主干能力。

但当前运行形态仍然存在两个明显问题：

- 本地开发时需要分别启动 `uvicorn` 与 `review_worker`，开发体验不连续。
- `codereview/` 目录仍然保留独立运行时与核心审查实现，`backend` 侧通过桥接方式调用，尚未完成真正的一体化收口。

用户已经确认接下来的方向是：

- 本地开发模式下只启动 `uvicorn`，由项目自动拉起 worker。
- `codereview/` 的代码最终完整迁入 `backend`，后续删除 `codereview/` 目录。
- 生产环境仍以同一项目的不同运行角色部署，而不是维护两个独立项目。

本设计文档用于明确目标架构、迁移边界、过渡策略、验收标准与实施顺序，作为后续实施计划的基线。

## 2. 目标

本阶段目标如下：

- 将 `backend` 作为唯一长期运行时归属。
- 在本地开发模式下实现单入口启动，只需运行 `uvicorn`。
- 将 `codereview/` 中的审查核心能力逐步迁入 `backend/app/review/*`。
- 保证现有 GitLab + GitHub webhook 审查链路持续可用。
- 保持现阶段环境变量配置方式不变。
- 为最终删除 `codereview/` 提供可验证、可回滚的迁移路径。

## 3. 非目标

本设计明确不包含以下内容：

- Gitea 实时接入，本轮仅保留后续扩展位。
- 将平台凭据改造成项目级数据库托管。
- 新增分布式调度平台或多 worker 编排平台。
- 重做管理后台交互或通知产品形态。
- 在本轮内引入全新的审查算法或多轮深度审查模式。

## 4. 已确认约束

- 首期平台范围为 `GitLab + GitHub`，`Gitea` 后补。
- 继续沿用 `codereview` 的环境变量配置方式。
- 尽量实现 `codereview` 的全量功能迁移，而不是只迁 webhook 外壳。
- spec 使用中文。
- 本轮优先保证真实链路稳定，不接受只停留在架构抽象层。

## 5. 现状判断

当前系统已经形成如下分层：

- `backend/app/api/` 负责 FastAPI API 与 webhook 接入。
- `backend/app/services/` 负责审查记录入库、队列、执行、通知、评论等服务。
- `backend/app/workers/review_worker.py` 负责消费 Redis 队列并触发审查执行。
- `codereview/` 内仍持有 LLM reviewer、环境变量约定、部分平台行为与审查核心逻辑。

这意味着当前状态不是最终形态，只是“`backend` 外壳 + `codereview` 核心”的兼容过渡态。它已经能跑通链路，但仍存在以下结构性问题：

- worker 启动方式与 FastAPI 生命周期割裂。
- reviewer 逻辑边界不清，核心审查能力不在 `backend` 领域内。
- `codereview` 目录仍然对路径、环境和运行时上下文有显式依赖。
- 后续如果继续在桥接模式上堆功能，删除 `codereview/` 的成本会越来越高。

## 6. 方案对比

### 6.1 方案 A：只做开发态单入口

做法：

- 保持 `codereview` 桥接结构不变。
- 仅在 FastAPI `lifespan` 中自动拉起一个本地 worker 子进程。

优点：

- 交付快，改动集中。
- 能立即改善本地开发体验。

缺点：

- 只解决启动体验，不解决架构收口。
- `codereview/` 仍然是事实上的核心运行时。
- 后续仍需再做一次完整迁移。

### 6.2 方案 B：先收口运行方式，再分批迁移核心能力

做法：

- 先在 `backend` 中建立统一生命周期与 worker 托管机制。
- 再将 `codereview` 的能力按模块迁入 `backend/app/review/*`。
- 迁移期间保留兼容适配层与开关。

优点：

- 本地体验和最终架构同时收敛。
- 可以维持真实链路持续可用。
- 适合逐步替换和阶段验收。

缺点：

- 需要设计过渡层。
- 迁移期间会短暂存在双实现并存。

### 6.3 方案 C：一次性大重构

做法：

- 一次性把 worker、reviewer、配置、报告、通知都迁完。

优点：

- 最终结构最干净。

缺点：

- 回归面太大。
- 很难在中间阶段维持真实 webhook 链路稳定。
- 排障成本高，不利于并行验证。

### 6.4 结论

采用 **方案 B**。

这是当前约束下最稳妥的路径：先把运行时边界收口，再逐步迁移 `codereview` 核心能力，最终删除 `codereview/`。

## 7. 目标架构

### 7.1 总体原则

- `backend` 是唯一长期代码归属与运行入口。
- 本地开发允许单入口，但 worker 仍然是独立执行单元。
- 生产环境继续拆分为同一项目下的 API 角色和 Worker 角色。
- 审查能力应以内聚模块形式沉淀在 `backend/app/review/`。
- 迁移期间允许适配层存在，但不允许新增对 `codereview/` 的深度耦合。

### 7.2 运行角色

系统最终保留两个运行角色：

- `API Role`
  - 承载 FastAPI、管理后台 API、webhook 接入、鉴权、Bootstrap、健康检查。
- `Worker Role`
  - 承载审查任务消费、平台 diff 拉取、prompt 组装、LLM 调用、评论回写、通知投递、日报生成等异步工作。

这两个角色属于同一项目、同一代码仓库、同一数据库和同一配置体系，不是两个项目。

### 7.3 本地开发模式

本地开发模式下仅启动：

```bash
uvicorn app.main:app --reload
```

随后由 FastAPI 生命周期托管一个开发态 worker supervisor，自动拉起一个 worker 子进程。

### 7.4 生产模式

生产环境维持两个进程或两个 workload：

- `uvicorn app.main:app`
- `python -m app.workers.review_worker`

原因如下：

- API 流量与审查任务具备不同的资源特征。
- worker 的耗时、内存与失败重试模型不应和 API 请求进程耦合。
- 独立角色更便于水平扩缩、容错与可观测。

## 8. 模块边界设计

### 8.1 新的目标目录结构

建议形成如下结构：

- `backend/app/api/`
- `backend/app/services/`
- `backend/app/workers/`
- `backend/app/review/config/`
- `backend/app/review/llm/`
- `backend/app/review/reviewer/`
- `backend/app/review/reporting/`
- `backend/app/review/platform/`
- `backend/app/core/`

### 8.2 关键组件

建议引入以下组件边界：

- `AppLifecycleManager`
  - 负责应用生命周期编排、bootstrap、开发态 worker 启停协调。
- `DevWorkerSupervisor`
  - 仅在开发模式下启用，负责拉起、监控、关闭一个本地 worker 子进程。
- `ReviewWorker`
  - 负责消费队列并调用执行服务。
- `ReviewExecutionService`
  - 负责单次审查任务的完整编排。
- `ReviewerProtocol`
  - 定义 reviewer 的统一接口。
- `PlatformAdapter`
  - 负责平台差异，如 PR/MR/Push diff 获取、评论回写、通知补充上下文。
- `ReviewPromptBuilder`
  - 负责从模板、变更、提交信息组装 prompt。
- `ReviewReporter`
  - 负责日报或统计汇总输出。

### 8.3 组件职责

职责划分如下：

- `api` 层只做接收、校验、入库、入队，不做长耗时审查。
- `services` 层负责业务编排、数据库变更、状态流转。
- `workers` 层负责消费与进程边界。
- `review/*` 层负责平台无关或平台相关的审查核心能力。

## 9. 开发态单入口设计

### 9.1 设计目标

- 只开 `uvicorn` 即可跑本地完整链路。
- 不影响生产 worker 的独立运行方式。
- 在 `--reload` 场景下避免重复拉起多个 worker。

### 9.2 设计方案

在 FastAPI `lifespan` 中增加开发态托管逻辑：

- 当 `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER=1` 时启用。
- 创建 `DevWorkerSupervisor`。
- supervisor 启动一个子进程执行 worker 入口。
- 应用退出时回收该子进程。

### 9.3 reload 场景要求

必须处理 `uvicorn --reload` 的重复进程问题，避免父进程与重载子进程都拉起 worker。设计要求如下：

- 只允许真正承载请求的服务进程拉起 worker。
- worker 进程必须带有可识别标记，便于本地排查。
- 重载时旧 worker 应被清理，新 worker 再拉起。

### 9.4 失败策略

- 开发态 worker 启动失败时，API 启动不能静默成功。
- 至少要在日志中明确报错并给出退出原因。
- 本设计明确要求 API 直接 fail fast 并退出，避免出现“API 看起来启动成功但本地链路实际不可用”的假成功状态。

## 10. CodeReview 全量迁移设计

### 10.1 迁移对象

需要从 `codereview/` 迁入 `backend` 的能力至少包括：

- LLM 配置读取与 provider 选择。
- prompt 组装与审查主流程。
- review score 解析。
- 支持文件后缀与过滤策略。
- 平台差异适配中仍然留在 `codereview/` 的部分行为。
- 报告与日报能力。
- 与 reviewer 强绑定的环境变量兼容逻辑。

### 10.2 迁移后的目标归属

- LLM 能力迁入 `backend/app/review/llm/`
- reviewer 能力迁入 `backend/app/review/reviewer/`
- 平台审查拼装逻辑迁入 `backend/app/review/platform/`
- 日报与汇总能力迁入 `backend/app/review/reporting/`
- 兼容配置能力迁入 `backend/app/review/config/`

### 10.3 过渡层设计

在迁移期间引入 reviewer 抽象层：

- `ReviewerProtocol`
- `LegacyCodeReviewerAdapter`
- `BackendReviewerAdapter`

其中：

- `LegacyCodeReviewerAdapter` 继续桥接 `codereview` 老实现。
- `BackendReviewerAdapter` 指向新迁入 `backend` 的实现。

执行服务始终只依赖 `ReviewerProtocol`，不直接依赖 `codereview`。

### 10.4 迁移开关

建议增加以下开关：

- `AI_CODE_REVIEWER_DEV_AUTOSTART_WORKER`
- `AI_CODE_REVIEWER_USE_BACKEND_REVIEWER`

含义如下：

- 第一个开关控制本地开发时是否自动托管 worker。
- 第二个开关控制执行服务使用老 reviewer 还是新 reviewer。

这样可以保证迁移期间随时切换回旧实现，便于真实链路回归。

### 10.5 删除条件

只有满足以下条件后，才能删除 `codereview/`：

- 新 reviewer 默认运行在 `backend` 中。
- GitLab + GitHub 真实链路验证通过。
- 通知、评论、日报、评分解析都不再依赖 `codereview` 目录。
- 回归测试与验证脚本不再引用 `codereview` 路径。

## 11. 配置策略

### 11.1 本轮原则

继续保持环境变量配置方式，不做项目级密钥托管改造。

### 11.2 配置归属

迁移完成后，环境变量读取逻辑应统一由 `backend` 配置层管理，但字段名保持兼容，避免破坏现有 `.env`。

### 11.3 兼容要求

- `backend` 作为唯一配置入口。
- 历史 `codereview` 使用的变量名尽量继续兼容。
- 不允许新的核心模块依赖切换工作目录或手工注入 `sys.path` 才能运行。

## 12. 数据流与执行流

目标执行流保持如下：

1. GitLab / GitHub webhook 进入 `backend`。
2. webhook 解析、幂等检查、项目匹配、记录入库。
3. 任务进入 Redis 队列。
4. worker 消费任务并加载 `ReviewExecutionService`。
5. `ReviewExecutionService` 调用平台 adapter 拉取变更与提交信息。
6. `ReviewPromptBuilder` 按项目模板与变更内容组装 prompt。
7. reviewer 调用 LLM 并返回审查结果。
8. 执行服务更新 `review_records` 状态、分数、总结、trace。
9. 评论服务回写 GitLab / GitHub comment。
10. 通知服务按配置选择机器人并投递 IM 消息。
11. 日报与统计能力从 PostgreSQL 统一读取数据。

## 13. 测试与验收

### 13.1 测试层次

至少覆盖以下四层：

- 生命周期层
  - 验证开发态 worker 自动拉起与退出回收。
- 审查核心层
  - 验证新 reviewer 与 legacy reviewer 在关键行为上兼容。
- 执行链路层
  - 验证 webhook 入队、worker 消费、状态流转、评论与通知。
- 真实回归层
  - 使用现有真实链路验证脚本执行一次完整 `git push`。

### 13.2 里程碑验收

里程碑 1：开发态单入口完成

- 仅开 `uvicorn` 即可跑通 webhook -> queue -> worker -> review 的本地链路。
- reload 不会产生多个 worker。

里程碑 2：`codereview/` 可删除

- 新 reviewer 成为默认实现。
- 全链路验证通过。
- 删除 `codereview/` 后测试与真实验证仍然通过。

## 14. 实施顺序

建议按以下顺序进入后续实施计划：

1. 建立开发态 worker supervisor 与生命周期托管。
2. 抽象 reviewer 接口，解耦执行服务与 `codereview` 直接依赖。
3. 将 LLM、prompt、score 解析等能力迁入 `backend/app/review/*`。
4. 将报告与日报能力迁入 `backend`。
5. 切换默认 reviewer 到 backend 实现。
6. 跑完整测试与真实链路验证。
7. 删除 `codereview/` 与相关兼容代码。

## 15. 分支策略

这轮工作建议从现有已稳定的 `feature/review-agent-access` 再切独立实现分支进行，例如：

- `codex/backend-single-entry-review-migration`

这样可以：

- 保持已完成的 webhook/worker 主线稳定。
- 让开发态单入口与全量迁移形成独立提交序列。
- 便于在迁移过程中做阶段性回滚、对比与 PR 拆分。

## 16. 结论

本次改造不建议只修“本地启动不方便”这一层表象问题，也不建议一次性大重构。最合适的路径是：

- 以 `backend` 为唯一归属。
- 先收口本地与生产的运行边界。
- 再通过 reviewer 抽象与兼容开关逐步把 `codereview` 全量迁入 `backend`。
- 最终删除 `codereview/`，使 FastAPI 后端成为唯一可运行系统。

这是当前约束下最稳、可验证、可持续演进的方案。
