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

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

beforeEach(() => {
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
  mockHttpPut.mockReset();
  mockHttpPatch.mockReset();
  mockHttpDelete.mockReset();
});

test("根据后端契约渲染用户列表表头", async () => {
  mockHttpGet
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [] });

  renderWithQuery(<UserListPage />);

  expect(await screen.findByText("用户名")).toBeInTheDocument();
  expect(screen.getByText("邮箱")).toBeInTheDocument();
  expect(screen.getByText("角色")).toBeInTheDocument();
  expect(screen.getByText("超级管理员")).toBeInTheDocument();
});

test("renders console user management layout", async () => {
  mockHttpGet
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [] });

  renderWithQuery(<UserListPage />);

  expect(await screen.findByText("系统用户中心")).toBeInTheDocument();
});

test("点击新建用户后可以打开表单并提交创建请求", async () => {
  mockHttpGet
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({
      data: [
        {
          id: 2,
          name: "Reviewer",
          code: "reviewer",
          description: "代码审查员",
          is_system: false,
          permissions: [],
          menus: [],
        },
      ],
    })
    .mockResolvedValue({ data: [] });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      id: 10,
      username: "alice",
      nickname: "Alice",
      email: "alice@example.com",
      phone: "15500000001",
      is_active: true,
      is_superuser: false,
      must_change_password: false,
      roles: [{ id: 2, name: "Reviewer", code: "reviewer" }],
    },
  });

  renderWithQuery(<UserListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "新建用户" }));

  expect(await screen.findByText("创建用户")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("用户名"), {
    target: { value: "alice" },
  });
  fireEvent.change(screen.getByLabelText("初始密码"), {
    target: { value: "alice123456" },
  });
  fireEvent.change(screen.getByLabelText("昵称"), {
    target: { value: "Alice" },
  });
  fireEvent.change(screen.getByLabelText("邮箱"), {
    target: { value: "alice@example.com" },
  });
  fireEvent.change(screen.getByLabelText("手机号"), {
    target: { value: "15500000001" },
  });
  fireEvent.click(screen.getByLabelText("角色 Reviewer"));
  fireEvent.click(screen.getByRole("button", { name: "保存用户" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/users", {
      username: "alice",
      password: "alice123456",
      nickname: "Alice",
      email: "alice@example.com",
      phone: "15500000001",
      is_superuser: false,
      role_ids: [2],
    });
  });
});

test("编辑用户后会更新资料并覆盖角色分配", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: [
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
    })
    .mockResolvedValueOnce({
      data: [
        {
          id: 3,
          name: "Maintainer",
          code: "maintainer",
          description: "维护者",
          is_system: false,
          permissions: [],
          menus: [],
        },
      ],
    })
    .mockResolvedValue({ data: [] });
  mockHttpPatch.mockResolvedValueOnce({
    data: {
      id: 1,
      username: "bob",
      nickname: "Bobby",
      email: "bobby@example.com",
      phone: "15500000002",
      is_active: true,
      is_superuser: false,
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
      is_superuser: false,
      must_change_password: false,
      roles: [{ id: 3, name: "Maintainer", code: "maintainer" }],
    },
  });

  renderWithQuery(<UserListPage />);

  fireEvent.click((await screen.findAllByRole("button", { name: "编辑" }))[0]);

  expect(await screen.findByText("编辑用户")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("昵称"), {
    target: { value: "Bobby" },
  });
  fireEvent.change(screen.getByLabelText("邮箱"), {
    target: { value: "bobby@example.com" },
  });
  fireEvent.click(screen.getByLabelText("角色 Maintainer"));
  fireEvent.click(screen.getByRole("button", { name: "保存用户" }));

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/users/1", {
      nickname: "Bobby",
      email: "bobby@example.com",
      phone: "15500000002",
      is_superuser: false,
    });
    expect(mockHttpPut).toHaveBeenCalledWith("/users/1/roles", {
      role_ids: [3],
    });
  });
});

test("点击删除用户后会调用删除接口", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

  mockHttpGet
    .mockResolvedValueOnce({
      data: [
        {
          id: 8,
          username: "carol",
          nickname: "Carol",
          email: "carol@example.com",
          phone: "15500000003",
          is_active: true,
          is_superuser: false,
          must_change_password: false,
          roles: [],
        },
      ],
    })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValue({ data: [] });
  mockHttpDelete.mockResolvedValueOnce({ data: null });

  renderWithQuery(<UserListPage />);

  fireEvent.click((await screen.findAllByRole("button", { name: "删除" }))[0]);

  await waitFor(() => {
    expect(confirmSpy).toHaveBeenCalledWith("确认删除用户 carol 吗？");
    expect(mockHttpDelete).toHaveBeenCalledWith("/users/8");
  });

  confirmSpy.mockRestore();
});
