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

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

beforeEach(() => {
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
});

test("点击清空审计日志后调用 purge 接口并显示反馈", async () => {
  mockHttpGet.mockResolvedValue({
    data: {
      items: [
        {
          id: 1,
          user_id: 1,
          username_snapshot: "root-admin",
          action: "user.create",
          resource_type: "user",
          resource_id: 8,
          resource_name_snapshot: "alice",
          request_path: "/api/v1/users",
          request_method: "POST",
          request_payload: {},
          response_status: 201,
          result: "success",
          error_message: null,
          ip_address: "127.0.0.1",
          user_agent: "Vitest",
          created_at: "2026-06-06T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
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
    expect(mockHttpPost).toHaveBeenCalledWith("/audit-logs/purge");
  });
  expect(await screen.findByText("已清理 3 条业务审计日志。")).toBeInTheDocument();
  expect(screen.getByText("系统安全日志已保留。")).toBeInTheDocument();
});
