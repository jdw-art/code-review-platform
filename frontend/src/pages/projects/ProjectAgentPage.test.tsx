import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { ProjectAgentPage } from "./ProjectAgentPage";

const {
  createAgentEventSourceMock,
  createAgentSessionMock,
  listAgentMessagesMock,
  listAgentSessionsMock,
  sendAgentMessageMock,
} = vi.hoisted(() => ({
  listAgentSessionsMock: vi.fn(),
  createAgentSessionMock: vi.fn(),
  listAgentMessagesMock: vi.fn(),
  sendAgentMessageMock: vi.fn(),
  createAgentEventSourceMock: vi.fn(),
}));

vi.mock("../../features/agent/api", () => ({
  listAgentSessions: listAgentSessionsMock,
  createAgentSession: createAgentSessionMock,
  listAgentMessages: listAgentMessagesMock,
  sendAgentMessage: sendAgentMessageMock,
  createAgentEventSource: createAgentEventSourceMock,
}));

class MockEventSource {
  listeners = new Map<string, Array<(event: { data: string }) => void>>();

  addEventListener(type: string, handler: (event: { data: string }) => void) {
    const current = this.listeners.get(type) ?? [];
    current.push(handler);
    this.listeners.set(type, current);
  }

  close() {
    return undefined;
  }

  emit(type: string, payload: Record<string, unknown>) {
    const current = this.listeners.get(type) ?? [];
    current.forEach((handler) =>
      handler({
        data: JSON.stringify(payload),
      })
    );
  }
}

function renderWithProviders(ui: ReactElement) {
  const queryClient = createQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/projects/7/agent"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/projects/:projectId/agent" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test("renders sessions, sends a message, and appends streamed assistant text", async () => {
  const source = new MockEventSource();
  listAgentSessionsMock.mockResolvedValueOnce([
    {
      id: 11,
      project_id: 7,
      title: "仓库理解助手",
      status: "active",
      workspace_fingerprint: "fp-1234567890",
      snapshot_id: 88,
      created_at: "2026-06-03T09:00:00Z",
      updated_at: "2026-06-03T09:00:00Z",
    },
  ]);
  listAgentMessagesMock.mockResolvedValue([]);
  sendAgentMessageMock.mockResolvedValueOnce({
    session_id: 11,
    user_message_id: 201,
    assistant_message_id: 202,
    run_id: 301,
    status: "accepted",
  });
  createAgentEventSourceMock.mockReturnValue(source);

  renderWithProviders(<ProjectAgentPage />);

  expect(await screen.findByText("仓库理解助手")).toBeInTheDocument();
  expect(await screen.findByText("session #11")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("新问题"), {
    target: { value: "后端入口在哪里？" },
  });
  fireEvent.click(screen.getByRole("button", { name: "发送" }));

  await waitFor(() => {
    expect(sendAgentMessageMock).toHaveBeenCalledWith(11, "后端入口在哪里？");
  });

  act(() => {
    source.emit("assistant_delta", {
      id: 1,
      event_type: "assistant_delta",
      payload: { delta: "后端入口在 " },
    });
    source.emit("tool_result", {
      id: 2,
      event_type: "tool_result",
      payload: { name: "read_file", output: "README.md" },
    });
    source.emit("assistant_message", {
      id: 3,
      event_type: "assistant_message",
      payload: {
        message_id: 202,
        content: "后端入口在 backend/app/main.py。",
      },
    });
    source.emit("final", {
      id: 4,
      event_type: "final",
      payload: { final_answer: "后端入口在 backend/app/main.py。" },
    });
  });

  expect(await screen.findByText("后端入口在 backend/app/main.py。")).toBeInTheDocument();
  expect(screen.getByText("read_file: README.md")).toBeInTheDocument();
});
