import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { ReviewRecordListPage } from "./ReviewRecordListPage";

const { mockHttpGet } = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
  },
}));

function renderWithProviders(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  mockHttpGet.mockReset();
});

test("renders the prototype review records header and search shell", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [
        {
          id: 18,
          project_id: 7,
          event_type: "merge_request",
          external_event_id: "mr-18",
          project_name_snapshot: "ai-review-console",
          template_id_snapshot: 2,
          template_name_snapshot: "TypeScript Web",
          author: "jacob",
          title: "refactor: unify project settings drawer and review pipeline",
          branch: "feat/review-layout",
          source_branch: "feat/review-layout",
          target_branch: "main",
          commit_count: 2,
          commit_messages: ["refactor: unify project settings drawer and review pipeline"],
          score: 92,
          review_status: "completed",
          review_result: "LGTM",
          summary:
            "AI 审查报告指出当前改动结构清晰，边界层职责明确，未发现高危阻断问题。",
          url: "https://example.com/reviews/18",
          url_slug: "reviews-18",
          last_commit_id: "a1b2c3d4e5f6g7h8",
          additions: 126,
          deletions: 18,
          created_at: "2026-06-06T10:00:00Z",
          updated_at: "2026-06-06T10:30:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithProviders(<ReviewRecordListPage />);

  expect(await screen.findByText("智能审查记录控制中心")).toBeInTheDocument();
  expect(mockHttpGet).toHaveBeenCalledWith("/review-records", {
    params: { page: 1, page_size: 5 },
  });
  expect(
    screen.getByPlaceholderText("按照项目名称、提交标题、作者进行全局过滤...")
  ).toBeInTheDocument();
  expect(await screen.findByText("ai-review-console")).toBeInTheDocument();
  expect(screen.getByText("AI 报告诊断意见 (review_result):")).toBeInTheDocument();
  expect(screen.getByText("SCORE评分")).toBeInTheDocument();
  expect(screen.getByText("92分")).toBeInTheDocument();
});

test("filters records with the prototype global search input", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [
        {
          id: 18,
          project_id: 7,
          event_type: "merge_request",
          external_event_id: "mr-18",
          project_name_snapshot: "ai-review-console",
          template_id_snapshot: 2,
          template_name_snapshot: "TypeScript Web",
          author: "jacob",
          title: "refactor: unify project settings drawer and review pipeline",
          branch: "feat/review-layout",
          source_branch: "feat/review-layout",
          target_branch: "main",
          commit_count: 2,
          commit_messages: ["refactor: unify project settings drawer and review pipeline"],
          score: 92,
          review_status: "completed",
          review_result: "LGTM",
          summary: "summary-a",
          url: "https://example.com/reviews/18",
          url_slug: "reviews-18",
          last_commit_id: "a1b2c3d4e5f6g7h8",
          additions: 126,
          deletions: 18,
          created_at: "2026-06-06T10:00:00Z",
          updated_at: "2026-06-06T10:30:00Z",
        },
        {
          id: 19,
          project_id: 8,
          event_type: "push",
          external_event_id: "push-19",
          project_name_snapshot: "design-system",
          template_id_snapshot: 3,
          template_name_snapshot: "React UI",
          author: "pascal",
          title: "fix: align token colors with console sidebar",
          branch: "fix/token-colors",
          source_branch: null,
          target_branch: null,
          commit_count: 1,
          commit_messages: ["fix: align token colors with console sidebar"],
          score: 71,
          review_status: "completed",
          review_result: "needs polish",
          summary: "summary-b",
          url: "https://example.com/reviews/19",
          url_slug: "reviews-19",
          last_commit_id: "z9y8x7w6v5u4t3s2",
          additions: 14,
          deletions: 6,
          created_at: "2026-06-06T09:00:00Z",
          updated_at: "2026-06-06T09:30:00Z",
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithProviders(<ReviewRecordListPage />);

  const searchInput = await screen.findByPlaceholderText(
    "按照项目名称、提交标题、作者进行全局过滤..."
  );

  fireEvent.change(searchInput, { target: { value: "pascal" } });

  await waitFor(() => {
    expect(screen.queryByText("ai-review-console")).not.toBeInTheDocument();
  });
  expect(screen.getByText("design-system")).toBeInTheDocument();
});

test("toggles review_result content between single-line clamp and expanded multi-line view", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [
        {
          id: 20,
          project_id: 9,
          event_type: "merge_request",
          external_event_id: "mr-20",
          project_name_snapshot: "agent-platform",
          template_id_snapshot: 4,
          template_name_snapshot: "Python Service",
          author: "feynman",
          title: "feat: stream review trace into admin console",
          branch: "feat/review-trace",
          source_branch: "feat/review-trace",
          target_branch: "main",
          commit_count: 3,
          commit_messages: ["feat: stream review trace into admin console"],
          score: 88,
          review_status: "completed",
          review_result: "line 1\nline 2\nline 3",
          summary: "line 1\nline 2\nline 3",
          url: "https://example.com/reviews/20",
          url_slug: "reviews-20",
          last_commit_id: "m1n2b3v4c5x6z7a8",
          additions: 88,
          deletions: 22,
          created_at: "2026-06-06T08:00:00Z",
          updated_at: "2026-06-06T08:30:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
      total_pages: 1,
    },
  });

  renderWithProviders(<ReviewRecordListPage />);

  const toggleButton = await screen.findByRole("button", {
    name: "AI 报告诊断意见 (review_result):",
  });
  const summaryText = await screen.findByText(/line 1/);

  expect(toggleButton).toHaveAttribute("aria-expanded", "false");
  expect(summaryText.className).toContain("line-clamp-1");

  fireEvent.click(toggleButton);

  expect(toggleButton).toHaveAttribute("aria-expanded", "true");
  expect(summaryText.className).not.toContain("line-clamp-1");

  fireEvent.click(toggleButton);

  expect(toggleButton).toHaveAttribute("aria-expanded", "false");
  expect(summaryText.className).toContain("line-clamp-1");
});

test("切换审查记录分页参数后会透传给后端接口", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 30,
            project_id: 7,
            event_type: "merge_request",
            external_event_id: "mr-30",
            project_name_snapshot: "ai-review-console",
            template_id_snapshot: 2,
            template_name_snapshot: "TypeScript Web",
            author: "jacob",
            title: "feat: page one",
            branch: "feat/page-one",
            source_branch: "feat/page-one",
            target_branch: "main",
            platform_type: "gitlab",
            delivery_status: "delivered",
            error_message: null,
            retry_count: 0,
            reviewed_at: null,
            failed_at: null,
            commit_count: 1,
            commit_messages: ["feat: page one"],
            score: 92,
            review_status: "completed",
            review_result: "ok",
            summary: "ok",
            url: "https://example.com/reviews/30",
            url_slug: "reviews-30",
            last_commit_id: "a1b2c3d4e5f6g7h8",
            additions: 12,
            deletions: 1,
            created_at: "2026-06-06T10:00:00Z",
            updated_at: "2026-06-06T10:30:00Z",
          },
        ],
        total: 12,
        page: 1,
        page_size: 5,
        total_pages: 3,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 31,
            project_id: 7,
            event_type: "merge_request",
            external_event_id: "mr-31",
            project_name_snapshot: "ai-review-console",
            template_id_snapshot: 2,
            template_name_snapshot: "TypeScript Web",
            author: "jacob",
            title: "feat: size twenty",
            branch: "feat/page-size",
            source_branch: "feat/page-size",
            target_branch: "main",
            platform_type: "gitlab",
            delivery_status: "delivered",
            error_message: null,
            retry_count: 0,
            reviewed_at: null,
            failed_at: null,
            commit_count: 1,
            commit_messages: ["feat: size twenty"],
            score: 88,
            review_status: "completed",
            review_result: "ok",
            summary: "ok",
            url: "https://example.com/reviews/31",
            url_slug: "reviews-31",
            last_commit_id: "b1b2c3d4e5f6g7h8",
            additions: 8,
            deletions: 2,
            created_at: "2026-06-06T10:00:00Z",
            updated_at: "2026-06-06T10:30:00Z",
          },
        ],
        total: 12,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    });

  renderWithProviders(<ReviewRecordListPage />);

  expect(await screen.findByText("feat: page one")).toBeInTheDocument();

  fireEvent.change(screen.getByDisplayValue("5 条"), {
    target: { value: "20" },
  });

  await waitFor(() => {
    expect(mockHttpGet).toHaveBeenLastCalledWith("/review-records", {
      params: { page: 1, page_size: 20 },
    });
  });
});

test("点击审查记录下一页时会透传当前页码", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 40,
            project_id: 7,
            event_type: "merge_request",
            external_event_id: "mr-40",
            project_name_snapshot: "ai-review-console",
            template_id_snapshot: 2,
            template_name_snapshot: "TypeScript Web",
            author: "jacob",
            title: "feat: page one",
            branch: "feat/page-one",
            source_branch: "feat/page-one",
            target_branch: "main",
            platform_type: "gitlab",
            delivery_status: "delivered",
            error_message: null,
            retry_count: 0,
            reviewed_at: null,
            failed_at: null,
            commit_count: 1,
            commit_messages: ["feat: page one"],
            score: 92,
            review_status: "completed",
            review_result: "ok",
            summary: "ok",
            url: "https://example.com/reviews/40",
            url_slug: "reviews-40",
            last_commit_id: "a1b2c3d4e5f6g7h8",
            additions: 12,
            deletions: 1,
            created_at: "2026-06-06T10:00:00Z",
            updated_at: "2026-06-06T10:30:00Z",
          },
        ],
        total: 12,
        page: 1,
        page_size: 5,
        total_pages: 3,
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [
          {
            id: 41,
            project_id: 7,
            event_type: "merge_request",
            external_event_id: "mr-41",
            project_name_snapshot: "ai-review-console",
            template_id_snapshot: 2,
            template_name_snapshot: "TypeScript Web",
            author: "jacob",
            title: "feat: page two",
            branch: "feat/page-two",
            source_branch: "feat/page-two",
            target_branch: "main",
            platform_type: "gitlab",
            delivery_status: "delivered",
            error_message: null,
            retry_count: 0,
            reviewed_at: null,
            failed_at: null,
            commit_count: 1,
            commit_messages: ["feat: page two"],
            score: 88,
            review_status: "completed",
            review_result: "ok",
            summary: "ok",
            url: "https://example.com/reviews/41",
            url_slug: "reviews-41",
            last_commit_id: "b1b2c3d4e5f6g7h8",
            additions: 8,
            deletions: 2,
            created_at: "2026-06-06T10:00:00Z",
            updated_at: "2026-06-06T10:30:00Z",
          },
        ],
        total: 12,
        page: 2,
        page_size: 5,
        total_pages: 3,
      },
    });

  renderWithProviders(<ReviewRecordListPage />);

  expect(await screen.findByText("feat: page one")).toBeInTheDocument();

  fireEvent.click(await screen.findByRole("button", { name: "下一页" }));

  await waitFor(() => {
    expect(mockHttpGet).toHaveBeenLastCalledWith("/review-records", {
      params: { page: 2, page_size: 5 },
    });
  });
});
