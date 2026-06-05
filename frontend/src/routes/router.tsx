import {
  createBrowserRouter,
  Navigate,
  Outlet,
  useLocation,
  type RouteObject,
} from "react-router-dom";

import { AppShell } from "../components/layout/AppShell";
import { useAuth } from "../lib/auth/auth-context";
import { LoginPage } from "../pages/auth/LoginPage";
import { BotListPage } from "../pages/bots/BotListPage";
import { DashboardPage } from "../pages/dashboard/DashboardPage";
import { ModelListPage } from "../pages/models/ModelListPage";
import { MemberAnalyticsPage } from "../pages/analytics/MemberAnalyticsPage";
import { ProjectAgentPage } from "../pages/projects/ProjectAgentPage";
import { ProjectListPage } from "../pages/projects/ProjectListPage";
import { ProjectTemplateListPage } from "../pages/projects/ProjectTemplateListPage";
import { ReviewRecordDetailPage } from "../pages/reviews/ReviewRecordDetailPage";
import { ReviewRecordListPage } from "../pages/reviews/ReviewRecordListPage";
import { AuditLogPage } from "../pages/system/AuditLogPage";
import { RoleListPage } from "../pages/system/RoleListPage";
import { UserListPage } from "../pages/system/UserListPage";

function LoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-6">
      <div className="rounded-3xl border border-slate-200 bg-white px-8 py-6 text-sm text-slate-600 shadow-sm">
        正在加载后台会话...
      </div>
    </main>
  );
}

function RootRedirect() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  return <Navigate replace to={status === "authenticated" ? "/dashboard" : "/login"} />;
}

function ProtectedLayout() {
  const location = useLocation();
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingScreen />;
  }

  if (status !== "authenticated") {
    return (
      <Navigate
        replace
        to="/login"
        state={{ from: location.pathname }}
      />
    );
  }

  return <AppShell />;
}

function PlaceholderPage() {
  const location = useLocation();

  return (
    <section className="rounded-[1.75rem] border border-dashed border-slate-300 bg-white px-6 py-8 shadow-sm">
      <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Coming Next</p>
      <h1 className="mt-3 text-2xl font-semibold text-slate-900">页面建设中</h1>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
        当前已经进入后台壳子，但 <code>{location.pathname}</code> 对应的业务页面会在后续任务中逐步接入真实列表与表单。
      </p>
    </section>
  );
}

/**
 * 路由树当前先保证认证、壳子和仪表盘进入路径正确，后续任务再逐页替换占位路由。
 */
export const routeConfig: RouteObject[] = [
  {
    path: "/",
    element: <RootRedirect />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: <ProtectedLayout />,
    children: [
      {
        path: "/dashboard",
        element: <DashboardPage />,
      },
      {
        path: "/projects",
        element: <ProjectListPage />,
      },
      {
        path: "/projects/:projectId/agent",
        element: <ProjectAgentPage />,
      },
      {
        path: "/project-templates",
        element: <ProjectTemplateListPage />,
      },
      {
        path: "/review-records",
        element: <ReviewRecordListPage />,
      },
      {
        path: "/review-records/:reviewRecordId",
        element: <ReviewRecordDetailPage />,
      },
      {
        path: "/member-analytics",
        element: <MemberAnalyticsPage />,
      },
      {
        path: "/models",
        element: <ModelListPage />,
      },
      {
        path: "/notification-bots",
        element: <BotListPage />,
      },
      {
        path: "/audit-logs",
        element: <AuditLogPage />,
      },
      {
        path: "/system",
        element: <Navigate replace to="/system/users" />,
      },
      {
        path: "/system/audit-logs",
        element: <Navigate replace to="/audit-logs" />,
      },
      {
        path: "/system/users",
        element: <UserListPage />,
      },
      {
        path: "/system/roles",
        element: <RoleListPage />,
      },
      {
        path: "*",
        element: <PlaceholderPage />,
      },
    ],
  },
];

export const router = createBrowserRouter(routeConfig);
