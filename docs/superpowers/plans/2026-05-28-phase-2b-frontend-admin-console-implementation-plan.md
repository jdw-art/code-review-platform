# Phase 2B Frontend Admin Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为第二阶段管理后台落地最小可用前端壳子，覆盖登录、仪表盘、项目/模板、审查记录、成员分析、模型、机器人、系统日志以及用户/角色管理页面。

**Architecture:** 在空的 `frontend/` 目录中基于 Vite + React + TypeScript + Tailwind 搭建单页后台应用。使用 React Router 管理页面路由，使用 Axios 统一调用后端接口，使用 TanStack Query 管理服务端状态，菜单以 `/api/v1/me/menus` 为准动态渲染。

**Tech Stack:** React 18、TypeScript、Vite、Tailwind CSS、React Router、Axios、TanStack Query、Vitest、Testing Library

---

## File Map

### Root frontend scaffolding

- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/vitest.config.ts`
- `frontend/postcss.config.js`
- `frontend/tailwind.config.ts`
- `frontend/index.html`

### App bootstrap and shared files

- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/test/setup.ts`
- `frontend/src/lib/api/http.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/auth/token-store.ts`
- `frontend/src/lib/auth/auth-context.tsx`
- `frontend/src/lib/query/query-client.ts`
- `frontend/src/routes/router.tsx`

### Shared UI building blocks

- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/SidebarNav.tsx`
- `frontend/src/components/layout/Topbar.tsx`
- `frontend/src/components/common/PageCard.tsx`
- `frontend/src/components/common/DataTable.tsx`
- `frontend/src/components/common/StatusBadge.tsx`
- `frontend/src/components/common/DrawerForm.tsx`
- `frontend/src/components/common/StatCard.tsx`

### Pages

- `frontend/src/pages/auth/LoginPage.tsx`
- `frontend/src/pages/dashboard/DashboardPage.tsx`
- `frontend/src/pages/projects/ProjectListPage.tsx`
- `frontend/src/pages/projects/ProjectTemplateListPage.tsx`
- `frontend/src/pages/reviews/ReviewRecordListPage.tsx`
- `frontend/src/pages/reviews/ReviewRecordDetailPage.tsx`
- `frontend/src/pages/analytics/MemberAnalyticsPage.tsx`
- `frontend/src/pages/models/ModelListPage.tsx`
- `frontend/src/pages/bots/BotListPage.tsx`
- `frontend/src/pages/system/AuditLogPage.tsx`
- `frontend/src/pages/system/UserListPage.tsx`
- `frontend/src/pages/system/RoleListPage.tsx`

### Domain API wrappers

- `frontend/src/features/projects/api.ts`
- `frontend/src/features/project-templates/api.ts`
- `frontend/src/features/reviews/api.ts`
- `frontend/src/features/dashboard/api.ts`
- `frontend/src/features/member-analytics/api.ts`
- `frontend/src/features/models/api.ts`
- `frontend/src/features/bots/api.ts`
- `frontend/src/features/system/api.ts`

### Tests

- `frontend/src/pages/auth/LoginPage.test.tsx`
- `frontend/src/components/layout/AppShell.test.tsx`
- `frontend/src/pages/projects/ProjectListPage.test.tsx`
- `frontend/src/pages/reviews/ReviewRecordListPage.test.tsx`

### Task 1: Scaffold the Frontend Workspace

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/index.css`
- Create: `frontend/src/test/setup.ts`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Write the failing smoke test**

```tsx
import { render, screen } from "@testing-library/react";

import App from "./App";

test("renders admin shell title placeholder", () => {
  render(<App />);
  expect(screen.getByText("AI Code Review")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the Vite app, Vitest config, and `App` component do not exist.

- [ ] **Step 3: Write the minimal implementation**

```json
// frontend/package.json
{
  "name": "ai-code-reviewer-frontend",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest"
  },
  "dependencies": {
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.0",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  }
}
```

```tsx
// frontend/src/App.tsx
export default function App() {
  return <div className="min-h-screen bg-slate-100 text-slate-900">AI Code Review</div>;
}
```

```css
/* frontend/src/styles/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  @apply bg-slate-100 text-slate-900 antialiased;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend
npm install
npm test -- --run
```

Expected: PASS for the smoke test and no missing Tailwind/Vitest config errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/vitest.config.ts frontend/postcss.config.js frontend/tailwind.config.ts frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/styles/index.css frontend/src/test/setup.ts frontend/src/App.test.tsx
git commit -m "feat(frontend): scaffold admin console workspace"
```

### Task 2: Implement Auth Flow and Layout Shell

**Files:**
- Create: `frontend/src/lib/api/http.ts`
- Create: `frontend/src/lib/auth/token-store.ts`
- Create: `frontend/src/lib/auth/auth-context.tsx`
- Create: `frontend/src/lib/query/query-client.ts`
- Create: `frontend/src/routes/router.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/layout/SidebarNav.tsx`
- Create: `frontend/src/components/layout/Topbar.tsx`
- Create: `frontend/src/pages/auth/LoginPage.tsx`
- Create: `frontend/src/pages/dashboard/DashboardPage.tsx`
- Test: `frontend/src/pages/auth/LoginPage.test.tsx`
- Test: `frontend/src/components/layout/AppShell.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
test("submits login form and stores tokens", async () => {
  render(<LoginPage />);

  await user.type(screen.getByLabelText("用户名"), "admin");
  await user.type(screen.getByLabelText("密码"), "jdw112233");
  await user.click(screen.getByRole("button", { name: "登录" }));

  expect(mockTokenStore.save).toHaveBeenCalled();
});


test("renders menu items returned by /me/menus", async () => {
  render(<AppShell />);
  expect(await screen.findByText("项目管理")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run src/pages/auth/LoginPage.test.tsx src/components/layout/AppShell.test.tsx`

Expected: FAIL because auth context, API client, and app shell do not exist.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/lib/auth/token-store.ts
export const tokenStore = {
  load: () => JSON.parse(localStorage.getItem("auth") ?? "null"),
  save: (payload: TokenPair) => localStorage.setItem("auth", JSON.stringify(payload)),
  clear: () => localStorage.removeItem("auth"),
};
```

```tsx
// frontend/src/pages/auth/LoginPage.tsx
export function LoginPage() {
  const [form, setForm] = useState({ username: "", password: "" });
  const mutation = useMutation({
    mutationFn: (payload: { username: string; password: string }) =>
      http.post("/auth/login", payload).then((response) => response.data),
  });

  return (
    <form onSubmit={handleSubmit} className="mx-auto mt-24 max-w-md rounded-3xl bg-white p-8 shadow-sm">
      <label>用户名</label>
      <input value={form.username} />
      <label>密码</label>
      <input type="password" value={form.password} />
      <button type="submit">登录</button>
    </form>
  );
}
```

```tsx
// frontend/src/components/layout/AppShell.tsx
export function AppShell() {
  const { menuTree, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-slate-100">
      <SidebarNav menus={menuTree} />
      <main className="flex-1 p-8">
        <Topbar onLogout={logout} />
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run src/pages/auth/LoginPage.test.tsx src/components/layout/AppShell.test.tsx`

Expected: PASS and the auth shell can render menu-driven navigation.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/http.ts frontend/src/lib/auth/token-store.ts frontend/src/lib/auth/auth-context.tsx frontend/src/lib/query/query-client.ts frontend/src/routes/router.tsx frontend/src/components/layout/AppShell.tsx frontend/src/components/layout/SidebarNav.tsx frontend/src/components/layout/Topbar.tsx frontend/src/pages/auth/LoginPage.tsx frontend/src/pages/dashboard/DashboardPage.tsx frontend/src/pages/auth/LoginPage.test.tsx frontend/src/components/layout/AppShell.test.tsx
git commit -m "feat(frontend): add auth flow and admin shell"
```

### Task 3: Implement Project and Project Template Pages

**Files:**
- Create: `frontend/src/components/common/PageCard.tsx`
- Create: `frontend/src/components/common/DataTable.tsx`
- Create: `frontend/src/components/common/DrawerForm.tsx`
- Create: `frontend/src/features/projects/api.ts`
- Create: `frontend/src/features/project-templates/api.ts`
- Create: `frontend/src/pages/projects/ProjectListPage.tsx`
- Create: `frontend/src/pages/projects/ProjectTemplateListPage.tsx`
- Test: `frontend/src/pages/projects/ProjectListPage.test.tsx`

- [ ] **Step 1: Write the failing page test**

```tsx
test("renders project template table headers from backend contract", async () => {
  render(<ProjectTemplateListPage />);

  expect(await screen.findByText("模板名称")).toBeInTheDocument();
  expect(screen.getByText("文件扩展名")).toBeInTheDocument();
  expect(screen.getByText("Review 提示词")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run src/pages/projects/ProjectListPage.test.tsx`

Expected: FAIL because table components and project API wrappers do not exist.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/features/project-templates/api.ts
export async function listProjectTemplates(params: { page: number; page_size: number }) {
  const { data } = await http.get("/project-templates", { params });
  return data;
}
```

```tsx
// frontend/src/pages/projects/ProjectTemplateListPage.tsx
const columns = [
  { key: "name", title: "模板名称" },
  { key: "description", title: "描述" },
  { key: "file_extensions", title: "文件扩展名" },
  { key: "review_prompt_configured", title: "Review 提示词" },
];
```

```tsx
// frontend/src/pages/projects/ProjectListPage.tsx
export function ProjectListPage() {
  const { data } = useQuery({ queryKey: ["projects"], queryFn: () => listProjects({ page: 1, page_size: 20 }) });
  return <DataTable columns={columns} rows={data?.items ?? []} />;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run src/pages/projects/ProjectListPage.test.tsx`

Expected: PASS and the project/template pages render the business fields defined in the spec.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/common/PageCard.tsx frontend/src/components/common/DataTable.tsx frontend/src/components/common/DrawerForm.tsx frontend/src/features/projects/api.ts frontend/src/features/project-templates/api.ts frontend/src/pages/projects/ProjectListPage.tsx frontend/src/pages/projects/ProjectTemplateListPage.tsx frontend/src/pages/projects/ProjectListPage.test.tsx
git commit -m "feat(frontend): add project management pages"
```

### Task 4: Implement Model, Bot, and System Log Pages

**Files:**
- Create: `frontend/src/components/common/StatusBadge.tsx`
- Create: `frontend/src/features/models/api.ts`
- Create: `frontend/src/features/bots/api.ts`
- Create: `frontend/src/features/system/api.ts`
- Create: `frontend/src/pages/models/ModelListPage.tsx`
- Create: `frontend/src/pages/bots/BotListPage.tsx`
- Create: `frontend/src/pages/system/AuditLogPage.tsx`

- [ ] **Step 1: Write the failing rendering test**

```tsx
test("renders masked model api key column without plaintext secrets", async () => {
  render(<ModelListPage />);

  expect(await screen.findByText("模型名称")).toBeInTheDocument();
  expect(screen.queryByText("sk-live-secret")).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because the model/bot/system pages and status badge components do not exist.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/pages/models/ModelListPage.tsx
const columns = [
  { key: "name", title: "模型名称" },
  { key: "provider", title: "提供方" },
  { key: "model_code", title: "模型标识" },
  { key: "api_key_masked", title: "API Key" },
  { key: "last_test_status", title: "连通性" },
];
```

```tsx
// frontend/src/pages/system/AuditLogPage.tsx
const columns = [
  { key: "created_at", title: "时间" },
  { key: "username_snapshot", title: "操作人" },
  { key: "action", title: "操作" },
  { key: "resource_type", title: "资源类型" },
  { key: "result", title: "结果" },
];
```

```tsx
// frontend/src/components/common/StatusBadge.tsx
export function StatusBadge({ value }: { value: string | boolean }) {
  const text = value === true ? "启用" : value === false ? "停用" : String(value);
  return <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs text-emerald-700">{text}</span>;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run`

Expected: PASS and no plaintext secrets render in the model/bot pages.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/common/StatusBadge.tsx frontend/src/features/models/api.ts frontend/src/features/bots/api.ts frontend/src/features/system/api.ts frontend/src/pages/models/ModelListPage.tsx frontend/src/pages/bots/BotListPage.tsx frontend/src/pages/system/AuditLogPage.tsx
git commit -m "feat(frontend): add model bot and audit log pages"
```

### Task 5: Implement Review Records, Member Analytics, and Dashboard

**Files:**
- Create: `frontend/src/components/common/StatCard.tsx`
- Create: `frontend/src/features/reviews/api.ts`
- Create: `frontend/src/features/dashboard/api.ts`
- Create: `frontend/src/features/member-analytics/api.ts`
- Create: `frontend/src/pages/reviews/ReviewRecordListPage.tsx`
- Create: `frontend/src/pages/reviews/ReviewRecordDetailPage.tsx`
- Create: `frontend/src/pages/analytics/MemberAnalyticsPage.tsx`
- Modify: `frontend/src/pages/dashboard/DashboardPage.tsx`
- Test: `frontend/src/pages/reviews/ReviewRecordListPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
test("renders review record business fields from page contract", async () => {
  render(<ReviewRecordListPage />);

  expect(await screen.findByText("项目名称")).toBeInTheDocument();
  expect(screen.getByText("事件类型")).toBeInTheDocument();
  expect(screen.getByText("评分")).toBeInTheDocument();
  expect(screen.getByText("提交信息")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run src/pages/reviews/ReviewRecordListPage.test.tsx`

Expected: FAIL because review, dashboard, and analytics pages are not implemented.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/pages/reviews/ReviewRecordListPage.tsx
const columns = [
  { key: "project_name_snapshot", title: "项目名称" },
  { key: "event_type", title: "事件类型" },
  { key: "author", title: "作者" },
  { key: "score", title: "评分" },
  { key: "commit_messages", title: "提交信息" },
];
```

```tsx
// frontend/src/pages/dashboard/DashboardPage.tsx
export function DashboardPage() {
  const { data } = useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: () => http.get("/dashboard/overview").then((response) => response.data),
  });

  return (
    <div className="grid gap-6 md:grid-cols-4">
      <StatCard label="项目总数" value={data?.total_projects ?? 0} />
      <StatCard label="审查记录" value={data?.total_review_records ?? 0} />
      <StatCard label="平均评分" value={data?.average_score ?? 0} />
    </div>
  );
}
```

```tsx
// frontend/src/pages/analytics/MemberAnalyticsPage.tsx
export function MemberAnalyticsPage() {
  const { data } = useMemberAnalyticsQuery();
  return <DataTable columns={columns} rows={data?.items ?? []} />;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --run src/pages/reviews/ReviewRecordListPage.test.tsx`

Expected: PASS and the page contract fields from the spec are visible.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/common/StatCard.tsx frontend/src/features/reviews/api.ts frontend/src/features/dashboard/api.ts frontend/src/features/member-analytics/api.ts frontend/src/pages/reviews/ReviewRecordListPage.tsx frontend/src/pages/reviews/ReviewRecordDetailPage.tsx frontend/src/pages/analytics/MemberAnalyticsPage.tsx frontend/src/pages/dashboard/DashboardPage.tsx frontend/src/pages/reviews/ReviewRecordListPage.test.tsx
git commit -m "feat(frontend): add review and analytics pages"
```

### Task 6: Add User/Role Management Pages and Final Verification

**Files:**
- Create: `frontend/src/pages/system/UserListPage.tsx`
- Create: `frontend/src/pages/system/RoleListPage.tsx`
- Modify: `frontend/src/routes/router.tsx`
- Modify: `frontend/src/components/layout/SidebarNav.tsx`

- [ ] **Step 1: Write the failing route assertions**

```tsx
test("routes include user and role management pages", () => {
  const renderWithRouter = (path: string) =>
    render(<MemoryRouter initialEntries={[path]}><AppShell /></MemoryRouter>);

  renderWithRouter("/system/users");
  expect(screen.getByText("用户管理")).toBeInTheDocument();

  renderWithRouter("/system/roles");
  expect(screen.getByText("角色管理")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --run`

Expected: FAIL because these routes and pages are not yet registered.

- [ ] **Step 3: Write the minimal implementation**

```tsx
// frontend/src/pages/system/UserListPage.tsx
export function UserListPage() {
  const { data } = useQuery({
    queryKey: ["users"],
    queryFn: () => http.get("/users").then((response) => response.data),
  });
  return <DataTable columns={userColumns} rows={data ?? []} />;
}
```

```tsx
// frontend/src/routes/router.tsx
{
  path: "/system/users",
  element: <UserListPage />,
},
{
  path: "/system/roles",
  element: <RoleListPage />,
}
```

- [ ] **Step 4: Run full frontend verification**

Run:

```bash
cd frontend
npm test -- --run
npm run build
```

Expected:

- all frontend tests pass
- Vite production build succeeds without type errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/system/UserListPage.tsx frontend/src/pages/system/RoleListPage.tsx frontend/src/routes/router.tsx frontend/src/components/layout/SidebarNav.tsx
git commit -m "feat(frontend): complete admin console shell"
```
