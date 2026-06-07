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
  lastRolesParams = undefined;
});

test("按原型渲染 RBAC 角色表和新增系统角色按钮", async () => {
  mockHttpGet
    .mockImplementationOnce(async (_url: string, config?: { params?: Record<string, unknown> }) => {
      lastRolesParams = config?.params;
      return {
        data: {
          items: [
            {
              id: 1,
              name: "Super Admin",
              code: "SUPER_ADMIN",
              description: "系统角色",
              is_system: true,
              permissions: [],
              menus: [],
            },
          ],
          total: 1,
          page: 1,
          page_size: 5,
          total_pages: 1,
        },
      };
    })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [] });

  renderWithQuery(<RoleListPage />);

  expect(await screen.findByText("RBAC 角色权限与路由控制模块")).toBeInTheDocument();
  expect(lastRolesParams).toEqual({ page: 1, page_size: 5 });
  expect(screen.getByText("全局角色配置表 (roles)")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "新增系统角色" })).toBeInTheDocument();
});

test("按原型创建角色并提交权限与菜单分配", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 5,
        total_pages: 0,
      },
    })
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
          icon: "UserCheck",
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
      code: "QUALITY_OWNER",
      description: "负责质量门禁",
      is_system: false,
      permissions: [],
      menus: [],
    },
  });
  mockHttpPut
    .mockResolvedValueOnce({
      data: {
        id: 3,
        name: "质量负责人",
        code: "QUALITY_OWNER",
        description: "负责质量门禁",
        is_system: false,
        permissions: [],
        menus: [],
      },
    })
    .mockResolvedValueOnce({
      data: {
        id: 3,
        name: "质量负责人",
        code: "QUALITY_OWNER",
        description: "负责质量门禁",
        is_system: false,
        permissions: [],
        menus: [],
      },
    });

  renderWithQuery(<RoleListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "新增系统角色" }));

  expect(await screen.findByText("创建全新系统角色")).toBeInTheDocument();
  expect(screen.getByText("1. 后台左侧系统菜单分配")).toBeInTheDocument();
  expect(screen.getByText("2. 后台 38 项精细功能点准入权限分配")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("角色名称 (name)"), {
    target: { value: "质量负责人" },
  });
  fireEvent.change(screen.getByLabelText("唯一英文代码标识 (code)"), {
    target: { value: "QUALITY_OWNER" },
  });
  fireEvent.change(screen.getByLabelText("职责要旨及描述说明 (description)"), {
    target: { value: "负责质量门禁" },
  });
  fireEvent.click(screen.getByLabelText("菜单 用户管理"));
  fireEvent.click(screen.getByLabelText("权限 user:read"));
  fireEvent.click(screen.getByRole("button", { name: "保存权限配置" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/roles", {
      name: "质量负责人",
      code: "QUALITY_OWNER",
      description: "负责质量门禁",
    });
    expect(mockHttpPut).toHaveBeenNthCalledWith(1, "/roles/3/permissions", {
      permission_ids: [1],
    });
    expect(mockHttpPut).toHaveBeenNthCalledWith(2, "/roles/3/menus", {
      menu_ids: [11],
    });
  });
});

test("编辑角色后会保存原型弹窗中的权限与菜单配置", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 5,
            name: "审查员",
            code: "REVIEWER",
            description: "负责代码审查",
            is_system: false,
            permissions: [],
            menus: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 5,
        total_pages: 1,
      },
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
          icon: "ShieldCheck",
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
      code: "REVIEWER",
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
        code: "REVIEWER",
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
        code: "REVIEWER",
        description: "负责关键变更审查",
        is_system: false,
        permissions: [],
        menus: [],
      },
    });

  renderWithQuery(<RoleListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "控制分配" }));

  expect(await screen.findByText("编辑角色 - [审查员] 权限及菜单管控分配")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("角色名称 (name)"), {
    target: { value: "高级审查员" },
  });
  fireEvent.change(screen.getByLabelText("职责要旨及描述说明 (description)"), {
    target: { value: "负责关键变更审查" },
  });
  fireEvent.click(screen.getByLabelText("菜单 角色管理"));
  fireEvent.click(screen.getByLabelText("权限 user:read"));
  fireEvent.click(screen.getByRole("button", { name: "保存权限配置" }));

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

test("删除自定义角色时会调用删除接口", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 9,
            name: "访客",
            code: "VISITOR",
            description: "只读角色",
            is_system: false,
            permissions: [],
            menus: [],
          },
        ],
        total: 1,
        page: 1,
        page_size: 5,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValue({ data: [] });
  mockHttpDelete.mockResolvedValueOnce({ data: null });

  renderWithQuery(<RoleListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "删除" }));

  await waitFor(() => {
    expect(confirmSpy).toHaveBeenCalledWith("确认删除角色 访客 吗？");
    expect(mockHttpDelete).toHaveBeenCalledWith("/roles/9");
  });

  confirmSpy.mockRestore();
});

test("切换角色管理分页参数后会透传给后端接口", async () => {
  mockHttpGet.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/roles") {
      lastRolesParams = config?.params;
      const page = (config?.params?.page as number | undefined) ?? 1;
      const pageSize = (config?.params?.page_size as number | undefined) ?? 5;

      return {
        data: {
          items: [
            {
              id: page,
              name: `角色-${page}`,
              code: `ROLE_${page}`,
              description: "分页角色",
              is_system: false,
              permissions: [],
              menus: [],
            },
          ],
          total: 12,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(12 / pageSize),
        },
      };
    }

    return { data: [] };
  });

  renderWithQuery(<RoleListPage />);

  expect(await screen.findByText("角色-1")).toBeInTheDocument();

  fireEvent.change(screen.getByDisplayValue("5 条"), {
    target: { value: "10" },
  });

  await waitFor(() => {
    expect(lastRolesParams).toEqual({ page: 1, page_size: 10 });
  });
});

test("点击角色管理下一页时会透传当前页码", async () => {
  mockHttpGet.mockImplementation(async (url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/roles") {
      lastRolesParams = config?.params;
      const page = (config?.params?.page as number | undefined) ?? 1;
      const pageSize = (config?.params?.page_size as number | undefined) ?? 5;

      return {
        data: {
          items: [
            {
              id: page,
              name: `角色-${page}`,
              code: `ROLE_${page}`,
              description: "分页角色",
              is_system: false,
              permissions: [],
              menus: [],
            },
          ],
          total: 12,
          page,
          page_size: pageSize,
          total_pages: Math.ceil(12 / pageSize),
        },
      };
    }

    return { data: [] };
  });

  renderWithQuery(<RoleListPage />);

  expect(await screen.findByText("角色-1")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "下一页" }));

  await waitFor(() => {
    expect(lastRolesParams).toEqual({ page: 2, page_size: 5 });
  });
});
