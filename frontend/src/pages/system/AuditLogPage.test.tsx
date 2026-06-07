import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { AuditLogPage } from "./AuditLogPage";

const { mockHttpGet, mockHttpPost } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function buildAuditLog(overrides?: Record<string, unknown>) {
  return {
    id: 1,
    user_id: 1,
    username_snapshot: "root-admin",
    action: "user.create",
    resource_type: "user",
    resource_id: 8,
    resource_name_snapshot: "alice",
    request_path: "/api/v1/users",
    request_method: "POST",
    request_payload: { username: "alice" },
    response_status: 201,
    result: "success",
    error_message: null,
    ip_address: "127.0.0.1",
    user_agent: "Vitest",
    created_at: "2026-06-06T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
});

test("按原型渲染系统安全审计中心标题条、工具栏和表格头部", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [buildAuditLog()],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  const { container } = renderWithQuery(<AuditLogPage />);

  const root = container.firstElementChild;
  expect(root).toHaveClass("p-6", "space-y-4", "max-w-7xl", "mx-auto");
  expect(await screen.findByText("系统安全审计中心 (audit_logs)")).toBeInTheDocument();
  expect(mockHttpGet).toHaveBeenCalledWith("/audit-logs", {
    params: { page: 1, page_size: 10 },
  });
  expect(
    screen.getByPlaceholderText("搜操作行为 action、资源、API 路径、操作人...")
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "全部状态" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "成功 (SUCCESS)" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "拦截/失败 (FAILED)" })).toBeInTheDocument();
  expect(screen.getByText("创建时间 (created_at)")).toBeInTheDocument();
  expect(screen.getByText("执功结果")).toBeInTheDocument();
  expect(screen.getByText("网络端点 (path & method)")).toBeInTheDocument();
  expect(screen.getByText("审计说明")).toBeInTheDocument();
});

test("按原型支持搜索与失败筛选", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [
        buildAuditLog(),
        buildAuditLog({
          id: 2,
          username_snapshot: "auditor",
          action: "role.delete",
          request_method: "DELETE",
          request_path: "/api/v1/roles/2",
          result: "failed",
          error_message: "SYSTEM_ROLE_DELETE_FORBIDDEN",
        }),
      ],
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithQuery(<AuditLogPage />);

  expect(await screen.findByText("user.create")).toBeInTheDocument();
  expect(screen.getByText("role.delete")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "拦截/失败 (FAILED)" }));

  expect(screen.queryByText("user.create")).not.toBeInTheDocument();
  expect(screen.getByText("role.delete")).toBeInTheDocument();

  fireEvent.change(screen.getByPlaceholderText("搜操作行为 action、资源、API 路径、操作人..."), {
    target: { value: "auditor" },
  });

  expect(screen.getByText("role.delete")).toBeInTheDocument();
  expect(screen.queryByText("root-admin")).not.toBeInTheDocument();
});

test("点击清空审计日志后调用 purge 接口并显示反馈", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [buildAuditLog()],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      },
    });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      purged_count: 3,
    },
  });

  renderWithQuery(<AuditLogPage />);

  fireEvent.click(await screen.findByRole("button", { name: "清空审计日志" }));

  await waitFor(() => {
    expect(confirmSpy).toHaveBeenCalledWith("确认清理业务审计日志吗？系统安全日志会保留。");
    expect(mockHttpPost).toHaveBeenCalledWith("/audit-logs/purge");
  });

  expect(await screen.findByText("已清理 3 条业务审计日志。")).toBeInTheDocument();
  expect(screen.getByText("系统安全日志已保留。")).toBeInTheDocument();

  confirmSpy.mockRestore();
});

test("切换系统日志分页参数后会将 page 和 page_size 透传给后端", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [buildAuditLog()],
        total: 80,
        page: 1,
        page_size: 10,
        total_pages: 8,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [buildAuditLog({ id: 2 })],
        total: 80,
        page: 1,
        page_size: 50,
        total_pages: 2,
      },
    });

  renderWithQuery(<AuditLogPage />);

  expect(await screen.findByText("user.create")).toBeInTheDocument();

  fireEvent.change(screen.getByDisplayValue("10 条"), {
    target: { value: "50" },
  });

  await waitFor(() => {
    expect(mockHttpGet).toHaveBeenLastCalledWith("/audit-logs", {
      params: { page: 1, page_size: 50 },
    });
  });
});

test("点击系统日志下一页时会透传当前页码", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [buildAuditLog()],
        total: 80,
        page: 1,
        page_size: 10,
        total_pages: 8,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [buildAuditLog({ id: 3 })],
        total: 80,
        page: 2,
        page_size: 10,
        total_pages: 8,
      },
    });

  renderWithQuery(<AuditLogPage />);

  expect(await screen.findByText("user.create")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "下一页" }));

  await waitFor(() => {
    expect(mockHttpGet).toHaveBeenLastCalledWith("/audit-logs", {
      params: { page: 2, page_size: 10 },
    });
  });
});
