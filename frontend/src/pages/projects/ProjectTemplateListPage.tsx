import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  createProjectTemplate,
  getProjectTemplateOptions,
  listProjectTemplates,
  updateProjectTemplate,
  updateProjectTemplateStatus,
  type ProjectTemplateCreatePayload,
  type ProjectTemplateUpdatePayload,
} from "../../features/project-templates/api";
import {
  normalizeOptionalText,
  parseCommaSeparatedList,
  parseJsonObject,
  toPrettyJson,
} from "../../lib/forms/serializers";
import type { ProjectTemplateResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";

interface ProjectTemplateFormState {
  name: string;
  code: string;
  description: string;
  file_extensions_text: string;
  review_prompt_template: string;
  prompt_metadata_text: string;
  is_active: boolean;
}

const emptyTemplateForm: ProjectTemplateFormState = {
  name: "",
  code: "",
  description: "",
  file_extensions_text: ".py, .ts, .tsx",
  review_prompt_template: "",
  prompt_metadata_text: "{}",
  is_active: true,
};

function buildCreatePayload(
  form: ProjectTemplateFormState
): ProjectTemplateCreatePayload {
  return {
    name: form.name.trim(),
    code: form.code.trim(),
    description: normalizeOptionalText(form.description),
    file_extensions: parseCommaSeparatedList(form.file_extensions_text),
    review_prompt_template: normalizeOptionalText(form.review_prompt_template),
    prompt_metadata: parseJsonObject(form.prompt_metadata_text),
    is_active: form.is_active,
  };
}

function buildUpdatePayload(
  form: ProjectTemplateFormState
): ProjectTemplateUpdatePayload {
  return {
    name: form.name.trim(),
    code: form.code.trim(),
    description: normalizeOptionalText(form.description),
    file_extensions: parseCommaSeparatedList(form.file_extensions_text),
    review_prompt_template: normalizeOptionalText(form.review_prompt_template),
    prompt_metadata: parseJsonObject(form.prompt_metadata_text),
  };
}

function buildTemplateForm(row: ProjectTemplateResponse): ProjectTemplateFormState {
  return {
    name: row.name,
    code: row.code,
    description: row.description ?? "",
    file_extensions_text: row.file_extensions.join(", "),
    review_prompt_template: row.review_prompt_template ?? "",
    prompt_metadata_text: toPrettyJson(row.prompt_metadata),
    is_active: row.is_active,
  };
}

/**
 * 项目模板页补齐新增、编辑与启停，方便直接维护提示词模板和扩展名范围。
 */
export function ProjectTemplateListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProjectTemplateResponse | null>(
    null
  );
  const [form, setForm] = useState<ProjectTemplateFormState>(emptyTemplateForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["project-templates", "list"],
    queryFn: () => listProjectTemplates({ page: 1, page_size: 20 }),
  });
  const { data: options } = useQuery({
    queryKey: ["project-templates", "options"],
    queryFn: () => getProjectTemplateOptions(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (editingTemplate === null) {
        return createProjectTemplate(buildCreatePayload(form));
      }
      return updateProjectTemplate(editingTemplate.id, buildUpdatePayload(form));
    },
    onSuccess: async () => {
      setDrawerOpen(false);
      setEditingTemplate(null);
      setForm(emptyTemplateForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["project-templates", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存项目模板失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: ProjectTemplateResponse) =>
      updateProjectTemplateStatus(row.id, !row.is_active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["project-templates", "list"] });
    },
  });

  function openCreateDrawer() {
    setEditingTemplate(null);
    setForm({
      ...emptyTemplateForm,
      file_extensions_text:
        options?.common_file_extensions.slice(0, 3).join(", ") ??
        emptyTemplateForm.file_extensions_text,
    });
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: ProjectTemplateResponse) {
    setEditingTemplate(row);
    setForm(buildTemplateForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function updateField<KeyT extends keyof ProjectTemplateFormState>(
    field: KeyT,
    value: ProjectTemplateFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    try {
      await saveMutation.mutateAsync();
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("提示词元数据 JSON 解析失败，请检查格式。");
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存项目模板失败。");
      }
    }
  }

  const templateColumns: DataTableColumn<ProjectTemplateResponse>[] = [
    {
      key: "name",
      title: "模板名称",
    },
    {
      key: "description",
      title: "描述",
      render: (row) => row.description || "-",
    },
    {
      key: "file_extensions",
      title: "文件扩展名",
      render: (row) => row.file_extensions.join(", "),
    },
    {
      key: "review_prompt_configured",
      title: "Review 提示词",
      render: (row) => (row.review_prompt_configured ? "已配置" : "未配置"),
    },
    {
      key: "is_active",
      title: "状态",
      render: (row) => <StatusBadge value={row.is_active} />,
    },
    {
      key: "actions",
      title: "操作",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => openEditDrawer(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => void statusMutation.mutateAsync(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            {row.is_active ? "停用" : "启用"}
          </button>
        </div>
      ),
    },
  ];

  return (
    <>
      <PageCard
        title="项目模板管理"
        description="查看文件扩展名覆盖范围、Review 提示词配置状态与模板启停状态。"
        actions={
          <button
            type="button"
            onClick={openCreateDrawer}
            className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            新建模板
          </button>
        }
      >
        <DataTable
          columns={templateColumns}
          rows={data?.items ?? []}
          loading={isLoading}
          emptyText="暂无项目模板数据"
        />
      </PageCard>

      <DrawerForm
        open={drawerOpen}
        title={editingTemplate === null ? "创建项目模板" : "编辑项目模板"}
        description="维护模板编码、扩展名范围和 Review 提示词。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-5" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            模板名称
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            模板编码
            <input
              value={form.code}
              onChange={(event) => updateField("code", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            文件扩展名
            <input
              value={form.file_extensions_text}
              onChange={(event) => updateField("file_extensions_text", event.target.value)}
              className={inputClassName}
            />
            <span className="mt-2 block text-xs text-slate-500">
              使用逗号分隔，例如：.py, .ts, .tsx
            </span>
          </label>

          <label className={labelClassName}>
            描述
            <textarea
              value={form.description}
              onChange={(event) => updateField("description", event.target.value)}
              className={`${inputClassName} min-h-24`}
            />
          </label>

          <label className={labelClassName}>
            Review 提示词
            <textarea
              value={form.review_prompt_template}
              onChange={(event) =>
                updateField("review_prompt_template", event.target.value)
              }
              className={`${inputClassName} min-h-32`}
            />
          </label>

          <label className={labelClassName}>
            提示词元数据 JSON
            <textarea
              value={form.prompt_metadata_text}
              onChange={(event) =>
                updateField("prompt_metadata_text", event.target.value)
              }
              className={`${inputClassName} min-h-32 font-mono text-xs`}
            />
          </label>

          {editingTemplate === null ? (
            <label className="flex items-center gap-3 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => updateField("is_active", event.target.checked)}
              />
              创建后立即启用
            </label>
          ) : null}

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saveMutation.isPending ? "保存中..." : "保存模板"}
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
