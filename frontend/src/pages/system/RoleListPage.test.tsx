import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { RoleListPage } from "./RoleListPage";

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

test("点击新建角色后可以打开表单并提交创建请求", async () => {
  mockHttpGet
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({
      data: [
        {
          id: 1,
          name: "查看用户",
          code: "user:read",
          resource: "user",
          action: "read",
          description: "查看用户",
          is_system: true,
        },
      ],
    })
    .mockResolvedValueOnce({
      data: [
        {
          id: 11,
          parent_id: null,
          name: "用户管理",
          path: "/system/users",
          component: null,
          icon: null,
          sort: 20,
          visible: true,
          redirect: null,
          meta: null,
          is_system: true,
          children: [],
        },
      ],
    })
    .mockResolvedValue({ data: [] });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      id: 3,
      name: "质量负责人",
      code: "quality-owner",
      description: "负责质量门禁",
      is_system: false,
      permissions: [],
      menus: [],
    },
  });

  renderWithQuery(<RoleListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "新建角色" }));

  expect(await screen.findByText("创建角色")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("角色名称"), {
    target: { value: "质量负责人" },
  });
  fireEvent.change(screen.getByLabelText("角色编码"), {
    target: { value: "quality-owner" },
  });
  fireEvent.change(screen.getByLabelText("描述"), {
    target: { value: "负责质量门禁" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存角色" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/roles", {
      name: "质量负责人",
      code: "quality-owner",
      description: "负责质量门禁",
    });
  });
});

test("编辑角色后会更新基础信息并覆盖权限菜单分配", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: [
        {
          id: 5,
          name: "审查员",
          code: "reviewer",
          description: "负责代码审查",
          is_system: false,
          permissions: [],
          menus: [],
        },
      ],
    })
    .mockResolvedValueOnce({
      data: [
        {
          id: 2,
          name: "查看用户",
          code: "user:read",
          resource: "user",
          action: "read",
          description: "查看用户",
          is_system: true,
        },
      ],
    })
    .mockResolvedValueOnce({
      data: [
        {
          id: 18,
          parent_id: null,
          name: "角色管理",
          path: "/system/roles",
          component: null,
          icon: null,
          sort: 30,
          visible: true,
          redirect: null,
          meta: null,
          is_system: true,
          children: [],
        },
      ],
    })
    .mockResolvedValue({ data: [] });
  mockHttpPatch.mockResolvedValueOnce({
    data: {
      id: 5,
      name: "高级审查员",
      code: "reviewer",
      description: "负责关键变更审查",
      is_system: false,
      permissions: [],
      menus: [],
    },
  });
  mockHttpPut
    .mockResolvedValueOnce({
      data: {
        id: 5,
        name: "高级审查员",
        code: "reviewer",
        description: "负责关键变更审查",
        is_system: false,
        permissions: [],
        menus: [],
      },
    })
    .mockResolvedValueOnce({
      data: {
        id: 5,
        name: "高级审查员",
        code: "reviewer",
        description: "负责关键变更审查",
        is_system: false,
        permissions: [],
        menus: [],
      },
    });

  renderWithQuery(<RoleListPage />);

  fireEvent.click((await screen.findAllByRole("button", { name: "编辑" }))[0]);

  expect(await screen.findByText("编辑角色")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("角色名称"), {
    target: { value: "高级审查员" },
  });
  fireEvent.change(screen.getByLabelText("描述"), {
    target: { value: "负责关键变更审查" },
  });
  fireEvent.click(screen.getByLabelText("权限 user:read"));
  fireEvent.click(screen.getByLabelText("菜单 角色管理"));
  fireEvent.click(screen.getByRole("button", { name: "保存角色" }));

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/roles/5", {
      name: "高级审查员",
      description: "负责关键变更审查",
    });
    expect(mockHttpPut).toHaveBeenNthCalledWith(1, "/roles/5/permissions", {
      permission_ids: [2],
    });
    expect(mockHttpPut).toHaveBeenNthCalledWith(2, "/roles/5/menus", {
      menu_ids: [18],
    });
  });
});

test("点击删除角色后会调用删除接口", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

  mockHttpGet
    .mockResolvedValueOnce({
      data: [
        {
          id: 9,
          name: "访客",
          code: "visitor",
          description: "只读角色",
          is_system: false,
          permissions: [],
          menus: [],
        },
      ],
    })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValue({ data: [] });
  mockHttpDelete.mockResolvedValueOnce({ data: null });

  renderWithQuery(<RoleListPage />);

  fireEvent.click((await screen.findAllByRole("button", { name: "删除" }))[0]);

  await waitFor(() => {
    expect(confirmSpy).toHaveBeenCalledWith("确认删除角色 访客 吗？");
    expect(mockHttpDelete).toHaveBeenCalledWith("/roles/9");
  });

  confirmSpy.mockRestore();
});
