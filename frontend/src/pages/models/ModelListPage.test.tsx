import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
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
