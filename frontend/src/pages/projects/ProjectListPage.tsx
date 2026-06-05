import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  createProject,
  getProjectOptions,
  listProjects,
  updateProject,
  updateProjectStatus,
  type ProjectPayload,
} from "../../features/projects/api";
import {
  normalizeOptionalText,
  parseJsonObject,
  toPrettyJson,
} from "../../lib/forms/serializers";
import type { ProjectResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";

interface ProjectFormState {
  name: string;
  key: string;
  platform_type: string;
  repo_url: string;
  default_branch: string;
  description: string;
  template_id: string;
  review_enabled: boolean;
  settings_text: string;
}

const emptyProjectForm: ProjectFormState = {
  name: "",
  key: "",
  platform_type: "gitlab",
  repo_url: "",
  default_branch: "main",
  description: "",
  template_id: "",
  review_enabled: true,
  settings_text: "{}",
};

function buildProjectPayload(form: ProjectFormState): ProjectPayload {
  return {
    name: form.name.trim(),
    key: form.key.trim(),
    platform_type: form.platform_type.trim(),
    repo_url: normalizeOptionalText(form.repo_url),
    default_branch: form.default_branch.trim(),
    description: normalizeOptionalText(form.description),
    template_id: form.template_id === "" ? null : Number(form.template_id),
    review_enabled: form.review_enabled,
    settings: parseJsonObject(form.settings_text),
  };
}

function buildProjectForm(row: ProjectResponse): ProjectFormState {
  return {
    name: row.name,
    key: row.key,
    platform_type: row.platform_type,
    repo_url: row.repo_url ?? "",
    default_branch: row.default_branch,
    description: row.description ?? "",
    template_id: row.template?.id ? String(row.template.id) : "",
    review_enabled: row.review_enabled,
    settings_text: toPrettyJson(row.settings ?? {}),
  };
}

/**
 * 项目管理页先把列表、创建、编辑与启停串起来，确保后台能实际维护项目数据。
 */
export function ProjectListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<ProjectResponse | null>(null);
  const [form, setForm] = useState<ProjectFormState>(emptyProjectForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["projects", "list"],
    queryFn: () => listProjects({ page: 1, page_size: 20 }),
  });
  const { data: options } = useQuery({
    queryKey: ["projects", "options"],
    queryFn: () => getProjectOptions(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = buildProjectPayload(form);
      if (editingProject === null) {
        return createProject(payload);
      }
      return updateProject(editingProject.id, payload);
    },
    onSuccess: async () => {
      setDrawerOpen(false);
      setEditingProject(null);
      setForm(emptyProjectForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存项目失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: ProjectResponse) =>
      updateProjectStatus(row.id, !row.is_active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
  });

  function openCreateDrawer() {
    setEditingProject(null);
    setForm({
      ...emptyProjectForm,
      platform_type: options?.platform_types[0]?.value ?? "gitlab",
    });
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: ProjectResponse) {
    setEditingProject(row);
    setForm(buildProjectForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function updateField<KeyT extends keyof ProjectFormState>(
    field: KeyT,
    value: ProjectFormState[KeyT]
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
        setErrorMessage("设置 JSON 解析失败，请检查格式。");
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存项目失败。");
      }
    }
  }

  const projectColumns: DataTableColumn<ProjectResponse>[] = [
    {
      key: "name",
      title: "项目名称",
    },
    {
      key: "platform_type",
      title: "平台",
      render: (row) => row.platform_type || "-",
    },
    {
      key: "default_branch",
      title: "默认分支",
    },
    {
      key: "template",
      title: "项目模板",
      render: (row) => row.template?.name ?? "未绑定",
    },
    {
      key: "review_enabled",
      title: "审查开关",
      render: (row) => <StatusBadge value={row.review_enabled} />,
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
          <Link
            to={`/projects/${row.id}/agent`}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            仓库助手
          </Link>
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
        title="项目管理"
        description="查看受管代码项目、绑定模板与基础审查开关状态。"
        actions={
          <button
            type="button"
            onClick={openCreateDrawer}
            className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            新建项目
          </button>
        }
      >
        <DataTable
          columns={projectColumns}
          rows={data?.items ?? []}
          loading={isLoading}
          emptyText="暂无项目数据"
        />
      </PageCard>

      <DrawerForm
        open={drawerOpen}
        title={editingProject === null ? "创建项目" : "编辑项目"}
        description="填写项目基本信息、绑定模板和默认审查配置。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-5" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            项目名称
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            项目标识
            <input
              value={form.key}
              onChange={(event) => updateField("key", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            平台类型
            <select
              value={form.platform_type}
              onChange={(event) => updateField("platform_type", event.target.value)}
              className={inputClassName}
            >
              {(options?.platform_types ?? []).map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className={labelClassName}>
            仓库地址
            <input
              value={form.repo_url}
              onChange={(event) => updateField("repo_url", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            默认分支
            <input
              value={form.default_branch}
              onChange={(event) => updateField("default_branch", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            绑定模板
            <select
              value={form.template_id}
              onChange={(event) => updateField("template_id", event.target.value)}
              className={inputClassName}
            >
              <option value="">不绑定模板</option>
              {(options?.template_options ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
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
            设置 JSON
            <textarea
              value={form.settings_text}
              onChange={(event) => updateField("settings_text", event.target.value)}
              className={`${inputClassName} min-h-32 font-mono text-xs`}
            />
          </label>

          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.review_enabled}
              onChange={(event) => updateField("review_enabled", event.target.checked)}
            />
            启用审查
          </label>

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
              {saveMutation.isPending ? "保存中..." : "保存项目"}
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
