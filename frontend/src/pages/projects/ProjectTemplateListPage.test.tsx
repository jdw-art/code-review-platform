import type { ReactElement } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { createQueryClient } from "../../lib/query/query-client";
import { ProjectTemplateListPage } from "./ProjectTemplateListPage";

const {
  mockHttpDelete,
  mockHttpGet,
  mockHttpPatch,
  mockHttpPost,
  mockHttpPut,
} = vi.hoisted(() => ({
  mockHttpDelete: vi.fn(),
  mockHttpGet: vi.fn(),
  mockHttpPatch: vi.fn(),
  mockHttpPost: vi.fn(),
  mockHttpPut: vi.fn(),
}));

vi.mock("../../lib/api/http", () => ({
  http: {
    delete: mockHttpDelete,
    get: mockHttpGet,
    patch: mockHttpPatch,
    post: mockHttpPost,
    put: mockHttpPut,
  },
}));

function renderWithQuery(ui: ReactElement) {
  const queryClient = createQueryClient();
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

function buildTemplate(id: number, overrides?: Partial<Record<string, unknown>>) {
  return {
    id,
    name: `模板-${id}`,
    code: `TEMPLATE_${id}`,
    description: `模板 ${id} 的描述`,
    file_extensions: [".ts", ".tsx", ".js"],
    review_prompt_template: `review prompt ${id}`,
    review_prompt_configured: true,
    prompt_metadata: { language: "zh-CN" },
    is_system: false,
    is_active: true,
    created_by: 1,
    created_at: "2026-06-06T10:00:00Z",
    updated_at: "2026-06-06T10:00:00Z",
    ...overrides,
  };
}

function mockTemplateQueries(rows: Array<ReturnType<typeof buildTemplate>>) {
  mockHttpGet.mockImplementation((url: string) => {
    if (url === "/project-templates/options") {
      return Promise.resolve({
        data: {
          common_file_extensions: [".ts", ".tsx", ".js", ".jsx"],
          prompt_metadata_presets: {
            languages: ["zh-CN"],
          },
        },
      });
    }

    if (url === "/project-templates") {
      return Promise.resolve({
        data: {
          items: rows,
          total: rows.length,
          page: 1,
          page_size: 100,
          total_pages: 1,
        },
      });
    }

    return Promise.reject(new Error(`Unhandled GET ${url}`));
  });
}

beforeEach(() => {
  mockHttpDelete.mockReset();
  mockHttpGet.mockReset();
  mockHttpPatch.mockReset();
  mockHttpPost.mockReset();
  mockHttpPut.mockReset();
  vi.restoreAllMocks();
});

test("renders the prototype-like template management layout and expandable prompt panel", async () => {
  mockTemplateQueries([buildTemplate(1, { name: "通用模板", code: "DEFAULT_GENERAL" })]);

  renderWithQuery(<ProjectTemplateListPage />);

  expect(await screen.findByText("审查模板与规则链控制中心")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "添加审查模板" })).toBeInTheDocument();
  expect(
    screen.getByPlaceholderText("检索规则名称、大写特征码(code)或核心说明...")
  ).toBeInTheDocument();
  expect(await screen.findByText("通用模板")).toBeInTheDocument();
  expect(await screen.findByText("DEFAULT_GENERAL")).toBeInTheDocument();

  fireEvent.click(screen.getByRole("button", { name: "展开 Review Prompt: 通用模板" }));

  expect(
    await screen.findByText("代码审计系统大模型元提示词 (review_prompt_template)")
  ).toBeInTheDocument();
  expect(screen.getByText("review prompt 1")).toBeInTheDocument();
});

test("opens the create modal and submits a create request", async () => {
  mockTemplateQueries([]);
  mockHttpPost.mockResolvedValueOnce({
    data: buildTemplate(9, {
      name: "React 模板",
      code: "FRONTEND_REACT",
    }),
  });

  renderWithQuery(<ProjectTemplateListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "添加审查模板" }));

  expect(await screen.findByText("部署高级自定义审查模板")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("模板公开名称"), {
    target: { value: "React 模板" },
  });
  fireEvent.change(screen.getByLabelText("特征大写标识码 (code)"), {
    target: { value: "frontend_react" },
  });
  fireEvent.change(screen.getByLabelText("审查范围描述与核心方向"), {
    target: { value: "React 和 TypeScript 审查" },
  });
  fireEvent.change(screen.getByLabelText("匹配拦截文件后缀 (由英文逗号 `,` 分隔)"), {
    target: { value: ".ts, .tsx, .js, .jsx" },
  });
  fireEvent.change(
    screen.getByLabelText("审查大模型系统级提示词模板 (review_prompt_template)"),
    {
      target: { value: "请审查 React 项目中的性能与依赖项问题" },
    }
  );
  fireEvent.click(screen.getByRole("button", { name: "确认保存" }));

  await waitFor(() => {
    expect(mockHttpPost).toHaveBeenCalledWith("/project-templates", {
      name: "React 模板",
      code: "FRONTEND_REACT",
      description: "React 和 TypeScript 审查",
      file_extensions: [".ts", ".tsx", ".js", ".jsx"],
      review_prompt_template: "请审查 React 项目中的性能与依赖项问题",
      prompt_metadata: {},
      is_active: true,
    });
  });
});

test("updates template status through the prototype switch control", async () => {
  mockTemplateQueries([buildTemplate(2, { name: "后端模板", is_active: true })]);
  mockHttpPatch.mockResolvedValueOnce({
    data: buildTemplate(2, { name: "后端模板", is_active: false }),
  });

  renderWithQuery(<ProjectTemplateListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "停用模板: 后端模板" }));

  await waitFor(() => {
    expect(mockHttpPatch).toHaveBeenCalledWith("/project-templates/2/status", {
      is_active: false,
    });
  });
});

test("deletes a custom template after confirmation", async () => {
  const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
  mockTemplateQueries([buildTemplate(3, { name: "可删除模板", is_system: false })]);
  mockHttpDelete.mockResolvedValueOnce({ data: null });

  renderWithQuery(<ProjectTemplateListPage />);

  fireEvent.click(await screen.findByRole("button", { name: "删除模板: 可删除模板" }));

  await waitFor(() => {
    expect(confirmSpy).toHaveBeenCalledWith(
      "确认删除审查模板“可删除模板”吗？这会影响绑定此类模板的审查工作。"
    );
    expect(mockHttpDelete).toHaveBeenCalledWith("/project-templates/3");
  });

  confirmSpy.mockRestore();
});
