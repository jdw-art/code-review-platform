import { isValidElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { buildReturnToLocation, routeConfig } from "../../routes/router";

const { authState, mockHttpGet } = vi.hoisted(() => ({
  authState: {
    status: "authenticated" as const,
    user: {
      id: 1,
      username: "admin",
      nickname: "管理员",
      email: "admin@example.com",
      phone: null,
      is_active: true,
      is_superuser: true,
    },
    roles: [],
    permissions: [],
    menuTree: [
      {
        id: 1,
        parent_id: null,
        name: "项目管理",
        path: "/projects",
        component: null,
        icon: "folder-kanban",
        sort: 10,
        visible: true,
        redirect: null,
        meta: null,
        children: [
          {
            id: 2,
            parent_id: 1,
            name: "项目智能体",
            path: "/projects/1/agent",
            component: null,
            icon: "bot",
            sort: 20,
            visible: true,
            redirect: null,
            meta: null,
            children: [],
          },
        ],
      },
      {
        id: 3,
        parent_id: null,
        name: "系统审计日志",
        path: "/audit-logs",
        component: null,
        icon: "scroll-text",
        sort: 30,
        visible: true,
        redirect: null,
        meta: null,
        children: [],
      },
    ],
    mustChangePassword: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    refreshAccessContext: vi.fn(),
  },
  mockHttpGet: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
  },
}));

vi.mock("../../lib/auth/auth-context", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => authState,
}));

afterEach(() => {
  mockHttpGet.mockReset();
  vi.resetModules();
});

function renderRouteAt(path: string) {
  const queryClient = createQueryClient();
  const router = createMemoryRouter(routeConfig, {
    initialEntries: [path],
  });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );

  return router;
}

test("用户中心路由渲染控制台标题", async () => {
  mockHttpGet.mockResolvedValue({
    data: [],
  });

  renderRouteAt("/system/users");

  expect(
    await screen.findByRole("heading", { level: 2, name: "系统用户中心" })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建用户" })).toBeInTheDocument();
});

test("角色矩阵路由渲染控制台标题", async () => {
  mockHttpGet.mockResolvedValue({
    data: [],
  });

  renderRouteAt("/system/roles");

  expect(
    await screen.findByRole("heading", { level: 2, name: "角色权限矩阵" })
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新建角色" })).toBeInTheDocument();
});

test("审计日志别名路由重定向后渲染控制台标题和激活导航", async () => {
  const protectedRoutes = routeConfig.find((route) => route.path === "/" && Array.isArray(route.children));
  const auditAliasRoute = protectedRoutes?.children?.find(
    (route) => route.path === "/system/audit-logs"
  );
  const auditAliasElement = auditAliasRoute?.element;

  expect(isValidElement(auditAliasElement)).toBe(true);
  if (!isValidElement(auditAliasElement)) {
    throw new Error("审计日志别名路由元素缺失");
  }
  expect(auditAliasElement.props.to).toBe("/audit-logs");
  expect(auditAliasElement.props.replace).toBe(true);

  mockHttpGet.mockResolvedValue({
    data: {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderRouteAt("/audit-logs");

  expect(
    await screen.findByRole("heading", { level: 2, name: "审计日志观测台" })
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "系统审计日志" })).toHaveClass("bg-indigo-50");
});

test("受保护路由返回地址保留完整深链接", () => {
  expect(
    buildReturnToLocation({
      pathname: "/review-records/42",
      search: "?tab=diff",
      hash: "#comments",
    })
  ).toBe("/review-records/42?tab=diff#comments");
});
