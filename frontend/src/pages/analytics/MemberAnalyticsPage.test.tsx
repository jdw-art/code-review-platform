import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { MemberAnalyticsPage } from "./MemberAnalyticsPage";
import { createQueryClient } from "../../lib/query/query-client";

const { mockListMemberAnalytics } = vi.hoisted(() => ({
  mockListMemberAnalytics: vi.fn(),
}));

vi.mock("../../features/member-analytics/api", () => ({
  listMemberAnalytics: mockListMemberAnalytics,
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

test("renders the member analysis prototype layout with real analytics fields", async () => {
  mockListMemberAnalytics.mockResolvedValueOnce({
    items: [
      {
        project_member_id: 101,
        project_id: 7,
        project_name: "核心支付引擎",
        member_name: "jdw-art",
        member_email: "jdw-art@gmail.com",
        role_name: "架构组组长",
        review_count: 18,
        average_score: 98.2,
        total_additions: 2540,
        total_deletions: 420,
        last_review_at: "2026-06-07T08:45:00Z",
      },
      {
        project_member_id: 102,
        project_id: 9,
        project_name: "风控审计中心",
        member_name: "system-agent",
        member_email: null,
        role_name: null,
        review_count: 4,
        average_score: null,
        total_additions: 450,
        total_deletions: 96,
        last_review_at: null,
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
    total_pages: 1,
  });

  renderWithQuery(<MemberAnalyticsPage />);

  expect(await screen.findByText("jdw-art")).toBeInTheDocument();
  expect(screen.getByText("团队代码提交活跃与规范分析")).toBeInTheDocument();
  expect(screen.getByText("开发组成员质量矩阵 (project_members)")).toBeInTheDocument();
  expect(screen.getByText("智能审计风险追踪")).toBeInTheDocument();

  expect(screen.getByText("jdw-art@gmail.com")).toBeInTheDocument();
  expect(screen.getByText("Role: 架构组组长")).toBeInTheDocument();
  expect(screen.getByText("98.2%")).toBeInTheDocument();
  expect(screen.getAllByText("member_id")).toHaveLength(2);
  expect(screen.getByText("核心支付引擎")).toBeInTheDocument();
  expect(screen.getByText("18 次审查")).toBeInTheDocument();
  expect(screen.getByText("+2540 / -420")).toBeInTheDocument();

  expect(screen.getByText("system-agent")).toBeInTheDocument();
  expect(screen.getByText("未填写邮箱")).toBeInTheDocument();
  expect(screen.getByText("Role: 未设置角色")).toBeInTheDocument();
  expect(screen.getByText("--")).toBeInTheDocument();
  expect(screen.getByText("暂无最近审查")).toBeInTheDocument();

  expect(screen.getByText("平均风险评估级 (Average Risk)")).toBeInTheDocument();
  expect(screen.getByText("系统判定决策值 (Decision Engine)")).toBeInTheDocument();
  expect(screen.getByText(/LOW RISK|GUARDED|MEDIUM RISK|HIGH RISK/)).toBeInTheDocument();
  expect(screen.getByText(/AUTOMERGE|GUARDED-MERGE|MANUAL-REVIEW/)).toBeInTheDocument();

  await waitFor(() => {
    expect(mockListMemberAnalytics).toHaveBeenCalledWith({ page: 1, page_size: 20 });
  });
});

test("renders an explicit loading state instead of the legacy table shell", () => {
  mockListMemberAnalytics.mockImplementationOnce(() => new Promise(() => {}));

  renderWithQuery(<MemberAnalyticsPage />);

  expect(screen.getByText("正在加载成员分析矩阵...")).toBeInTheDocument();
  expect(screen.queryByText("成员分析")).not.toBeInTheDocument();
});

test("renders an explicit error state when member analytics loading fails", async () => {
  mockListMemberAnalytics.mockRejectedValueOnce(new Error("member analytics unavailable"));

  renderWithQuery(<MemberAnalyticsPage />);

  expect(await screen.findByText("成员分析加载失败")).toBeInTheDocument();
  expect(screen.getByText("member analytics unavailable")).toBeInTheDocument();
  expect(screen.queryByText("开发组成员质量矩阵 (project_members)")).not.toBeInTheDocument();
});
