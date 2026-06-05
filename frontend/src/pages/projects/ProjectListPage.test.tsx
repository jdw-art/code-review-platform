import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { toConsoleDashboardOverview } from "../../features/dashboard/serializers";
import {
  toConsoleMemberAnalyticsDetail,
  toConsoleMemberAnalyticsRow,
} from "../../features/member-analytics/serializers";
import { toConsoleProjectTemplate } from "../../features/project-templates/serializers";
import { toConsoleProjectCard } from "../../features/projects/serializers";
import {
  toConsoleReviewDetail,
  toConsoleReviewRecord,
} from "../../features/reviews/serializers";
import { toConsoleRole, toConsoleUser } from "../../features/system/serializers";
import { ProjectListPage } from "./ProjectListPage";
import { ProjectTemplateListPage } from "./ProjectTemplateListPage";

const { mockHttpGet, mockHttpPatch, mockHttpPost, mockHttpPut } = vi.hoisted(() => ({
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

test("根据后端契约渲染项目模板表头", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    },
  });

  renderWithQuery(<ProjectTemplateListPage />);

  expect(await screen.findByText("模板名称")).toBeInTheDocument();
  expect(screen.getByText("文件扩展名")).toBeInTheDocument();
  expect(screen.getByText("Review 提示词")).toBeInTheDocument();
});

test("根据后端契约渲染项目列表表头", async () => {
  mockHttpGet.mockResolvedValueOnce({
    data: {
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
    },
  });

  renderWithQuery(<ProjectListPage />);

  expect(await screen.findByText("项目名称")).toBeInTheDocument();
  expect(screen.getByText("平台")).toBeInTheDocument();
  expect(screen.getByText("项目模板")).toBeInTheDocument();
});

test("点击新建项目后可以打开表单并提交创建请求", async () => {
  mockHttpGet
    .mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      },
    })
    .mockResolvedValueOnce({
      data: {
        platform_types: [
          { label: "GitLab", value: "gitlab" },
          { label: "GitHub", value: "github" },
        ],
        template_options: [],
      },
    })
    .mockResolvedValueOnce({
      data: {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
        total_pages: 0,
      },
    });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      id: 1,
      name: "测试项目",
      key: "demo-project",
      platform_type: "gitlab",
      repo_url: null,
      default_branch: "main",
      description: null,
      is_active: true,
      review_enabled: true,
      template: null,
      settings: {},
      created_by: 1,
      created_at: "2026-05-28T10:00:00Z",
      updated_at: "2026-05-28T10:00:00Z",
    },
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "新建项目" }));

  expect(await screen.findByText("创建项目")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("项目名称"), {
    target: { value: "测试项目" },
  });
  fireEvent.change(screen.getByLabelText("项目标识"), {
    target: { value: "demo-project" },
  });
  fireEvent.change(screen.getByLabelText("平台类型"), {
    target: { value: "gitlab" },
  });
  fireEvent.change(screen.getByLabelText("默认分支"), {
    target: { value: "main" },
  });
  fireEvent.click(screen.getByRole("button", { name: "保存项目" }));

  await waitFor(() => {
    expect(mockHttpGet).toHaveBeenCalledWith("/projects/options");
    expect(mockHttpPost).toHaveBeenCalledWith("/projects", {
      name: "测试项目",
      key: "demo-project",
      platform_type: "gitlab",
      repo_url: null,
      default_branch: "main",
      description: null,
      template_id: null,
      review_enabled: true,
      settings: {},
    });
  });
});

test("maps project response into console card fields", () => {
  const vm = toConsoleProjectCard({
    id: 1,
    name: "ai-code-reviewer",
    key: "AICR",
    platform_type: "GitHub",
    repo_url: "https://github.com/demo/repo.git",
    default_branch: "main",
    description: "demo",
    is_active: true,
    review_enabled: true,
    template: {
      id: 8,
      name: "通用模板",
      code: "DEFAULT_GENERAL",
      is_active: true,
      review_prompt_configured: true,
    },
    settings: {
      language: "TypeScript",
      owner: "jdw-art",
      average_score: 88.5,
      last_review_at: "2026-06-05T10:00:00Z",
    },
    created_by: 1,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  });

  expect(vm.enabled).toBe(true);
  expect(vm.language).toBe("TypeScript");
  expect(vm.scoreAverage).toBe(88.5);
  expect(vm.lastReviewAt).toContain("2026");
});

test("maps project response safely when settings are missing", () => {
  const vm = toConsoleProjectCard({
    id: 2,
    name: "fallback-project",
    key: "FALLBACK",
    platform_type: "GitLab",
    repo_url: null,
    default_branch: "main",
    description: null,
    is_active: false,
    review_enabled: false,
    template: null,
    settings: undefined,
    created_by: null,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  } as never);

  expect(vm.enabled).toBe(false);
  expect(vm.language).toBe("TypeScript");
  expect(vm.owner).toBe("system");
  expect(vm.scoreAverage).toBe(0);
  expect(vm.lastReviewAt).toBe("");
  expect(vm.description).toBe("No description provided.");
});

test("maps project response safely when settings are null", () => {
  const vm = toConsoleProjectCard({
    id: 3,
    name: "null-settings-project",
    key: "NULLS",
    platform_type: "GitHub",
    repo_url: null,
    default_branch: "main",
    description: null,
    is_active: true,
    review_enabled: true,
    template: null,
    settings: null,
    created_by: null,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  } as never);

  expect(vm.language).toBe("TypeScript");
  expect(vm.owner).toBe("system");
  expect(vm.scoreAverage).toBe(0);
  expect(vm.lastReviewAt).toBe("");
});

test("maps dashboard and template serializers safely for partial responses", () => {
  const dashboardVm = toConsoleDashboardOverview({
    total_projects: 0,
    active_projects: 0,
    total_review_records: 0,
    average_score: null,
    active_model_name: null,
    recent_reviews: undefined,
    project_chart: undefined,
    member_chart: null,
  } as never);
  const templateVm = toConsoleProjectTemplate({
    id: 9,
    name: "Template",
    code: "TEMPLATE",
    description: null,
    file_extensions: undefined,
    review_prompt_template: null,
    review_prompt_configured: false,
    prompt_metadata: {},
    is_system: false,
    is_active: true,
    created_by: null,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  } as never);

  expect(dashboardVm.recentReviews).toEqual([]);
  expect(dashboardVm.projectChart).toEqual([]);
  expect(dashboardVm.memberChart).toEqual([]);
  expect(templateVm.fileExtensions).toEqual([]);
  expect(templateVm.fileExtensionsLabel).toBe("");
});

test("maps system serializers safely when nested arrays are absent", () => {
  const userVm = toConsoleUser({
    id: 1,
    username: "admin",
    nickname: null,
    email: null,
    phone: null,
    is_active: true,
    is_superuser: true,
    must_change_password: false,
    roles: undefined,
  } as never);
  const roleVm = toConsoleRole({
    id: 1,
    name: "Admin",
    code: "admin",
    description: null,
    is_system: true,
    permissions: undefined,
    menus: null,
  } as never);

  expect(userVm.roles).toEqual([]);
  expect(roleVm.permissionCount).toBe(0);
  expect(roleVm.menuCount).toBe(0);
});

test("maps review serializers safely when nested arrays are absent", () => {
  const reviewVm = toConsoleReviewRecord({
    id: 1,
    project_id: 1,
    event_type: "push",
    external_event_id: null,
    project_name_snapshot: "demo",
    template_id_snapshot: null,
    template_name_snapshot: null,
    author: "alice",
    title: null,
    branch: null,
    source_branch: null,
    target_branch: null,
    commit_count: 0,
    commit_messages: undefined,
    score: null,
    review_status: "pending",
    review_result: null,
    summary: null,
    url: null,
    url_slug: null,
    last_commit_id: null,
    additions: 0,
    deletions: 0,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
  } as never);
  const reviewDetailVm = toConsoleReviewDetail({
    id: 2,
    project_id: 1,
    event_type: "merge_request",
    external_event_id: null,
    project_name_snapshot: "demo",
    template_id_snapshot: null,
    template_name_snapshot: null,
    author: "bob",
    title: null,
    branch: null,
    source_branch: null,
    target_branch: null,
    commit_count: 0,
    commit_messages: null,
    score: null,
    review_status: "pending",
    review_result: null,
    summary: null,
    url: null,
    url_slug: null,
    last_commit_id: null,
    additions: 0,
    deletions: 0,
    created_at: "2026-06-05T10:00:00Z",
    updated_at: "2026-06-05T10:00:00Z",
    review_prompt_snapshot: null,
    commits: undefined,
  } as never);

  expect(reviewVm.commitMessages).toEqual([]);
  expect(reviewDetailVm.commitMessages).toEqual([]);
  expect(reviewDetailVm.commits).toEqual([]);
});

test("maps member analytics detail safely when recent reviews are absent", () => {
  const rowVm = toConsoleMemberAnalyticsRow({
    project_member_id: 1,
    project_id: 1,
    project_name: "demo",
    member_name: "alice",
    member_email: null,
    role_name: null,
    review_count: 0,
    average_score: null,
    total_additions: 0,
    total_deletions: 0,
    last_review_at: null,
  });
  const detailVm = toConsoleMemberAnalyticsDetail({
    project_member_id: 2,
    project_id: 1,
    project_name: "demo",
    member_name: "bob",
    member_email: null,
    role_name: null,
    review_count: 0,
    average_score: null,
    total_additions: 0,
    total_deletions: 0,
    last_review_at: null,
    recent_reviews: undefined,
  } as never);

  expect(rowVm.totalChanges).toBe(0);
  expect(detailVm.recentReviews).toEqual([]);
});
