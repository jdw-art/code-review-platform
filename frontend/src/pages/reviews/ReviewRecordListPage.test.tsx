import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

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

test("通过审查记录路由渲染核心业务字段", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    },
  });

  window.history.pushState({}, "", "/review-records");
  const { default: App } = await import("../../App");

  render(<App />);

  expect(await screen.findByText("项目名称")).toBeInTheDocument();
  expect(screen.getByText("事件类型")).toBeInTheDocument();
  expect(screen.getByText("评分")).toBeInTheDocument();
  expect(screen.getByText("提交信息")).toBeInTheDocument();
});
