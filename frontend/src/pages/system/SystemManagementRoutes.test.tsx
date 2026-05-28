import { render, screen } from "@testing-library/react";
import { afterEach, vi } from "vitest";

const { mockHttpGet } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
  },
}));

vi.mock("../../lib/auth/auth-context", () => ({
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
  useAuth: () => ({
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
    menuTree: [],
    mustChangePassword: false,
    login: vi.fn(),
    logout: vi.fn(),
    changePassword: vi.fn(),
    refreshAccessContext: vi.fn(),
  }),
}));

afterEach(() => {
  vi.resetModules();
});

async function renderAppAt(path: string) {
  window.history.pushState({}, "", path);
  const { default: App } = await import("../../App");
  render(<App />);
}

test("用户管理路由渲染对应页面标题", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: [],
  });

  await renderAppAt("/system/users");

  expect(await screen.findByText("用户管理")).toBeInTheDocument();
});

test("角色管理路由渲染对应页面标题", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: [],
  });

  await renderAppAt("/system/roles");

  expect(await screen.findByText("角色管理")).toBeInTheDocument();
});
