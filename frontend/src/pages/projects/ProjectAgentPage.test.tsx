import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { ProjectAgentPage } from "./ProjectAgentPage";

const { mockHttpGet, mockHttpPost, mockTokenStore, mockFetch } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockTokenStore: {
    load: vi.fn(() => ({
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      expires_in: 900,
      must_change_password: false,
    })),
    save: vi.fn(),
    clear: vi.fn(),
  },
  mockFetch: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
  },
}));

vi.mock("../../lib/auth/token-store", () => ({
  tokenStore: mockTokenStore,
}));

function renderPage() {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/projects/1/agent"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/projects/:projectId/agent" element={<ProjectAgentPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function buildStreamResponse(chunks: string[]) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
    },
  });
}

beforeEach(() => {
  vi.stubGlobal("fetch", mockFetch);
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
  mockFetch.mockReset();
});

test("renders branch selector before session starts", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: [],
  });

  renderPage();

  expect(await screen.findByText("仓库对话助手")).toBeInTheDocument();
  expect(screen.getByLabelText("选择分支")).toBeInTheDocument();
});

test("creates session and renders it in session list", async () => {
  mockHttpGet
    .mockResolvedValueOnce({ data: [] })
    .mockResolvedValueOnce({
      data: [
        {
          id: 1,
          project_id: 1,
          title: "主分支仓库助手",
          status: "active",
          branch: "main",
          provider: "openai",
          model: "gpt-5.4",
          created_by: 1,
          created_at: "2026-06-04T08:00:00Z",
          updated_at: "2026-06-04T08:00:00Z",
          last_message_at: null,
        },
      ],
    });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      id: 1,
      project_id: 1,
      title: "主分支仓库助手",
      status: "active",
      branch: "main",
      provider: "openai",
      model: "gpt-5.4",
      created_by: 1,
      created_at: "2026-06-04T08:00:00Z",
      updated_at: "2026-06-04T08:00:00Z",
      last_message_at: null,
    },
  });
  mockFetch.mockImplementation(() =>
    Promise.resolve(
      buildStreamResponse([
        'event: ready\ndata: {"session_id":1,"status":"active"}\n\n',
      ])
    )
  );

  renderPage();

  fireEvent.click(await screen.findByRole("button", { name: "创建会话" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/projects/1/agent/sessions", {
      title: "主分支仓库助手",
      branch: "main",
    });
  });
  expect(await screen.findByText("当前项目下共 1 条仓库对话。")).toBeInTheDocument();
  expect(screen.getAllByText("主分支仓库助手").length).toBeGreaterThan(0);
});

test("sends message and renders streamed final answer", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: [
      {
        id: 2,
        project_id: 1,
        title: "主分支仓库助手",
        status: "active",
        branch: "main",
        provider: "openai",
        model: "gpt-5.4",
        created_by: 1,
        created_at: "2026-06-04T08:00:00Z",
        updated_at: "2026-06-04T08:00:00Z",
        last_message_at: null,
      },
    ],
  });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      id: 10,
      session_id: 2,
      run_id: 3,
      role: "user",
      content: "这个仓库是做什么的？",
      status: "completed",
      sequence: 1,
      content_format: "markdown",
      created_at: "2026-06-04T08:00:01Z",
    },
  });
  mockFetch
    .mockResolvedValueOnce(
      buildStreamResponse(['event: ready\ndata: {"session_id":2,"status":"active"}\n\n'])
    )
    .mockResolvedValueOnce(
      buildStreamResponse([
        'event: message\ndata: {"id":10,"session_id":2,"role":"user","content":"这个仓库是做什么的？","status":"completed","sequence":1,"created_at":"2026-06-04T08:00:01Z"}\n\n',
        'event: run_started\ndata: {"id":1,"run_id":3,"session_id":2,"sequence":1,"payload":{"branch":"main","head_sha":"sha-1"},"created_at":"2026-06-04T08:00:01Z"}\n\n',
        'event: tool_called\ndata: {"id":2,"run_id":3,"session_id":2,"sequence":4,"payload":{"tool_name":"read_file","tool_args":{"path":"README.md","start":1,"end":20}},"created_at":"2026-06-04T08:00:02Z"}\n\n',
        'event: final_answer\ndata: {"id":3,"run_id":3,"session_id":2,"sequence":7,"payload":{"final_answer":"README 表明这个仓库提供 Repo Agent 能力。"},"created_at":"2026-06-04T08:00:03Z"}\n\n',
        'event: ready\ndata: {"session_id":2,"status":"active"}\n\n',
      ])
    );

  renderPage();

  fireEvent.change(await screen.findByLabelText("发送消息"), {
    target: { value: "这个仓库是做什么的？" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送消息" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith(
      "/projects/1/agent/sessions/2/messages",
      {
        content: "这个仓库是做什么的？",
      }
    );
  });
  expect(await screen.findByText("最终回答")).toBeInTheDocument();
  expect(
    screen.getByText("README 表明这个仓库提供 Repo Agent 能力。")
  ).toBeInTheDocument();
});
