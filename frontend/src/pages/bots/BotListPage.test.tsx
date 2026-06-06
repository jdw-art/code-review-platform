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

test("机器人测试成功后显示成功反馈", async () => {
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
      last_test_message: "测试消息发送成功。",
      last_test_at: "2026-06-06T10:00:00Z",
      created_at: "2026-06-05T10:00:00Z",
      updated_at: "2026-06-06T10:00:00Z",
    },
  });

  renderWithQuery(<BotListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "测试" }));

  expect(
    await screen.findByText("已成功向「发布通知机器人」发送诊断测试 Ping 卡片！")
  ).toBeInTheDocument();
  expect(screen.getByText("测试消息发送成功。")).toBeInTheDocument();
});

test("机器人测试失败后显示错误反馈", async () => {
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
      last_test_status: "failed",
      last_test_message: "Webhook handshake token mismatch.",
      last_test_at: "2026-06-06T10:00:00Z",
      created_at: "2026-06-05T10:00:00Z",
      updated_at: "2026-06-06T10:00:00Z",
    },
  });

  renderWithQuery(<BotListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "测试" }));

  expect(
    await screen.findByText("向「发布通知机器人」发送测试卡片失败，请检查密钥或网络！")
  ).toBeInTheDocument();
  expect(screen.getByText("Webhook handshake token mismatch.")).toBeInTheDocument();
});

test("多行机器人测试并发进行时按行禁用并防止各自行重复点击", async () => {
  let resolveFirstRequest: ((value: unknown) => void) | null = null;
  let resolveSecondRequest: ((value: unknown) => void) | null = null;

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
        {
          id: 8,
          name: "质量预警机器人",
          bot_type: "dingtalk",
          webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=bot-8",
          secret_masked: "sec******123",
          mention_strategy: "reviewers",
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
  mockHttpPost.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveFirstRequest = resolve;
      })
  );
  mockHttpPost.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        resolveSecondRequest = resolve;
      })
  );

  renderWithQuery(<BotListPage />);

  const [firstTestButton, secondTestButton] = await screen.findAllByRole("button", {
    name: "测试",
  });
  fireEvent.click(firstTestButton);
  fireEvent.click(secondTestButton);

  await waitFor(() => {
    expect(firstTestButton).toBeDisabled();
    expect(secondTestButton).toBeDisabled();
  });

  fireEvent.click(firstTestButton);
  fireEvent.click(secondTestButton);

  expect(mockHttpPost).toHaveBeenCalledTimes(2);

  expect(resolveFirstRequest).not.toBeNull();
  resolveFirstRequest!({
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
      last_test_message: "测试消息发送成功。",
      last_test_at: "2026-06-06T10:00:00Z",
      created_at: "2026-06-05T10:00:00Z",
      updated_at: "2026-06-06T10:00:00Z",
    },
  });

  await waitFor(() => {
    expect(firstTestButton).not.toBeDisabled();
    expect(secondTestButton).toBeDisabled();
  });

  fireEvent.click(secondTestButton);

  expect(mockHttpPost).toHaveBeenCalledTimes(2);

  expect(resolveSecondRequest).not.toBeNull();
  resolveSecondRequest!({
    data: {
      id: 8,
      name: "质量预警机器人",
      bot_type: "dingtalk",
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=bot-8",
      secret_masked: "sec******123",
      mention_strategy: "reviewers",
      template_config: {},
      is_active: true,
      last_test_status: "success",
      last_test_message: "测试消息发送成功。",
      last_test_at: "2026-06-06T10:00:00Z",
      created_at: "2026-06-05T10:00:00Z",
      updated_at: "2026-06-06T10:00:00Z",
    },
  });

  await waitFor(() => {
    expect(secondTestButton).not.toBeDisabled();
  });
});
