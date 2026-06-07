import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { ProjectListPage } from "./ProjectListPage";

const {
  mockHttpDelete,
  mockHttpGet,
  mockHttpPatch,
  mockHttpPost,
  mockHttpPut,
} = vi.hoisted(() => ({
  mockHttpGet: vi.fn(),
  mockHttpPost: vi.fn(),
  mockHttpPut: vi.fn(),
  mockHttpPatch: vi.fn(),
  mockHttpDelete: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    get: mockHttpGet,
    post: mockHttpPost,
    put: mockHttpPut,
    patch: mockHttpPatch,
    delete: mockHttpDelete,
  },
}));

function mockProjectQueries(args: {
  listResponses: Array<{ data: { items: ReturnType<typeof buildProject>[]; total: number; page: number; page_size: number; total_pages: number } }>;
  optionsResponse?: {
    data: {
      platform_types: Array<{ label: string; value: string }>;
      template_options: Array<{ id: number; name: string; code: string; description: string | null; file_extensions: string[] }>;
    };
  };
}) {
  const listQueue = [...args.listResponses];
  const optionsResponse = args.optionsResponse ?? {
    data: {
      platform_types: [
        { label: "GitLab", value: "gitlab" },
        { label: "GitHub", value: "github" },
      ],
      template_options: [],
    },
  };

  mockHttpGet.mockImplementation((url: string, config?: { params?: Record<string, unknown> }) => {
    if (url === "/projects/options") {
      return Promise.resolve(optionsResponse);
    }
    if (url === "/projects") {
      if (config?.params !== undefined) {
        lastListProjectsParams = config.params;
      }
      return Promise.resolve(listQueue.shift() ?? args.listResponses.at(-1));
    }
    return Promise.reject(new Error(`Unhandled GET ${url}`));
  });
}

let lastListProjectsParams: Record<string, unknown> | undefined;

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={["/projects"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/projects" element={ui} />
          <Route path="/projects/:projectId/agent" element={<div>项目助手页</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function buildProject(id: number, overrides?: Partial<Record<string, unknown>>) {
  return {
    id,
    name: `项目-${id}`,
    key: `PROJECT-${id}`,
    platform_type: id % 2 === 0 ? "github" : "gitlab",
    repo_url: `https://example.com/repo-${id}.git`,
    default_branch: "main",
    description: `项目 ${id} 的说明`,
    is_active: true,
    review_enabled: true,
    language: id % 2 === 0 ? "TypeScript" : "Python",
    owner: `owner-${id}`,
    score_average: 80 + id,
    last_review_at: `2026-06-${String((id % 9) + 1).padStart(2, "0")}T10:00:00Z`,
    template: null,
    settings: {
      language: id % 2 === 0 ? "TypeScript" : "Python",
      owner: `owner-${id}`,
    },
    created_by: 1,
    created_at: "2026-06-01T10:00:00Z",
    updated_at: "2026-06-01T10:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  mockHttpGet.mockReset();
  mockHttpPost.mockReset();
  mockHttpPut.mockReset();
  mockHttpPatch.mockReset();
  mockHttpDelete.mockReset();
  lastListProjectsParams = undefined;
  vi.restoreAllMocks();
});

test("renders the high-fidelity project management layout with cards", async () => {
  mockProjectQueries({
    listResponses: [{
      data: {
        items: [buildProject(1)],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    }],
  });

  renderWithQuery(<ProjectListPage />);

  expect(await screen.findByText("仓库代码项目管理")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "添加审查仓库" })).toBeInTheDocument();
  expect(screen.getByPlaceholderText("搜索项目名称、唯一标识 key 或是 仓库链接...")).toBeInTheDocument();
  expect(await screen.findByText("KEY: PROJECT-1")).toBeInTheDocument();
  expect(screen.getByText("立即监测")).toBeInTheDocument();
  expect(screen.getByText("手动审查")).toBeInTheDocument();
});

test("opens the add modal and submits a create request", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
      },
      {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
      },
    ],
  });
  mockHttpPost.mockResolvedValueOnce({
    data: buildProject(9, {
      name: "新项目",
      key: "NEW-PROJECT",
      platform_type: "github",
      repo_url: "https://example.com/new-project.git",
      description: "新增项目说明",
      language: "Go",
      owner: "console-owner",
      settings: {
        language: "Go",
        owner: "console-owner",
      },
    }),
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "添加审查仓库" }));

  expect(await screen.findByText("添加新监控审查代码库")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("项目名称 (name)"), {
    target: { value: "新项目" },
  });
  fireEvent.change(screen.getByLabelText("唯一项目标识代码 (key - 唯一约束)"), {
    target: { value: "new-project" },
  });
  fireEvent.change(screen.getByLabelText("托管平台类型 (platform_type)"), {
    target: { value: "github" },
  });
  fireEvent.change(screen.getByLabelText("默认分析分支 (default_branch)"), {
    target: { value: "main" },
  });
  fireEvent.change(screen.getByLabelText("Git 仓库 URL (repo_url)"), {
    target: { value: "https://example.com/new-project.git" },
  });
  fireEvent.change(screen.getByLabelText("偏好展示主要语言"), {
    target: { value: "Go" },
  });
  fireEvent.change(screen.getByLabelText("项目说明 (description)"), {
    target: { value: "新增项目说明" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认保存" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/projects", {
      name: "新项目",
      key: "new-project",
      platform_type: "github",
      repo_url: "https://example.com/new-project.git",
      default_branch: "main",
      description: "新增项目说明",
      template_id: null,
      review_enabled: true,
      settings: {
        language: "Go",
      },
    });
  });
});

test("uses server-backed search, language filters, and pagination", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [
            buildProject(1, { name: "Alpha Service", language: "Python", settings: { language: "Python", owner: "owner-1" } }),
            buildProject(2, { name: "Beta Console", language: "TypeScript", settings: { language: "TypeScript", owner: "owner-2" } }),
            buildProject(3, { name: "Gamma API", language: "Go", settings: { language: "Go", owner: "owner-3" } }),
          ],
          total: 7,
          page: 1,
          page_size: 3,
          total_pages: 3,
        },
      },
      {
        data: {
          items: [
            buildProject(4, { name: "Delta Worker", language: "Java", settings: { language: "Java", owner: "owner-4" } }),
            buildProject(5, { name: "Epsilon UI", language: "React", settings: { language: "React", owner: "owner-5" } }),
            buildProject(6, { name: "Zeta Agent", language: "Rust", settings: { language: "Rust", owner: "owner-6" } }),
          ],
          total: 7,
          page: 2,
          page_size: 3,
          total_pages: 3,
        },
      },
      {
        data: {
          items: [buildProject(7, { name: "Omega Batch", language: "Python", settings: { language: "Python", owner: "owner-7" } })],
          total: 1,
          page: 1,
          page_size: 3,
          total_pages: 1,
        },
      },
      {
        data: {
          items: [buildProject(7, { name: "Omega Batch", language: "Python", settings: { language: "Python", owner: "owner-7" } })],
          total: 1,
          page: 1,
          page_size: 3,
          total_pages: 1,
        },
      },
    ],
  });

  renderWithQuery(<ProjectListPage />);

  expect(await screen.findByText("Alpha Service")).toBeInTheDocument();
  expect(lastListProjectsParams).toEqual({ page: 1, page_size: 6 });

  fireEvent.click(screen.getByRole("button", { name: "下一页" }));
  expect(await screen.findByText("Delta Worker")).toBeInTheDocument();
  expect(lastListProjectsParams).toEqual({ page: 2, page_size: 6 });

  fireEvent.click(screen.getByRole("button", { name: "Python" }));
  await waitFor(() => {
    expect(lastListProjectsParams).toEqual({
      page: 1,
      page_size: 6,
      language: "Python",
    });
  });

  fireEvent.change(screen.getByPlaceholderText("搜索项目名称、唯一标识 key 或是 仓库链接..."), {
    target: { value: "Omega" },
  });
  await waitFor(() => {
    expect(lastListProjectsParams).toEqual({
      page: 1,
      page_size: 6,
      language: "Python",
      search: "Omega",
    });
  });
  expect(await screen.findByText("Omega Batch")).toBeInTheDocument();
});

test("opens the edit modal, shows template binding, and submits an update request", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [
            buildProject(1, {
              name: "项目-1",
              key: "PROJECT-1",
              platform_type: "github",
              repo_url: "https://github.com/acme/project-1.git",
              default_branch: "main",
              description: "原始说明",
              language: "TypeScript",
              owner: "owner-1",
              template: {
                id: 12,
                name: "TS Review Template",
                code: "ts-review-template",
                is_active: true,
                review_prompt_configured: true,
              },
              settings: {
                language: "TypeScript",
                owner: "owner-1",
                external_project_id: "3001",
                external_repo_full_name: "acme/project-1",
              },
            }),
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
      {
        data: {
          items: [
            buildProject(1, {
              name: "项目-1 更新版",
              key: "PROJECT-1",
              platform_type: "github",
              repo_url: "https://github.com/acme/project-1-updated.git",
              default_branch: "release",
              description: "更新说明",
              language: "Go",
              owner: "repo-admin",
              template: {
                id: 15,
                name: "Go Review Template",
                code: "go-review-template",
                is_active: true,
                review_prompt_configured: true,
              },
              settings: {
                language: "Go",
                owner: "repo-admin",
                external_project_id: "9001",
                external_repo_full_name: "acme/project-1-updated",
              },
            }),
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
    ],
    optionsResponse: {
      data: {
        platform_types: [
          { label: "GitLab", value: "gitlab" },
          { label: "GitHub", value: "github" },
        ],
        template_options: [
          {
            id: 12,
            name: "TS Review Template",
            code: "ts-review-template",
            description: "TypeScript template",
            file_extensions: [".ts", ".tsx"],
          },
          {
            id: 15,
            name: "Go Review Template",
            code: "go-review-template",
            description: "Go template",
            file_extensions: [".go"],
          },
        ],
      },
    },
  });
  mockHttpPut.mockResolvedValueOnce({
    data: buildProject(1, {
      name: "项目-1 更新版",
      key: "PROJECT-1",
      platform_type: "github",
      repo_url: "https://github.com/acme/project-1-updated.git",
      default_branch: "release",
      description: "更新说明",
      language: "Go",
      owner: "repo-admin",
      template: {
        id: 15,
        name: "Go Review Template",
        code: "go-review-template",
        is_active: true,
        review_prompt_configured: true,
      },
      settings: {
        language: "Go",
        owner: "repo-admin",
        external_project_id: "9001",
        external_repo_full_name: "acme/project-1-updated",
      },
    }),
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "编辑 项目-1" }));

  expect(await screen.findByText("编辑项目配置")).toBeInTheDocument();
  expect(screen.getByDisplayValue("项目-1")).toBeInTheDocument();
  expect(screen.getByDisplayValue("PROJECT-1")).toBeInTheDocument();
  expect(screen.getByDisplayValue("TS Review Template")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("项目名称 (name)"), {
    target: { value: "项目-1 更新版" },
  });
  fireEvent.change(screen.getByLabelText("默认分析分支 (default_branch)"), {
    target: { value: "release" },
  });
  fireEvent.change(screen.getByLabelText("Git 仓库 URL (repo_url)"), {
    target: { value: "https://github.com/acme/project-1-updated.git" },
  });
  fireEvent.change(screen.getByLabelText("偏好展示主要语言"), {
    target: { value: "Go" },
  });
  fireEvent.change(screen.getByLabelText("归属负责人 (owner)"), {
    target: { value: "repo-admin" },
  });
  fireEvent.change(screen.getByLabelText("外部项目 ID (external_project_id)"), {
    target: { value: "9001" },
  });
  fireEvent.change(screen.getByLabelText("GitHub 仓库全名 (external_repo_full_name)"), {
    target: { value: "acme/project-1-updated" },
  });
  fireEvent.change(screen.getByLabelText("绑定项目模板 (template_id)"), {
    target: { value: "15" },
  });
  fireEvent.change(screen.getByLabelText("项目说明 (description)"), {
    target: { value: "更新说明" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认保存" }));

  await waitFor(() => {
    expect(mockHttpPut).toHaveBeenCalledWith("/projects/1", {
      name: "项目-1 更新版",
      key: "PROJECT-1",
      platform_type: "github",
      repo_url: "https://github.com/acme/project-1-updated.git",
      default_branch: "release",
      description: "更新说明",
      template_id: 15,
      review_enabled: true,
      settings: {
        language: "Go",
        owner: "repo-admin",
        external_project_id: "9001",
        external_repo_full_name: "acme/project-1-updated",
      },
    });
  });
});

test("preserves lowercase project keys when editing existing projects", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [
            buildProject(1, {
              key: "legacy-project",
              settings: {
                language: "TypeScript",
                owner: "owner-1",
                external_repo_full_name: "acme/legacy-project",
              },
            }),
          ],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
    ],
  });
  mockHttpPut.mockResolvedValueOnce({
    data: buildProject(1, {
      key: "legacy-project",
      description: "保持原 key",
    }),
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "编辑 项目-1" }));
  fireEvent.change(screen.getByLabelText("项目说明 (description)"), {
    target: { value: "保持原 key" },
  });
  fireEvent.click(screen.getByRole("button", { name: "确认保存" }));

  await waitFor(() => {
    expect(mockHttpPut).toHaveBeenCalledWith(
      "/projects/1",
      expect.objectContaining({
        key: "legacy-project",
      })
    );
  });
});

test("toggles project status with the card switch", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [buildProject(1, { is_active: true })],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
      {
        data: {
          items: [buildProject(1, { is_active: false })],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
    ],
    optionsResponse: {
      data: {
        platform_types: [{ label: "GitLab", value: "gitlab" }],
        template_options: [],
      },
    },
  });
  mockHttpPatch.mockResolvedValueOnce({
    data: buildProject(1, { is_active: false }),
  });

  renderWithQuery(<ProjectListPage />);

  const toggle = await screen.findByRole("button", { name: "切换 项目-1 启用状态" });
  fireEvent.click(toggle);

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/projects/1/status", {
      is_active: false,
    });
  });
});

test("deletes a project from the card action", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [buildProject(1)],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
      {
        data: {
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
          total_pages: 0,
        },
      },
    ],
    optionsResponse: {
      data: {
        platform_types: [{ label: "GitLab", value: "gitlab" }],
        template_options: [],
      },
    },
  });
  mockHttpDelete.mockResolvedValueOnce({});
  vi.spyOn(window, "confirm").mockReturnValue(true);

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "删除 项目-1" }));

  await waitFor(() => {
    expect(mockHttpDelete).toHaveBeenCalledWith("/projects/1");
  });
});

test("triggers manual review from the card action", async () => {
  mockProjectQueries({
    listResponses: [
      {
        data: {
          items: [buildProject(1)],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
      {
        data: {
          items: [buildProject(1)],
          total: 1,
          page: 1,
          page_size: 20,
          total_pages: 1,
        },
      },
    ],
    optionsResponse: {
      data: {
        platform_types: [{ label: "GitLab", value: "gitlab" }],
        template_options: [],
      },
    },
  });
  mockHttpPost.mockResolvedValueOnce({
    data: {
      review_record_id: 88,
      status: "queued",
      branch: "main",
      last_commit_id: "sha-main-001",
    },
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "手动审查 项目-1" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/projects/1/manual-review");
  });
  expect(await screen.findByText("手动审查任务已入队")).toBeInTheDocument();
});

test("enters the workspace route from 立即监测", async () => {
  mockProjectQueries({
    listResponses: [{
      data: {
        items: [buildProject(1)],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    }],
    optionsResponse: {
      data: {
        platform_types: [{ label: "GitLab", value: "gitlab" }],
        template_options: [],
      },
    },
  });

  renderWithQuery(<ProjectListPage />);

  fireEvent.click(await screen.findByRole("link", { name: "立即监测 项目-1" }));

  expect(await screen.findByText("项目助手页")).toBeInTheDocument();
});
