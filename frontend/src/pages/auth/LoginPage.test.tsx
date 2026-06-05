import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { AuthProvider } from "../../lib/auth/auth-context";
import { http } from "../../lib/api/http";
import { tokenStore } from "../../lib/auth/token-store";
import { createQueryClient } from "../../lib/query/query-client";
import { DashboardPage } from "../dashboard/DashboardPage";
import { LoginPage } from "./LoginPage";

const { mockHttpGet, mockHttpPost, mockTokenStore } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockTokenStore: {
    load: vi.fn(() => null),
    save: vi.fn(),
    clear: vi.fn(),
  },
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    post: mockHttpPost,
    get: mockHttpGet,
  },
}));

vi.mock("../../lib/auth/token-store", () => ({
  tokenStore: mockTokenStore,
}));

function renderLoginPage() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/login"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test("提交登录表单后保存令牌", async () => {
  mockHttpPost.mockResolvedValueOnce({
    data: {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_in: 900,
      must_change_password: false,
    },
  });
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
      roles: [],
      permissions: [],
      menus: [],
      must_change_password: false,
    },
  });

  renderLoginPage();

  expect(screen.getByText("AI Code Review Console")).toBeInTheDocument();
  expect(screen.getByText("超级管理员")).toBeInTheDocument();
  expect(screen.getByText("开发工程师")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "进入控制台" })).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("用户名"), {
    target: { value: "admin" },
  });
  fireEvent.change(screen.getByLabelText("密码"), {
    target: { value: "jdw112233" },
  });
  fireEvent.click(screen.getByRole("button", { name: "进入控制台" }));

  await waitFor(() => {
    expect(http.post).toHaveBeenCalledWith("/auth/login", {
      username: "admin",
      password: "jdw112233",
    });
    expect(tokenStore.save).toHaveBeenCalledWith(
      expect.objectContaining({
        access_token: "access-token",
        refresh_token: "refresh-token",
      })
    );
  });
});

test("首次登录需要改密时展示改密表单", async () => {
  mockHttpPost.mockResolvedValueOnce({
    data: {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_in: 900,
      must_change_password: true,
    },
  });
  mockHttpGet.mockResolvedValueOnce({
    data: {
      id: 1,
      username: "admin",
      nickname: "管理员",
      email: "admin@example.com",
      phone: null,
      is_active: true,
      is_superuser: true,
      must_change_password: true,
      roles: [],
    },
  });

  renderLoginPage();

  fireEvent.change(screen.getByLabelText("用户名"), {
    target: { value: "admin" },
  });
  fireEvent.change(screen.getByLabelText("密码"), {
    target: { value: "jdw112233" },
  });
  fireEvent.click(screen.getByRole("button", { name: "进入控制台" }));

  expect(await screen.findByText("首次登录需要先修改密码")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "修改密码" })).toBeInTheDocument();
  expect(http.get).toHaveBeenCalledWith("/me/profile");
});
