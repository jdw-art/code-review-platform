import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { toConsoleModel } from "../../features/models/serializers";
import { ModelListPage } from "./ModelListPage";

const { mockHttpGet } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

test("渲染脱敏后的模型字段而不是明文密钥", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [
        {
          id: 1,
          name: "OpenAI GPT 4.1",
          provider: "openai",
          model_code: "gpt-4.1",
          base_url: "https://api.openai.com/v1",
          api_key_masked: "sk-l**********-key",
          temperature: 0.2,
          max_tokens: 4096,
          top_p: 0.9,
          prompt_template: "review code",
          is_default: true,
          is_active: true,
          last_test_status: "success",
          last_test_message: "ok",
          last_test_at: "2026-05-28T10:00:00Z",
          created_at: "2026-05-28T10:00:00Z",
          updated_at: "2026-05-28T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithQuery(<ModelListPage />);

  expect(await screen.findByText("模型名称")).toBeInTheDocument();
  expect(await screen.findByText("OpenAI GPT 4.1")).toBeInTheDocument();
  expect(screen.queryByText("sk-live-secret")).not.toBeInTheDocument();
});

test("renders console model cards and activation action", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithQuery(<ModelListPage />);

  expect(await screen.findByText("审查模型与计算智能矩阵")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "部署新模型智算" })).toBeInTheDocument();
});

test("maps model response into console fields", () => {
  const vm = toConsoleModel({
    id: 1,
    name: "OpenAI GPT 4.1",
    provider: "openai",
    model_code: "gpt-4.1",
    base_url: "https://api.openai.com/v1",
    api_key_masked: "sk-l**********-key",
    temperature: 0.2,
    max_tokens: 4096,
    top_p: 0.9,
    prompt_template: "review code",
    is_default: true,
    is_active: true,
    queries_count: 27,
    last_test_status: "success",
    last_test_message: "ok",
    last_test_at: "2026-05-28T10:00:00Z",
    created_at: "2026-05-28T10:00:00Z",
    updated_at: "2026-05-28T10:00:00Z",
  });

  expect(vm.isActive).toBe(true);
  expect(vm.queriesCount).toBe(27);
  expect(vm.api_key_masked).toBe("sk-l**********-key");
});

test("maps model response safely when queries_count is absent or null", () => {
  const missingCountVm = toConsoleModel({
    id: 2,
    name: "Claude 3.7 Sonnet",
    provider: "anthropic",
    model_code: "claude-3-7-sonnet",
    base_url: null,
    api_key_masked: null,
    temperature: null,
    max_tokens: null,
    top_p: null,
    prompt_template: null,
    is_default: false,
    is_active: false,
    last_test_status: null,
    last_test_message: null,
    last_test_at: null,
    created_at: "2026-05-28T10:00:00Z",
    updated_at: "2026-05-28T10:00:00Z",
  });
  const nullCountVm = toConsoleModel({
    id: 3,
    name: "Gemini 2.5 Pro",
    provider: "google",
    model_code: "gemini-2.5-pro",
    base_url: null,
    api_key_masked: null,
    temperature: null,
    max_tokens: null,
    top_p: null,
    prompt_template: null,
    is_default: false,
    is_active: true,
    queries_count: null,
    last_test_status: null,
    last_test_message: null,
    last_test_at: null,
    created_at: "2026-05-28T10:00:00Z",
    updated_at: "2026-05-28T10:00:00Z",
  });

  expect(missingCountVm.queriesCount).toBe(0);
  expect(nullCountVm.queriesCount).toBe(0);
});
