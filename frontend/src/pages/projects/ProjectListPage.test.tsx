import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
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
