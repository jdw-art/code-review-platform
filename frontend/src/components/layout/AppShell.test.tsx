import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { http } from "../../lib/api/http";
import { AuthProvider } from "../../lib/auth/auth-context";
import { tokenStore } from "../../lib/auth/token-store";
import { createQueryClient } from "../../lib/query/query-client";
import { DashboardPage } from "../../pages/dashboard/DashboardPage";
import { AppShell } from "./AppShell";

const { mockHttpGet, mockHttpPost, mockTokenStore } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockTokenStore: {
    load: vi.fn(() => ({
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_in: 900,
      must_change_password: false,
    })),
    save: vi.fn(),
    clear: vi.fn(),
  },
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
  },
}));

vi.mock("../../lib/auth/token-store", () => ({
  tokenStore: mockTokenStore,
}));

function renderAppShell() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/dashboard"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AuthProvider>
          <Routes>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test("renders console shell navigation and topbar labels", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      user: {
        id: 1,
        username: "admin",
        nickname: "管理员",
        email: "admin@example.com",
        phone: null,
        is_active: true,
        is_superuser: true,
      },
      roles: [
        {
          id: 1,
          name: "超级管理员",
          code: "super_admin",
        },
      ],
      permissions: [],
      menus: [
        {
          id: 1,
          parent_id: null,
          name: "仪表盘",
          path: "/dashboard",
          component: null,
          icon: "layout-dashboard",
          sort: 10,
          visible: true,
          redirect: null,
          meta: null,
          children: [],
        },
        {
          id: 2,
          parent_id: null,
          name: "系统管理",
          path: "/system",
          component: null,
          icon: "folder-kanban",
          sort: 20,
          visible: true,
          redirect: null,
          meta: null,
          children: [
            {
              id: 3,
              parent_id: 2,
              name: "系统日志",
              path: "/system/logs",
              component: null,
              icon: "scroll-text",
              sort: 30,
              visible: true,
              redirect: null,
              meta: null,
              children: [],
            },
          ],
        },
      ],
      must_change_password: false,
    },
  });

  renderAppShell();

  expect(await screen.findByText("AI Code Review")).toBeInTheDocument();
  expect(screen.getByText("欢迎回来")).toBeInTheDocument();
  expect(screen.getByText("系统日志")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "退出登录" })).toBeInTheDocument();
  expect(http.get).toHaveBeenCalledWith("/me/access-context");
  expect(tokenStore.load).toHaveBeenCalled();
});

test("renders an unassigned role label when the authenticated user has no roles", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      user: {
        id: 1,
        username: "reviewer",
        nickname: "审查员",
        email: "reviewer@example.com",
        phone: null,
        is_active: true,
        is_superuser: false,
      },
      roles: [],
      permissions: [],
      menus: [
        {
          id: 1,
          parent_id: null,
          name: "仪表盘",
          path: "/dashboard",
          component: null,
          icon: "layout-dashboard",
          sort: 10,
          visible: true,
          redirect: null,
          meta: null,
          children: [],
        },
      ],
      must_change_password: true,
    },
  });

  renderAppShell();

  expect(await screen.findByText("reviewer")).toBeInTheDocument();
  expect(screen.getByText("未分配角色")).toBeInTheDocument();
  expect(screen.queryByText("超级管理员")).not.toBeInTheDocument();
});
