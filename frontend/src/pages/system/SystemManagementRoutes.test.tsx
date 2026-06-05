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
  mockHttpGet.mockResolvedValueOnce({
    data: [],
  });

  renderRouteAt("/system/users");

  expect(await screen.findByText("系统用户中心")).toBeInTheDocument();
  expect(screen.getByText("用户管理")).toBeInTheDocument();
});

test("角色矩阵路由渲染控制台标题", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: [],
  });

  renderRouteAt("/system/roles");

  expect(await screen.findByText("智能角色矩阵")).toBeInTheDocument();
  expect(screen.getByText("角色管理")).toBeInTheDocument();
});

test("审计日志别名路由重定向后渲染控制台标题和激活导航", async () => {
  const protectedRoutes = routeConfig.find((route) => route.path === "/" && Array.isArray(route.children));
  const auditAliasRoute = protectedRoutes?.children?.find(
    (route) => route.path === "/system/audit-logs"
  );

  expect(isValidElement(auditAliasRoute?.element)).toBe(true);
  expect(auditAliasRoute?.element.props.to).toBe("/audit-logs");
  expect(auditAliasRoute?.element.props.replace).toBe(true);

  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [],
    },
  });

  renderRouteAt("/audit-logs");

  expect((await screen.findAllByText("系统审计日志")).length).toBeGreaterThanOrEqual(2);
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
