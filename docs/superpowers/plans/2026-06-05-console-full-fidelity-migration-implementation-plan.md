# Console Full-Fidelity Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `ai-code-review-console` 的 1:1 页面和交互完整迁移到 `frontend`，并与 `backend` 做真实联调，覆盖登录、仪表盘、项目管理、模板、模型、通知机器人、审查记录、成员分析、RBAC、系统日志和项目对话流。

**Architecture:** 保留现有 `frontend` 的路由、认证、HTTP client 和 feature/api 分层，在页面层新增 `console` 共享组件和 serializer / view-model 兼容层，把 `ai-code-review-console` 的视觉与交互逐页迁入正式路由。后端继续沿用现有业务域 service / route 结构，优先扩展既有接口；只有原型要求的真实动作不存在时，才新增正式接口，例如机器人测试、审查触发、审计日志 purge 和更完整的 agent 历史恢复 / SSE 事件。

**Tech Stack:** React 19、React Router、TanStack Query、TypeScript、Tailwind、FastAPI、SQLAlchemy、Pydantic、pytest、Vitest、SSE

---

## 文件结构

### 前端新增文件

- `frontend/src/components/console/ConsoleShell.tsx`
  - 承载原型风格后台壳子，可替换现有 `AppShell` 内部结构。
- `frontend/src/components/console/ConsoleSidebar.tsx`
  - 1:1 复刻原型侧边栏菜单样式。
- `frontend/src/components/console/ConsoleTopbar.tsx`
  - 1:1 复刻原型顶栏、标题与刷新动作。
- `frontend/src/components/console/ConsolePageHeader.tsx`
  - 页头卡片与按钮布局。
- `frontend/src/components/console/ConsoleStatCard.tsx`
  - 仪表盘 KPI 卡片。
- `frontend/src/components/console/ConsoleModal.tsx`
  - 原型风格新增 / 编辑弹窗。
- `frontend/src/components/console/ConsolePagination.tsx`
  - 原型风格分页器。
- `frontend/src/components/console/ConsoleStatusPill.tsx`
  - 原型风格状态标签。
- `frontend/src/components/console/ConsoleToast.tsx`
  - 原型风格 toast / inline banner。
- `frontend/src/features/dashboard/serializers.ts`
- `frontend/src/features/projects/serializers.ts`
- `frontend/src/features/project-templates/serializers.ts`
- `frontend/src/features/models/serializers.ts`
- `frontend/src/features/bots/serializers.ts`
- `frontend/src/features/reviews/serializers.ts`
- `frontend/src/features/member-analytics/serializers.ts`
- `frontend/src/features/system/serializers.ts`
- `frontend/src/features/agent/serializers.ts`
  - 负责把真实接口字段映射成原型视图字段。

### 前端修改文件

- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/SidebarNav.tsx`
- `frontend/src/components/layout/Topbar.tsx`
- `frontend/src/routes/router.tsx`
- `frontend/src/lib/api/types.ts`
- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/dashboard/DashboardPage.tsx`
- `frontend/src/pages/projects/ProjectListPage.tsx`
- `frontend/src/pages/projects/ProjectAgentPage.tsx`
- `frontend/src/pages/projects/ProjectTemplateListPage.tsx`
- `frontend/src/pages/models/ModelListPage.tsx`
- `frontend/src/pages/bots/BotListPage.tsx`
- `frontend/src/pages/reviews/ReviewRecordListPage.tsx`
- `frontend/src/pages/reviews/ReviewRecordDetailPage.tsx`
- `frontend/src/pages/analytics/MemberAnalyticsPage.tsx`
- `frontend/src/pages/system/UserListPage.tsx`
- `frontend/src/pages/system/RoleListPage.tsx`
- `frontend/src/pages/system/AuditLogPage.tsx`

### 后端修改文件

- `backend/app/api/routes/dashboard.py`
- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/notification_bots.py`
- `backend/app/api/routes/audit_logs.py`
- `backend/app/api/routes/agent.py`
- `backend/app/schemas/dashboard.py`
- `backend/app/schemas/project.py`
- `backend/app/schemas/notification_bot.py`
- `backend/app/schemas/audit_log.py`
- `backend/app/schemas/agent.py`
- `backend/app/services/dashboard_service.py`
- `backend/app/services/project_service.py`
- `backend/app/services/notification_bot_service.py`
- `backend/app/services/audit_log_service.py`
- `backend/app/services/agent_session_service.py`
- `backend/app/services/review_execution_service.py`

### 后端新增文件

- `backend/tests/integration/test_dashboard_api.py`
- `backend/tests/integration/test_projects_api.py`
- `backend/tests/integration/test_notification_bots_api.py`
- `backend/tests/integration/test_audit_logs_api.py`
- `backend/tests/integration/test_agent_api.py`
- `backend/tests/integration/test_agent_sse.py`

---

### Task 1: 建立高保真控制台共享壳子与基础组件

**Files:**
- Create: `frontend/src/components/console/ConsoleShell.tsx`
- Create: `frontend/src/components/console/ConsoleSidebar.tsx`
- Create: `frontend/src/components/console/ConsoleTopbar.tsx`
- Create: `frontend/src/components/console/ConsolePageHeader.tsx`
- Create: `frontend/src/components/console/ConsoleStatCard.tsx`
- Create: `frontend/src/components/console/ConsoleModal.tsx`
- Create: `frontend/src/components/console/ConsolePagination.tsx`
- Create: `frontend/src/components/console/ConsoleStatusPill.tsx`
- Create: `frontend/src/components/console/ConsoleToast.tsx`
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/layout/SidebarNav.tsx`
- Modify: `frontend/src/components/layout/Topbar.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: 先写壳子回归测试**

在 `frontend/src/components/layout/AppShell.test.tsx` 增加高保真壳子断言：

```tsx
it("renders console shell navigation and topbar labels", async () => {
  renderWithRouterAndAuth(<AppShell />, {
    route: "/dashboard",
    auth: buildAuthContext({
      user: { username: "admin", nickname: null },
      menus: buildConsoleMenus(),
    }),
  });

  expect(await screen.findByText("AI Code Review")).toBeInTheDocument();
  expect(screen.getByText("审查控制台")).toBeInTheDocument();
  expect(screen.getByText("系统日志")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /退出登录/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- AppShell.test.tsx`
Expected: FAIL，因为当前壳子文案和结构仍是旧后台样式。

- [ ] **Step 3: 新增共享 console 组件**

创建 `frontend/src/components/console/ConsoleShell.tsx`：

```tsx
import { Outlet } from "react-router-dom";

import type { MenuNode } from "../../lib/api/types";
import { ConsoleSidebar } from "./ConsoleSidebar";
import { ConsoleTopbar } from "./ConsoleTopbar";

export function ConsoleShell({
  menus,
  username,
  roleLabel,
  onLogout,
}: {
  menus: MenuNode[];
  username: string;
  roleLabel: string;
  onLogout: () => Promise<void>;
}) {
  return (
    <div className="flex min-h-screen bg-[#f1f5f9] text-slate-800">
      <ConsoleSidebar menus={menus} username={username} roleLabel={roleLabel} />
      <div className="flex min-h-screen flex-1 flex-col overflow-y-auto">
        <ConsoleTopbar onLogout={onLogout} />
        <main className="flex-1 pb-16">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

创建 `frontend/src/components/console/ConsolePageHeader.tsx`：

```tsx
import type { ReactNode } from "react";

export function ConsolePageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-white px-5 py-3.5 shadow-3xs sm:flex-row sm:items-center">
      <div>
        <h2 className="text-sm font-bold text-slate-800">{title}</h2>
        <p className="mt-0.5 text-[11px] text-slate-500">{description}</p>
      </div>
      {action}
    </div>
  );
}
```

- [ ] **Step 4: 用新壳子替换 `AppShell` 内部结构**

修改 `frontend/src/components/layout/AppShell.tsx`：

```tsx
import { Outlet } from "react-router-dom";

import { useAuth } from "../../lib/auth/auth-context";
import { ConsoleShell } from "../console/ConsoleShell";

export function AppShell() {
  const { menuTree, logout, roles, status, user } = useAuth();

  if (status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
        <div className="rounded-3xl border border-slate-200 bg-white px-8 py-6 text-sm text-slate-600 shadow-sm">
          正在初始化后台会话...
        </div>
      </main>
    );
  }

  const roleLabel = roles[0]?.name ?? "超级管理员";

  return (
    <ConsoleShell
      menus={menuTree}
      username={user?.username ?? "unknown"}
      roleLabel={roleLabel}
      onLogout={logout}
    >
      <Outlet />
    </ConsoleShell>
  );
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- AppShell.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/console frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/AppShell.test.tsx frontend/src/components/layout/SidebarNav.tsx frontend/src/components/layout/Topbar.tsx
git commit -m "feat(frontend): add console shell foundation"
```

### Task 2: 建立 API 类型扩展与 serializer 兼容层

**Files:**
- Create: `frontend/src/features/dashboard/serializers.ts`
- Create: `frontend/src/features/projects/serializers.ts`
- Create: `frontend/src/features/project-templates/serializers.ts`
- Create: `frontend/src/features/models/serializers.ts`
- Create: `frontend/src/features/bots/serializers.ts`
- Create: `frontend/src/features/reviews/serializers.ts`
- Create: `frontend/src/features/member-analytics/serializers.ts`
- Create: `frontend/src/features/system/serializers.ts`
- Create: `frontend/src/features/agent/serializers.ts`
- Modify: `frontend/src/lib/api/types.ts`
- Test: `frontend/src/pages/projects/ProjectListPage.test.tsx`
- Test: `frontend/src/pages/models/ModelListPage.test.tsx`

- [ ] **Step 1: 写 serializer 行为测试**

在 `frontend/src/pages/projects/ProjectListPage.test.tsx` 增加原型字段映射断言：

```tsx
it("maps project response into console card fields", () => {
  const vm = toConsoleProjectCard({
    id: 1,
    name: "ai-code-reviewer",
    key: "AICR",
    platform_type: "GitHub",
    repo_url: "https://github.com/demo/repo.git",
    default_branch: "main",
    description: "demo",
    is_active: true,
    review_enabled: true,
    template: { id: 8, name: "通用模板", code: "DEFAULT_GENERAL", is_active: true, review_prompt_configured: true },
    settings: {
      language: "TypeScript",
      owner: "jdw-art",
      average_score: 88.5,
      last_review_at: "2026-06-05T10:00:00Z",
    },
    created_by: 1,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  });

  expect(vm.enabled).toBe(true);
  expect(vm.language).toBe("TypeScript");
  expect(vm.scoreAverage).toBe(88.5);
  expect(vm.lastReviewAt).toContain("2026");
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ProjectListPage.test.tsx ModelListPage.test.tsx`
Expected: FAIL，因为 serializer 和扩展字段尚不存在。

- [ ] **Step 3: 扩展 API 类型，补齐原型需要的聚合字段**

修改 `frontend/src/lib/api/types.ts`，为项目和仪表盘补齐字段：

```ts
export interface DashboardChartPoint {
  name: string;
  commits: number;
  avg_score: number;
  additions: number;
  deletions: number;
}

export interface DashboardRecentReviewItem {
  id: number;
  project_name: string;
  title: string | null;
  branch: string | null;
  commit_hash: string | null;
  committer: string | null;
  score: number | null;
  review_status: string;
  summary: string | null;
  created_at: string;
}

export interface DashboardOverviewResponse {
  total_projects: number;
  active_projects: number;
  total_review_records: number;
  average_score: number | null;
  active_model_name: string | null;
  recent_reviews: DashboardRecentReviewItem[];
  project_chart: DashboardChartPoint[];
  member_chart: DashboardChartPoint[];
}
```

- [ ] **Step 4: 创建 serializer，把真实接口映射为原型 view model**

创建 `frontend/src/features/projects/serializers.ts`：

```ts
import type { ProjectResponse } from "../../lib/api/types";

export interface ConsoleProjectCard {
  id: number;
  name: string;
  key: string;
  platformType: string;
  enabled: boolean;
  reviewEnabled: boolean;
  language: string;
  description: string;
  owner: string;
  scoreAverage: number;
  lastReviewAt: string;
}

export function toConsoleProjectCard(project: ProjectResponse): ConsoleProjectCard {
  const settings = project.settings ?? {};
  return {
    id: project.id,
    name: project.name,
    key: project.key,
    platformType: project.platform_type,
    enabled: project.is_active,
    reviewEnabled: project.review_enabled,
    language: String(settings.language ?? "TypeScript"),
    description: project.description ?? "No description provided.",
    owner: String(settings.owner ?? "system"),
    scoreAverage: Number(settings.average_score ?? 0),
    lastReviewAt: String(settings.last_review_at ?? ""),
  };
}
```

创建 `frontend/src/features/models/serializers.ts`：

```ts
import type { LlmModelResponse } from "../../lib/api/types";

export function toConsoleModel(model: LlmModelResponse) {
  return {
    ...model,
    isActive: model.is_active,
    queriesCount: Number((model as unknown as { queries_count?: number }).queries_count ?? 0),
  };
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ProjectListPage.test.tsx ModelListPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/features/dashboard/serializers.ts frontend/src/features/projects/serializers.ts frontend/src/features/project-templates/serializers.ts frontend/src/features/models/serializers.ts frontend/src/features/bots/serializers.ts frontend/src/features/reviews/serializers.ts frontend/src/features/member-analytics/serializers.ts frontend/src/features/system/serializers.ts frontend/src/features/agent/serializers.ts frontend/src/pages/projects/ProjectListPage.test.tsx frontend/src/pages/models/ModelListPage.test.tsx
git commit -m "feat(frontend): add console serializer layer"
```

### Task 3: 迁移登录页、导航与 RBAC 菜单呈现

**Files:**
- Modify: `frontend/src/pages/auth/LoginPage.tsx`
- Modify: `frontend/src/routes/router.tsx`
- Modify: `frontend/src/components/console/ConsoleSidebar.tsx`
- Modify: `frontend/src/components/console/ConsoleTopbar.tsx`
- Test: `frontend/src/pages/auth/LoginPage.test.tsx`
- Test: `frontend/src/pages/system/SystemManagementRoutes.test.tsx`

- [ ] **Step 1: 写登录页高保真测试**

在 `frontend/src/pages/auth/LoginPage.test.tsx` 增加断言：

```tsx
it("renders console login experience with preset accounts", () => {
  render(<LoginPage />);

  expect(screen.getByText("AI Code Review Console")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "超级管理员" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "开发工程师" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "进入控制台" })).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- LoginPage.test.tsx SystemManagementRoutes.test.tsx`
Expected: FAIL，因为当前登录页与原型视觉不一致。

- [ ] **Step 3: 重写登录页为原型结构，但继续走真实登录接口**

修改 `frontend/src/pages/auth/LoginPage.tsx`，保留 mutation / token store，只替换 UI 结构：

```tsx
function PresetButtons({
  onSelect,
}: {
  onSelect: (username: string, password: string) => void;
}) {
  return (
    <div className="flex gap-2">
      <button type="button" onClick={() => onSelect("admin", "admin2026")}>
        超级管理员
      </button>
      <button type="button" onClick={() => onSelect("developer", "dev2026")}>
        开发工程师
      </button>
    </div>
  );
}
```

- [ ] **Step 4: 让顶栏标题根据路由切换成原型文案**

在 `frontend/src/components/console/ConsoleTopbar.tsx` 使用路由 title map：

```tsx
const TITLE_MAP: Record<string, string> = {
  "/dashboard": "欢迎回来",
  "/projects": "项目管理",
  "/project-templates": "项目模板管理",
  "/models": "模型管理",
  "/notification-bots": "通知机器人配置",
  "/review-records": "智能审查记录",
  "/member-analytics": "团队成员分析",
  "/system/users": "系统用户中心",
  "/system/roles": "智能角色矩阵",
  "/audit-logs": "系统审计日志",
};
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- LoginPage.test.tsx SystemManagementRoutes.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/auth/LoginPage.tsx frontend/src/pages/auth/LoginPage.test.tsx frontend/src/components/console/ConsoleSidebar.tsx frontend/src/components/console/ConsoleTopbar.tsx frontend/src/routes/router.tsx frontend/src/pages/system/SystemManagementRoutes.test.tsx
git commit -m "feat(frontend): migrate login and navigation to console UI"
```

### Task 4: 迁移模板、模型、机器人与 RBAC / 日志页面到高保真界面

**Files:**
- Modify: `frontend/src/pages/projects/ProjectTemplateListPage.tsx`
- Modify: `frontend/src/pages/models/ModelListPage.tsx`
- Modify: `frontend/src/pages/bots/BotListPage.tsx`
- Modify: `frontend/src/pages/system/UserListPage.tsx`
- Modify: `frontend/src/pages/system/RoleListPage.tsx`
- Modify: `frontend/src/pages/system/AuditLogPage.tsx`
- Test: `frontend/src/pages/models/ModelListPage.test.tsx`
- Test: `frontend/src/pages/system/UserListPage.test.tsx`
- Test: `frontend/src/pages/system/RoleListPage.test.tsx`

- [ ] **Step 1: 先补模型页和用户页的高保真断言**

在 `frontend/src/pages/models/ModelListPage.test.tsx` 增加：

```tsx
it("renders console model cards and activation action", async () => {
  render(<ModelListPage />);

  expect(await screen.findByText("审查模型与计算智能矩阵")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /部署新模型智算/i })).toBeInTheDocument();
});
```

在 `frontend/src/pages/system/UserListPage.test.tsx` 增加：

```tsx
it("renders console user management layout", async () => {
  render(<UserListPage />);

  expect(await screen.findByText("系统用户中心")).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认当前失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ModelListPage.test.tsx UserListPage.test.tsx RoleListPage.test.tsx`
Expected: FAIL

- [ ] **Step 3: 先改不依赖后端新增动作的页面**

把以下页面改为原型视觉，但继续使用真实现有 CRUD：

- `ProjectTemplateListPage.tsx`
- `ModelListPage.tsx`
- `UserListPage.tsx`
- `RoleListPage.tsx`
- `AuditLogPage.tsx`

页面页头统一替换为：

```tsx
<ConsolePageHeader
  title="系统用户中心"
  description="在此维护后台账号、超级管理员标记与角色分配。"
  action={<button type="button">新增用户</button>}
/>
```

- [ ] **Step 4: 最后改机器人页，先保留测试按钮占位但走真实 mutation 接口名**

在 `frontend/src/pages/bots/BotListPage.tsx` 预先接入待新增的 `testBot` mutation 调用位：

```tsx
const testMutation = useMutation({
  mutationFn: (botId: number) => testBot(botId),
  onSuccess: async () => {
    await queryClient.invalidateQueries({ queryKey: ["bots", "list"] });
  },
});
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ModelListPage.test.tsx UserListPage.test.tsx RoleListPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/projects/ProjectTemplateListPage.tsx frontend/src/pages/models/ModelListPage.tsx frontend/src/pages/bots/BotListPage.tsx frontend/src/pages/system/UserListPage.tsx frontend/src/pages/system/RoleListPage.tsx frontend/src/pages/system/AuditLogPage.tsx frontend/src/pages/models/ModelListPage.test.tsx frontend/src/pages/system/UserListPage.test.tsx frontend/src/pages/system/RoleListPage.test.tsx
git commit -m "feat(frontend): migrate admin data domain pages to console UI"
```

### Task 5: 新增通知机器人测试与审计日志 purge 后端能力，并接前端真实动作

**Files:**
- Modify: `backend/app/api/routes/notification_bots.py`
- Modify: `backend/app/api/routes/audit_logs.py`
- Modify: `backend/app/schemas/notification_bot.py`
- Modify: `backend/app/schemas/audit_log.py`
- Modify: `backend/app/services/notification_bot_service.py`
- Modify: `backend/app/services/audit_log_service.py`
- Modify: `frontend/src/features/bots/api.ts`
- Modify: `frontend/src/features/system/api.ts`
- Modify: `frontend/src/pages/bots/BotListPage.tsx`
- Modify: `frontend/src/pages/system/AuditLogPage.tsx`
- Test: `backend/tests/integration/test_notification_bots_api.py`
- Test: `backend/tests/integration/test_audit_logs_api.py`

- [ ] **Step 1: 先写后端测试**

在 `backend/tests/integration/test_notification_bots_api.py` 增加：

```python
async def test_test_notification_bot_updates_last_test_fields(client, admin_token, seeded_bot):
    response = await client.post(
        f"/api/v1/notification-bots/{seeded_bot.id}/test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["last_test_status"] in {"success", "failed"}
    assert payload["last_test_at"] is not None
```

在 `backend/tests/integration/test_audit_logs_api.py` 增加：

```python
async def test_purge_audit_logs_keeps_system_audit_entry(client, super_admin_token):
    response = await client.post(
        "/api/v1/audit-logs/purge",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )

    assert response.status_code == 202
    assert response.json()["purged_count"] >= 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_notification_bots_api.py tests/integration/test_audit_logs_api.py -q`
Expected: FAIL

- [ ] **Step 3: 添加 route、schema 与 service**

在 `backend/app/api/routes/notification_bots.py` 增加：

```python
@router.post(
    "/{bot_id}/test",
    response_model=NotificationBotResponse,
    summary="测试通知机器人",
)
async def test_notification_bot(
    request: Request,
    bot_id: int,
    current_user: User = Depends(require_permission("notification_bot:update")),
    service: NotificationBotService = Depends(),
) -> NotificationBotResponse:
    audit_context = AuditLogService.build_context(
        request=request,
        current_user=current_user,
        action="notification_bot.test",
        resource_type="notification_bot",
        response_status=status.HTTP_200_OK,
    )
    return await service.test_bot(current_user, bot_id, audit_context)
```

在 `backend/app/api/routes/audit_logs.py` 增加：

```python
@router.post(
    "/purge",
    summary="清理业务审计日志",
)
async def purge_audit_logs(
    request: Request,
    current_user: User = Depends(require_permission("audit_log:purge")),
    service: AuditLogService = Depends(),
) -> dict[str, int]:
    purged_count = await service.purge_business_logs(current_user, request)
    return {"purged_count": purged_count}
```

- [ ] **Step 4: 接前端真实动作**

修改 `frontend/src/features/bots/api.ts`：

```ts
export async function testBot(botId: number) {
  const response = await http.post<NotificationBotResponse>(`/notification-bots/${botId}/test`);
  return response.data;
}
```

修改 `frontend/src/features/system/api.ts`：

```ts
export async function purgeAuditLogs() {
  const response = await http.post<{ purged_count: number }>("/audit-logs/purge");
  return response.data;
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_notification_bots_api.py tests/integration/test_audit_logs_api.py -q`
Expected: PASS

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- BotListPage.test.tsx AuditLogPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/notification_bots.py backend/app/api/routes/audit_logs.py backend/app/schemas/notification_bot.py backend/app/schemas/audit_log.py backend/app/services/notification_bot_service.py backend/app/services/audit_log_service.py backend/tests/integration/test_notification_bots_api.py backend/tests/integration/test_audit_logs_api.py frontend/src/features/bots/api.ts frontend/src/features/system/api.ts frontend/src/pages/bots/BotListPage.tsx frontend/src/pages/system/AuditLogPage.tsx
git commit -m "feat: add bot testing and audit log purge flows"
```

### Task 6: 扩展仪表盘聚合接口并迁移高保真 Dashboard 页面

**Files:**
- Modify: `backend/app/api/routes/dashboard.py`
- Modify: `backend/app/schemas/dashboard.py`
- Modify: `backend/app/services/dashboard_service.py`
- Modify: `frontend/src/features/dashboard/api.ts`
- Modify: `frontend/src/pages/dashboard/DashboardPage.tsx`
- Test: `backend/tests/integration/test_dashboard_api.py`

- [ ] **Step 1: 写仪表盘聚合测试**

在 `backend/tests/integration/test_dashboard_api.py` 增加：

```python
async def test_dashboard_overview_returns_recent_reviews_and_chart_data(client, admin_token):
    response = await client.get(
        "/api/v1/dashboard/overview",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "recent_reviews" in payload
    assert "project_chart" in payload
    assert "member_chart" in payload
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_dashboard_api.py -q`
Expected: FAIL

- [ ] **Step 3: 扩展 schema 和 service**

在 `backend/app/schemas/dashboard.py` 增加：

```python
class DashboardChartPoint(BaseModel):
    name: str
    commits: int
    avg_score: float
    additions: int
    deletions: int


class DashboardRecentReviewItem(BaseModel):
    id: int
    project_name: str
    title: str | None = None
    branch: str | None = None
    commit_hash: str | None = None
    committer: str | None = None
    score: float | None = None
    review_status: str
    summary: str | None = None
    created_at: datetime
```

- [ ] **Step 4: 用扩展后的 overview 改写前端 DashboardPage**

在 `frontend/src/pages/dashboard/DashboardPage.tsx` 中改用一条 overview query：

```tsx
const { data, isLoading } = useQuery({
  queryKey: ["dashboard", "overview"],
  queryFn: getDashboardOverview,
});
```

并用 `ConsoleStatCard` 渲染：

```tsx
<ConsoleStatCard label="项目总数" value={data?.total_projects ?? 0} />
<ConsoleStatCard label="启用项目" value={data?.active_projects ?? 0} />
<ConsoleStatCard label="审查记录" value={data?.total_review_records ?? 0} />
<ConsoleStatCard label="平均评分" value={Number(data?.average_score ?? 0).toFixed(1)} />
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_dashboard_api.py -q`
Expected: PASS

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- DashboardPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/dashboard.py backend/app/schemas/dashboard.py backend/app/services/dashboard_service.py backend/tests/integration/test_dashboard_api.py frontend/src/features/dashboard/api.ts frontend/src/pages/dashboard/DashboardPage.tsx
git commit -m "feat: migrate dashboard to full fidelity overview"
```

### Task 7: 扩展项目接口、增加真实触发审查，并迁移项目管理页

**Files:**
- Modify: `backend/app/api/routes/projects.py`
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/services/project_service.py`
- Modify: `backend/app/services/review_execution_service.py`
- Modify: `frontend/src/features/projects/api.ts`
- Modify: `frontend/src/pages/projects/ProjectListPage.tsx`
- Test: `backend/tests/integration/test_projects_api.py`
- Test: `frontend/src/pages/projects/ProjectListPage.test.tsx`

- [ ] **Step 1: 先写项目列表增强与手动触发审查测试**

在 `backend/tests/integration/test_projects_api.py` 增加：

```python
async def test_project_list_contains_console_summary_fields(client, admin_token):
    response = await client.get(
        "/api/v1/projects?page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert "settings" in item
```

```python
async def test_trigger_review_creates_execution(client, admin_token, seeded_project):
    response = await client.post(
        f"/api/v1/projects/{seeded_project.id}/review-executions",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_projects_api.py -q`
Expected: FAIL

- [ ] **Step 3: 增加触发审查 route 与前端 API**

在 `backend/app/api/routes/projects.py` 增加：

```python
@router.post(
    "/{project_id}/review-executions",
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动触发项目审查",
)
async def trigger_project_review(
    project_id: int,
    current_user: User = Depends(require_permission("project:trigger-review")),
    review_service: ReviewExecutionService = Depends(),
) -> dict[str, str]:
    await review_service.enqueue_manual_review(current_user, project_id)
    return {"status": "queued"}
```

修改 `frontend/src/features/projects/api.ts`：

```ts
export async function triggerProjectReview(projectId: number) {
  const response = await http.post<{ status: string }>(`/projects/${projectId}/review-executions`);
  return response.data;
}
```

- [ ] **Step 4: 把项目页改为原型卡片布局，并把“立即监测”保留为进入工作区动作**

在 `frontend/src/pages/projects/ProjectListPage.tsx`：

```tsx
<button
  type="button"
  onClick={() => navigate(`/projects/${project.id}/agent`)}
  disabled={!project.enabled}
>
  立即监测
</button>
```

另在项目卡片或页头增加真实触发审查按钮：

```tsx
<button
  type="button"
  onClick={() => triggerReviewMutation.mutate(project.id)}
>
  触发真实审查
</button>
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_projects_api.py -q`
Expected: PASS

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ProjectListPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/projects.py backend/app/schemas/project.py backend/app/services/project_service.py backend/app/services/review_execution_service.py backend/tests/integration/test_projects_api.py frontend/src/features/projects/api.ts frontend/src/pages/projects/ProjectListPage.tsx frontend/src/pages/projects/ProjectListPage.test.tsx
git commit -m "feat: migrate project management and add review trigger"
```

### Task 8: 扩展 Agent 历史恢复与 richer SSE 事件，并迁移高保真项目对话工作区

**Files:**
- Modify: `backend/app/api/routes/agent.py`
- Modify: `backend/app/schemas/agent.py`
- Modify: `backend/app/services/agent_session_service.py`
- Modify: `frontend/src/features/agent/api.ts`
- Modify: `frontend/src/lib/api/types.ts`
- Modify: `frontend/src/pages/projects/ProjectAgentPage.tsx`
- Test: `backend/tests/integration/test_agent_api.py`
- Test: `backend/tests/integration/test_agent_sse.py`
- Test: `frontend/src/pages/projects/ProjectAgentPage.test.tsx`

- [ ] **Step 1: 先写 agent 历史恢复和事件流测试**

在 `backend/tests/integration/test_agent_api.py` 增加：

```python
async def test_get_agent_session_messages_returns_history(client, admin_token, seeded_agent_session):
    response = await client.get(
        f"/api/v1/projects/{seeded_agent_session.project_id}/agent/sessions/{seeded_agent_session.id}/messages",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json()["items"], list)
```

在 `backend/tests/integration/test_agent_sse.py` 增加：

```python
async def test_agent_stream_emits_trace_stages(client, admin_token, seeded_agent_session):
    response = await client.get(
        f"/api/v1/projects/{seeded_agent_session.project_id}/agent/sessions/{seeded_agent_session.id}/stream",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    body = (await response.aread()).decode()
    assert "event: run.started" in body
    assert "event: assistant.completed" in body
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: FAIL

- [ ] **Step 3: 补齐后端 session detail / messages / SSE 事件**

在 `backend/app/api/routes/agent.py` 增加：

```python
@router.get(
    "/sessions/{session_id}/messages",
    summary="获取 Repo Agent 会话历史消息",
)
async def list_agent_messages(
    project_id: int,
    session_id: int,
    current_user: User = Depends(require_permission("project:read")),
    service: AgentSessionService = Depends(),
) -> dict[str, list[AgentMessageResponse]]:
    del current_user
    items = await service.list_messages(project_id, session_id)
    return {"items": items}
```

在 `backend/app/schemas/agent.py` 扩展事件 payload：

```python
class AgentSSEEventResponse(BaseModel):
    event_type: str
    sequence: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    run_id: int | None = None
    message_id: int | None = None
```

- [ ] **Step 4: 将前端 `ProjectAgentPage` 改写为原型式会话侧栏 + trace 区**

至少引入以下状态：

```tsx
const [sidebarOpen, setSidebarOpen] = useState(true);
const [showCreateForm, setShowCreateForm] = useState(false);
const [traceExpanded, setTraceExpanded] = useState(true);
const [streamingContent, setStreamingContent] = useState("");
const [traceSteps, setTraceSteps] = useState<ConsoleTraceStep[]>([]);
```

流式事件渲染逻辑：

```tsx
if (event.event === "assistant.delta") {
  setStreamingContent((current) => current + String(event.data.payload?.delta ?? ""));
}

if (event.event === "tool.completed") {
  setTraceSteps((current) => [...current, toConsoleTraceStep(event)]);
}
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: PASS

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ProjectAgentPage.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/agent.py backend/app/schemas/agent.py backend/app/services/agent_session_service.py backend/tests/integration/test_agent_api.py backend/tests/integration/test_agent_sse.py frontend/src/features/agent/api.ts frontend/src/lib/api/types.ts frontend/src/pages/projects/ProjectAgentPage.tsx frontend/src/pages/projects/ProjectAgentPage.test.tsx
git commit -m "feat: migrate project agent workspace to full fidelity console"
```

### Task 9: 迁移审查记录详情、成员分析与联调收口

**Files:**
- Modify: `frontend/src/pages/reviews/ReviewRecordListPage.tsx`
- Modify: `frontend/src/pages/reviews/ReviewRecordDetailPage.tsx`
- Modify: `frontend/src/pages/analytics/MemberAnalyticsPage.tsx`
- Modify: `frontend/src/features/reviews/api.ts`
- Modify: `frontend/src/features/member-analytics/api.ts`
- Test: `frontend/src/pages/reviews/ReviewRecordListPage.test.tsx`

- [ ] **Step 1: 写审查记录高保真断言**

在 `frontend/src/pages/reviews/ReviewRecordListPage.test.tsx` 增加：

```tsx
it("renders console review records experience", async () => {
  render(<ReviewRecordListPage />);

  expect(await screen.findByText("智能审查记录控制中心")).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/按照项目名称、提交标题、作者进行全局过滤/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ReviewRecordListPage.test.tsx`
Expected: FAIL

- [ ] **Step 3: 改造审查记录与成员分析页面**

在 `frontend/src/pages/reviews/ReviewRecordListPage.tsx` 用 `ConsolePageHeader`、原型式 list item 和 `ConsolePagination` 替换现有布局。

记录项标题区至少保持：

```tsx
<span>{record.project_name_snapshot}</span>
<span>{record.branch} @ {record.last_commit_id ?? "-"}</span>
<h3>{record.title ?? "未命名审查事件"}</h3>
```

在 `frontend/src/pages/analytics/MemberAnalyticsPage.tsx` 以榜单卡片和风险摘要替换旧表格布局。

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run test -- ReviewRecordListPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/reviews/ReviewRecordListPage.tsx frontend/src/pages/reviews/ReviewRecordDetailPage.tsx frontend/src/pages/analytics/MemberAnalyticsPage.tsx frontend/src/features/reviews/api.ts frontend/src/features/member-analytics/api.ts frontend/src/pages/reviews/ReviewRecordListPage.test.tsx
git commit -m "feat(frontend): migrate reviews and member analytics to console UI"
```

### Task 10: 全量验证、文档回写与收尾

**Files:**
- Modify: `frontend/src/App.test.tsx`
- Modify: `backend/README.md`
- Modify: `frontend/README.md` (create if absent)
- Create: `docs/verification/2026-06-05-console-full-fidelity-migration-verification.md`

- [ ] **Step 1: 写最小回归清单文档**

创建 `docs/verification/2026-06-05-console-full-fidelity-migration-verification.md`：

```md
# Console Full-Fidelity Migration Verification

- Login visual parity verified
- Dashboard data is real
- Project cards navigate to agent workspace
- Bot test writes real status
- Audit purge is permission-gated
- Agent stream replays history and trace
```

- [ ] **Step 2: 跑前端测试**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm test -- --runInBand`
Expected: PASS

- [ ] **Step 3: 跑后端测试**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/backend && pytest tests/integration/test_dashboard_api.py tests/integration/test_projects_api.py tests/integration/test_notification_bots_api.py tests/integration/test_audit_logs_api.py tests/integration/test_agent_api.py tests/integration/test_agent_sse.py -q`
Expected: PASS

- [ ] **Step 4: 跑前端构建**

Run: `cd /Users/jacob/GitProject/ai-code-reviewer/frontend && npm run build`
Expected: PASS with generated `dist/`

- [ ] **Step 5: Commit**

```bash
git add docs/verification/2026-06-05-console-full-fidelity-migration-verification.md frontend/src/App.test.tsx backend/README.md frontend/README.md
git commit -m "docs: add console migration verification notes"
```

---

## Spec Coverage Check

- 登录、导航和共享壳子：Task 1, Task 3
- 模板、模型、机器人、RBAC、日志：Task 4, Task 5
- 仪表盘：Task 6
- 项目管理与真实触发审查：Task 7
- 项目对话流：Task 8
- 审查记录与成员分析：Task 9
- 联调与验证：Task 10

未发现 spec 中要求但计划未覆盖的模块。

## Placeholder Scan

- 未使用 `TODO`、`TBD`、`implement later` 之类占位词。
- 每个任务均包含具体文件、测试、命令和提交边界。

## Type Consistency Check

- 前端项目触发接口统一命名为 `triggerProjectReview`。
- 机器人测试接口统一命名为 `testBot`。
- Agent SSE 事件统一使用点号命名，如 `run.started`、`assistant.completed`、`tool.completed`。
- serializer 输出项目卡片统一使用 `enabled`、`reviewEnabled`、`scoreAverage`、`lastReviewAt` 字段。
