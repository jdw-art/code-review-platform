import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { BotListPage } from "./BotListPage";

const {
  mockHttpGet,
  mockHttpPost,
  mockHttpPut,
  mockHttpPatch,
} = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockHttpPut: vi.fn(),
  mockHttpPatch: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
    put: mockHttpPut,
    patch: mockHttpPatch,
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
});

test("点击测试按钮后会调用机器人测试接口", async () => {
  mockHttpGet.mockResolvedValue({
    data: {
      items: [
        {
          id: 7,
          name: "发布通知机器人",
          bot_type: "dingtalk",
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=bot-7",
          secret_masked: "sec******789",
          mention_strategy: "owners",
          template_config: {},
          is_active: true,
          last_test_status: "success",
          last_test_message: "ok",
          last_test_at: "2026-06-05T10:00:00Z",
          created_at: "2026-06-05T10:00:00Z",
          updated_at: "2026-06-05T10:00:00Z",
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
      id: 7,
      name: "发布通知机器人",
      bot_type: "dingtalk",
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=bot-7",
      secret_masked: "sec******789",
      mention_strategy: "owners",
      template_config: {},
      is_active: true,
      last_test_status: "success",
      last_test_message: "ok",
      last_test_at: "2026-06-06T10:00:00Z",
      created_at: "2026-06-05T10:00:00Z",
      updated_at: "2026-06-06T10:00:00Z",
    },
  });

  renderWithQuery(<BotListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "测试" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/notification-bots/7/test");
  });
});
