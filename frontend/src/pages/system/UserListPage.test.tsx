import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { UserListPage } from "./UserListPage";

const {
  mockHttpDelete,
  mockHttpGet,
  mockHttpPatch,
  mockHttpPost,
  mockHttpPut,
} = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockHttpPut: vi.fn(),
  mockHttpPatch: vi.fn(),
  mockHttpDelete: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
    put: mockHttpPut,
    patch: mockHttpPatch,
    delete: mockHttpDelete,
  },
}));

let lastUsersParams: Record<string, unknown> | undefined;
let lastRolesParams: Record<string, unknown> | undefined;

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

beforeEach(() => {
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
  mockHttpPut.mockReset();
  mockHttpPatch.mockReset();
  mockHttpDelete.mockReset();
  lastUsersParams = undefined;
  lastRolesParams = undefined;
});

test("按原型渲染 RBAC 用户管理卡片和激活用户统计", async () => {
  mockHttpGet.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/users") {
      lastUsersParams = config?.params;
      return {
        data: {
          items: [
            {
              id: 1,
              username: "admin",
              nickname: "管理员",
              email: "admin@example.com",
              phone: "13800000000",
              is_active: true,
              is_superuser: true,
              must_change_password: false,
              roles: [{ id: 1, name: "超级管理员", code: "SUPER_ADMIN" }],
            },
          ],
          total: 1,
          page: 1,
          page_size: 5,
          total_pages: 1,
        },
      };
    }

    lastRolesParams = config?.params;
    return {
      data: {
        items: [{ id: 1, name: "超级管理员", code: "SUPER_ADMIN", description: "系统角色" }],
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      },
    };
  });

  renderWithQuery(<UserListPage />);

  expect(await screen.findByText("RBAC 角色权限与路由控制模块")).toBeInTheDocument();
  expect(lastUsersParams).toEqual({ page: 1, page_size: 5 });
  expect(lastRolesParams).toEqual({ page: 1, page_size: 100 });
  expect(screen.getByText("用户管理")).toBeInTheDocument();
  expect(screen.getByText((content) => content.startsWith("Active Users"))).toBeInTheDocument();
  expect(screen.getByText("用户名")).toBeInTheDocument();
});

test("点击状态按钮后会调用用户启停接口", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 9,
            username: "reviewer",
            nickname: "审查员",
            email: "reviewer@example.com",
            phone: null,
            is_active: true,
            is_superuser: false,
            must_change_password: false,
            roles: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 5,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 100,
        total_pages: 0,
      },
    })
    .mockResolvedValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 5,
        total_pages: 0,
      },
    });
  mockHttpPatch.mockResolvedValueOnce({
    data: {
      id: 9,
      username: "reviewer",
      nickname: "审查员",
      email: "reviewer@example.com",
      phone: null,
      is_active: false,
      is_superuser: false,
      must_change_password: false,
      roles: [],
    },
  });

  renderWithQuery(<UserListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "ACTIVE" }));

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/users/9/status", {
      is_active: false,
    });
  });
});

test("编辑用户时按原型弹窗展示并保存资料与角色分配", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 1,
            username: "bob",
            nickname: "Bob",
            email: "bob@example.com",
            phone: "15500000002",
            is_active: true,
            is_superuser: false,
            must_change_password: false,
            roles: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 5,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 3,
            name: "Maintainer",
            code: "MAINTAINER",
            description: "维护者",
            is_system: false,
            permissions: [],
            menus: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 100,
        total_pages: 1,
      },
    })
    .mockResolvedValue({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 5,
        total_pages: 0,
      },
    });
  mockHttpPatch.mockResolvedValueOnce({
    data: {
      id: 1,
      username: "bob",
      nickname: "Bobby",
      email: "bobby@example.com",
      phone: "15500000002",
      is_active: true,
      is_superuser: true,
      must_change_password: false,
      roles: [],
    },
  });
  mockHttpPut.mockResolvedValueOnce({
    data: {
      id: 1,
      username: "bob",
      nickname: "Bobby",
      email: "bobby@example.com",
      phone: "15500000002",
      is_active: true,
      is_superuser: true,
      must_change_password: false,
      roles: [{ id: 3, name: "Maintainer", code: "MAINTAINER" }],
    },
  });

  renderWithQuery(<UserListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "编辑" }));

  expect(await screen.findByText("编辑用户角色与信息")).toBeInTheDocument();
  expect(screen.getByText("用户名 (username)")).toBeInTheDocument();
  expect(screen.getByText("角色分配")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("昵称"), {
    target: { value: "Bobby" },
  });
  fireEvent.change(screen.getByLabelText("邮箱"), {
    target: { value: "bobby@example.com" },
  });
  fireEvent.click(screen.getByLabelText("设为超级管理员 (is_superuser)"));
  fireEvent.click(screen.getByLabelText("角色 Maintainer"));
  fireEvent.click(screen.getByRole("button", { name: "保存修改" }));

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/users/1", {
      nickname: "Bobby",
      email: "bobby@example.com",
      phone: "15500000002",
      is_superuser: true,
    });
    expect(mockHttpPut).toHaveBeenCalledWith("/users/1/roles", {
      role_ids: [3],
    });
  });
});

test("切换用户管理分页参数后会透传给后端接口", async () => {
  mockHttpGet.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/users") {
      lastUsersParams = config?.params;
      const page = (config?.params?.page as number | undefined) ?? 1;
      const pageSize = (config?.params?.page_size as number | undefined) ?? 5;

      return {
        data: {
          items: [
            {
              id: page,
              username: `user-${page}`,
              nickname: `用户-${page}`,
              email: `user-${page}@example.com`,
              phone: null,
              is_active: true,
              is_superuser: false,
              must_change_password: false,
              roles: [],
            },
          ],
          total: 12,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(12 / pageSize),
        },
      };
    }

    lastRolesParams = config?.params;
    return {
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 100,
        total_pages: 0,
      },
    };
  });

  renderWithQuery(<UserListPage />);

  expect(await screen.findByText("user-1")).toBeInTheDocument();

  fireEvent.change(screen.getByDisplayValue("5 条"), {
    target: { value: "10" },
  });

  await waitFor(() => {
    expect(lastUsersParams).toEqual({ page: 1, page_size: 10 });
  });
});

test("点击用户管理下一页时会透传当前页码", async () => {
  mockHttpGet.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/users") {
      lastUsersParams = config?.params;
      const page = (config?.params?.page as number | undefined) ?? 1;
      const pageSize = (config?.params?.page_size as number | undefined) ?? 5;

      return {
        data: {
          items: [
            {
              id: page,
              username: `user-${page}`,
              nickname: `用户-${page}`,
              email: `user-${page}@example.com`,
              phone: null,
              is_active: true,
              is_superuser: false,
              must_change_password: false,
              roles: [],
            },
          ],
          total: 12,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(12 / pageSize),
        },
      };
    }

    lastRolesParams = config?.params;
    return {
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 100,
        total_pages: 0,
      },
    };
  });

  renderWithQuery(<UserListPage />);

  expect(await screen.findByText("user-1")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "下一页" }));

  await waitFor(() => {
    expect(lastUsersParams).toEqual({ page: 2, page_size: 5 });
  });
});
