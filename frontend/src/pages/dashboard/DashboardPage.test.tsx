import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { DashboardPage } from "./DashboardPage";
import { createQueryClient } from "../../lib/query/query-client";

const { mockHttpGet } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
  },
}));

vi.mock("../../lib/auth/auth-context", () => ({
  useAuth: () => ({
    user: {
      id: 1,
      username: "admin",
      nickname: "管理员",
      email: "admin@example.com",
      phone: null,
      is_active: true,
      is_superuser: true,
    },
  }),
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test("renders the high-fidelity console dashboard from a single overview query", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      total_projects: 6,
      active_projects: 4,
      total_review_records: 31,
      average_score: 87.4,
      active_model_name: "Gemini 2.5 Pro",
      recent_reviews: [
        {
          id: 101,
          project_name: "Payments API",
          title: "Harden webhook signature validation",
          branch: "hotfix/signature",
          commit_hash: "a1b2c3d4",
          committer: "alice",
          score: 92,
          review_status: "reviewed",
          summary: "Closed the signature timing leak and added regression coverage.",
          created_at: "2026-06-05T09:20:00Z",
        },
      ],
      project_chart: [
        {
          project_id: 1,
          name: "Payments API",
          commits: 12,
          avg_score: 91.5,
          additions: 1420,
          deletions: 430,
        },
        {
          project_id: 2,
          name: "Console Web",
          commits: 9,
          avg_score: 85.2,
          additions: 2180,
          deletions: 810,
        },
      ],
      member_chart: [
        {
          project_id: null,
          name: "alice",
          commits: 8,
          avg_score: 93.1,
          additions: 920,
          deletions: 230,
        },
        {
          project_id: null,
          name: "bob",
          commits: 7,
          avg_score: null,
          additions: 1110,
          deletions: 410,
        },
      ],
      models: [
        {
          id: 1,
          name: "Gemini 2.5 Pro",
          provider: "google",
          temperature: 0.2,
          is_default: true,
          is_active: true,
        },
        {
          id: 2,
          name: "Claude 3.7 Sonnet",
          provider: "anthropic",
          temperature: 0.1,
          is_default: false,
          is_active: true,
        },
      ],
      repo_health: [
        {
          project_id: 1,
          name: "Payments API",
          is_active: true,
          review_count: 12,
          average_score: 91.5,
          last_review_at: "2026-06-05T09:20:00Z",
        },
        {
          project_id: 2,
          name: "Legacy Worker",
          is_active: false,
          review_count: 4,
          average_score: 76.2,
          last_review_at: "2026-06-04T08:15:00Z",
        },
      ],
    },
  });

  renderWithQuery(<DashboardPage />);

  expect(await screen.findByText("管理员，欢迎进入代码复审控制中心")).toBeInTheDocument();
  expect(
    await screen.findByText("Harden webhook signature validation")
  ).toBeInTheDocument();
  expect(screen.getByText("活动模型: Gemini 2.5 Pro")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "仓库项目配置" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "切换审核模型" })).toBeInTheDocument();

  expect(screen.getByText("实时审查流水线监视器")).toBeInTheDocument();
  expect(screen.getByText("Harden webhook signature validation")).toBeInTheDocument();
  expect(screen.getByText("当前智算节点")).toBeInTheDocument();
  expect(screen.getByText("Claude 3.7 Sonnet")).toBeInTheDocument();
  expect(screen.getByText("仓库健康审查")).toBeInTheDocument();
  expect(screen.getByText("Legacy Worker")).toBeInTheDocument();

  expect(screen.getByText("研发效能可视化度量中心")).toBeInTheDocument();
  expect(screen.getByText("各项目代码提交频次")).toBeInTheDocument();
  expect(screen.getByText("成员代码质量评分指数")).toBeInTheDocument();
  expect(screen.getByText("均分: -")).toBeInTheDocument();
  expect(screen.getAllByText("Payments API").length).toBeGreaterThan(0);
});

test("renders an explicit loading state instead of fake zero metrics", () => {
  mockHttpGet.mockImplementationOnce(() => new Promise(() => {}));

  renderWithQuery(<DashboardPage />);

  expect(screen.getByText("正在加载仪表盘概览...")).toBeInTheDocument();
  expect(screen.queryByText("项目总数")).not.toBeInTheDocument();
});

test("renders an explicit error state when overview loading fails", async () => {
  mockHttpGet.mockRejectedValueOnce(new Error("overview unavailable"));

  renderWithQuery(<DashboardPage />);

  expect(await screen.findByText("仪表盘概览加载失败")).toBeInTheDocument();
  expect(screen.getByText("overview unavailable")).toBeInTheDocument();
  expect(screen.queryByText("项目总数")).not.toBeInTheDocument();
});

test("renders duplicate project names without duplicate React keys", async () => {
  const consoleErrorSpy = vi
    .spyOn(console, "error")
    .mockImplementation(() => undefined);

  mockHttpGet.mockResolvedValueOnce({
    data: {
      total_projects: 2,
      active_projects: 2,
      total_review_records: 2,
      average_score: 86,
      active_model_name: null,
      recent_reviews: [],
      project_chart: [
        {
          project_id: 11,
          name: "Shared Name",
          commits: 6,
          avg_score: 89,
          additions: 320,
          deletions: 120,
        },
        {
          project_id: 29,
          name: "Shared Name",
          commits: 4,
          avg_score: 83,
          additions: 210,
          deletions: 95,
        },
      ],
      member_chart: [],
      models: [],
      repo_health: [],
    },
  });

  renderWithQuery(<DashboardPage />);

  expect(await screen.findAllByText("Shared Name")).toHaveLength(6);
  expect(consoleErrorSpy).not.toHaveBeenCalledWith(
    expect.stringContaining('Encountered two children with the same key')
  );

  consoleErrorSpy.mockRestore();
});
