import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useMemo, useState } from "react";
import {
  Check,
  Edit3,
  FileCode,
  FileJson,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";

import {
  createProjectTemplate,
  deleteProjectTemplate,
  getProjectTemplateOptions,
  listProjectTemplates,
  updateProjectTemplate,
  updateProjectTemplateStatus,
  type ProjectTemplateCreatePayload,
  type ProjectTemplateUpdatePayload,
} from "../../features/project-templates/api";
import { ConsoleToast } from "../../components/console/ConsoleToast";
import {
  normalizeOptionalText,
  parseCommaSeparatedList,
} from "../../lib/forms/serializers";
import type { ProjectTemplateResponse } from "../../lib/api/types";

interface ProjectTemplateFormState {
  name: string;
  code: string;
  description: string;
  fileExtensionsText: string;
  reviewPromptTemplate: string;
  isActive: boolean;
}

const emptyTemplateForm: ProjectTemplateFormState = {
  name: "",
  code: "",
  description: "",
  fileExtensionsText: "ts, tsx, js, jsx",
  reviewPromptTemplate: "你是一个资深的研发主管。请对以下代码进行详细审查并提供建议：",
  isActive: true,
};

const LANGUAGE_PRESETS = [
  { name: "React / Web 前端", extensions: "ts, tsx, js, jsx, css, html", code: "FRONTEND_REACT" },
  { name: "Golang 核心后端", extensions: "go, sql, proto, yaml", code: "BACKEND_GO" },
  { name: "Enterprise Java", extensions: "java, xml, sql, properties", code: "BACKEND_JAVA" },
  { name: "Python 机器学习", extensions: "py, ipynb, json, txt", code: "PYTHON_ML" },
];

function buildCreatePayload(
  form: ProjectTemplateFormState
): ProjectTemplateCreatePayload {
  return {
    name: form.name.trim(),
    code: form.code.trim().toUpperCase(),
    description: normalizeOptionalText(form.description),
    file_extensions: parseCommaSeparatedList(form.fileExtensionsText).map((ext) =>
      ext.startsWith(".") ? ext : `.${ext}`
    ),
    review_prompt_template: normalizeOptionalText(form.reviewPromptTemplate),
    prompt_metadata: {},
    is_active: form.isActive,
  };
}

function buildUpdatePayload(
  form: ProjectTemplateFormState
): ProjectTemplateUpdatePayload {
  return {
    name: form.name.trim(),
    code: form.code.trim().toUpperCase(),
    description: normalizeOptionalText(form.description),
    file_extensions: parseCommaSeparatedList(form.fileExtensionsText).map((ext) =>
      ext.startsWith(".") ? ext : `.${ext}`
    ),
    review_prompt_template: normalizeOptionalText(form.reviewPromptTemplate),
    prompt_metadata: {},
  };
}

function buildTemplateForm(row: ProjectTemplateResponse): ProjectTemplateFormState {
  return {
    name: row.name,
    code: row.code,
    description: row.description ?? "",
    fileExtensionsText: (row.file_extensions ?? [])
      .map((ext) => ext.replace(/^\./, ""))
      .join(", "),
    reviewPromptTemplate: row.review_prompt_template ?? "",
    isActive: row.is_active,
  };
}

/**
 * 以控制台原型为基准重建模板页，同时保持真实模板 CRUD 与启停接口联调。
 */
export function ProjectTemplateListPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [expandedTemplateId, setExpandedTemplateId] = useState<number | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<ProjectTemplateResponse | null>(null);
  const [form, setForm] = useState<ProjectTemplateFormState>(emptyTemplateForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["project-templates", "list"],
    queryFn: () => listProjectTemplates({ page: 1, page_size: 100 }),
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
    onSuccess: async (_, variables) => {
      setIsModalOpen(false);
      setEditingTemplate(null);
      setForm(emptyTemplateForm);
      setErrorMessage(null);
      setSuccessMessage(
        editingTemplate === null ? "审查模板已成功创建。" : "审查模板参数已更新。"
      );
      await queryClient.invalidateQueries({ queryKey: ["project-templates", "list"] });
      return variables;
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存项目模板失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: ProjectTemplateResponse) =>
      updateProjectTemplateStatus(row.id, !row.is_active),
    onSuccess: async (_, row) => {
      setSuccessMessage(
        row.is_active ? `模板 ${row.name} 已停用。` : `模板 ${row.name} 已启用。`
      );
      await queryClient.invalidateQueries({ queryKey: ["project-templates", "list"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (row: ProjectTemplateResponse) => deleteProjectTemplate(row.id),
    onSuccess: async (_, row) => {
      setSuccessMessage(`模板 ${row.name} 已删除。`);
      await queryClient.invalidateQueries({ queryKey: ["project-templates", "list"] });
    },
  });

  const filteredTemplates = useMemo(() => {
    const rows = data?.items ?? [];
    const keyword = search.trim().toLowerCase();
    if (keyword.length === 0) {
      return rows;
    }

    return rows.filter((row) => {
      const description = row.description ?? "";
      return (
        row.name.toLowerCase().includes(keyword) ||
        row.code.toLowerCase().includes(keyword) ||
        description.toLowerCase().includes(keyword)
      );
    });
  }, [data?.items, search]);

  function updateField<KeyT extends keyof ProjectTemplateFormState>(
    field: KeyT,
    value: ProjectTemplateFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function openCreateModal() {
    setEditingTemplate(null);
    setForm({
      ...emptyTemplateForm,
      fileExtensionsText:
        options?.common_file_extensions
          .slice(0, 4)
          .map((ext) => ext.replace(/^\./, ""))
          .join(", ") ?? emptyTemplateForm.fileExtensionsText,
    });
    setErrorMessage(null);
    setIsModalOpen(true);
  }

  function openEditModal(row: ProjectTemplateResponse) {
    setEditingTemplate(row);
    setForm(buildTemplateForm(row));
    setErrorMessage(null);
    setIsModalOpen(true);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);

    try {
      await saveMutation.mutateAsync();
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存项目模板失败。");
      }
    }
  }

  async function handleDelete(row: ProjectTemplateResponse) {
    const confirmed = window.confirm(
      `确认删除审查模板“${row.name}”吗？这会影响绑定此类模板的审查工作。`
    );
    if (!confirmed) {
      return;
    }

    try {
      await deleteMutation.mutateAsync(row);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "删除模板失败。");
    }
  }

  return (
    <>
      <div className="max-w-7xl mx-auto space-y-4 p-6">
        <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-white px-5 py-3.5 shadow-3xs sm:flex-row sm:items-center">
          <div>
            <h2 className="flex items-center gap-1.5 font-sans text-sm font-bold text-slate-800">
              <FileJson className="h-4 w-4 shrink-0 text-indigo-500" />
              <span>审查模板与规则链控制中心</span>
            </h2>
            <p className="mt-0.5 text-[11px] text-slate-500">
              在此配置并开启自动 PR/MR 定制审查规则。核心字段名完全对齐 PostgreSQL{" "}
              <code className="rounded bg-slate-100 px-1 text-[10px] font-mono text-indigo-650">
                project_templates
              </code>{" "}
              表结构。
            </p>
          </div>
          <button
            type="button"
            onClick={openCreateModal}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-[#0a0b14] px-3.5 py-1.5 text-[11px] font-bold text-white shadow-2xs transition-all active:scale-[0.98] hover:bg-slate-900"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>添加审查模板</span>
          </button>
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-slate-200/80 bg-white p-3 shadow-3xs">
          <Search className="ml-1.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="检索规则名称、大写特征码(code)或核心说明..."
            className="w-full border-none bg-transparent text-xs text-slate-800 outline-hidden placeholder:text-slate-400"
          />
        </div>

        <div className="space-y-3">
          {filteredTemplates.length === 0 ? (
            <div className="rounded-xl border border-slate-200/85 bg-white p-12 text-center text-xs text-slate-400">
              暂无匹配的代码片段和审查约束模板
            </div>
          ) : (
            filteredTemplates.map((row) => {
              const isExpanded = expandedTemplateId === row.id;
              const fileExtensions = row.file_extensions ?? [];
              return (
                <div
                  key={row.id}
                  className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white shadow-3xs transition-all hover:border-slate-300"
                >
                  <div className="flex flex-col items-start justify-between gap-4 p-4 md:flex-row md:items-center md:p-5">
                    <div className="grow min-w-0 space-y-1.5">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-bold text-slate-800">{row.name}</span>
                        <span className="rounded border border-indigo-100/50 bg-indigo-50 px-1.5 py-[1px] font-mono text-[9px] font-semibold uppercase text-indigo-600">
                          {row.code}
                        </span>
                        {row.is_system ? (
                          <span className="rounded-xs bg-slate-150 px-1.5 text-[9px] font-semibold text-slate-600">
                            系统自带
                          </span>
                        ) : null}
                        {row.review_prompt_configured ? (
                          <span className="inline-flex items-center gap-1 rounded-xs border border-emerald-100 bg-emerald-50 px-1.5 py-[1px] text-[9px] font-semibold text-emerald-700">
                            <Check className="h-2.5 w-2.5" />
                            <span>Prompt 已配置</span>
                          </span>
                        ) : null}
                      </div>

                      <p className="line-clamp-2 text-xs font-light leading-normal text-slate-500 md:line-clamp-1">
                        {row.description || "暂无详细描述信息。"}
                      </p>

                      <div className="flex select-none flex-wrap items-center gap-2 pt-0.5 text-[10px] text-slate-400">
                        <span className="font-mono font-medium text-slate-500">后缀拦截:</span>
                        <div className="flex flex-wrap gap-1">
                          {fileExtensions.map((ext) => (
                            <span
                              key={ext}
                              className="rounded-xs bg-slate-100 px-1.5 text-[9.5px] font-mono text-slate-600"
                            >
                              {ext.startsWith(".") ? ext : `.${ext}`}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    <div className="flex w-full shrink-0 items-center justify-between gap-4 border-t pt-3 md:w-auto md:justify-end md:border-t-0 md:pt-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold tracking-wider text-slate-400">
                          STATUS
                        </span>
                        <button
                          type="button"
                          aria-label={`${row.is_active ? "停用" : "启用"}模板: ${row.name}`}
                          onClick={() => void statusMutation.mutateAsync(row)}
                          className={`relative h-5 w-9 cursor-pointer rounded-full p-0.5 transition-colors ${
                            row.is_active ? "bg-indigo-600" : "bg-slate-200"
                          }`}
                        >
                          <div
                            className={`h-4 w-4 transform rounded-full bg-white shadow-3xs transition-transform ${
                              row.is_active ? "translate-x-4" : "translate-x-0"
                            }`}
                          />
                        </button>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          aria-label={`${isExpanded ? "收起" : "展开"} Review Prompt: ${row.name}`}
                          onClick={() =>
                            setExpandedTemplateId(isExpanded ? null : row.id)
                          }
                          className="rounded-md border border-slate-200 p-1.5 text-slate-500 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-700"
                          title={isExpanded ? "收起 Review Prompt" : "展开 Review Prompt"}
                        >
                          <FileCode className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          aria-label={`编辑模板: ${row.name}`}
                          onClick={() => openEditModal(row)}
                          className="rounded-md border border-slate-200 p-1.5 text-indigo-650 transition hover:border-indigo-150 hover:bg-indigo-50 hover:text-indigo-700"
                          title="编辑模板参数"
                        >
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          aria-label={`删除模板: ${row.name}`}
                          disabled={row.is_system || deleteMutation.isPending}
                          onClick={() => void handleDelete(row)}
                          className="rounded-md border border-slate-200 p-1.5 text-rose-650 transition hover:border-rose-150 hover:bg-rose-50 hover:text-rose-700 disabled:cursor-not-allowed disabled:opacity-40"
                          title="删除模板"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {isExpanded ? (
                    <div className="flex flex-col gap-2 border-t border-slate-100 bg-slate-50/50 p-4">
                      <div className="flex items-center gap-1 text-[11px] font-bold text-slate-700">
                        <Sparkles className="h-3.5 w-3.5 animate-pulse text-amber-500" />
                        <span>代码审计系统大模型元提示词 (review_prompt_template)</span>
                      </div>
                      <pre className="max-h-[240px] overflow-y-auto whitespace-pre-wrap rounded-lg border border-slate-200/80 bg-white p-3 font-mono text-[11px] leading-relaxed text-slate-600">
                        {row.review_prompt_template || "暂无 Prompt 配置。"}
                      </pre>
                    </div>
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      </div>

      {isModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div
            role="dialog"
            aria-modal="true"
            className="flex max-h-[90vh] w-full max-w-xl flex-col overflow-hidden rounded-2xl border border-slate-205 bg-white shadow-xl"
          >
            <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/50 px-6 py-4.5">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-650 shadow-3xs">
                  <FileJson className="h-4 w-4 text-indigo-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-800">
                    {editingTemplate ? "编辑审查决策模板参数" : "部署高级自定义审查模板"}
                  </h3>
                  <p className="mt-0.5 text-[10px] font-sans text-slate-450">
                    挂载模型规则链对所有匹配 PR 分支代码实施拦截审查与安全阻断
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="cursor-pointer rounded-lg p-1 text-slate-400 transition hover:bg-slate-100/80 hover:text-slate-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 text-left space-y-4.5">
              {errorMessage ? (
                <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
                  {errorMessage}
                </div>
              ) : null}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <label className="space-y-1.5 text-xs font-semibold text-slate-700">
                  <span>
                    模板公开名称 <span className="text-rose-500">*</span>
                  </span>
                  <input
                    aria-label="模板公开名称"
                    required
                    value={form.name}
                    onChange={(event) => updateField("name", event.target.value)}
                    placeholder="例如: Go 微服务代码规范模板"
                    className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 shadow-3xs/5 transition focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-xs font-semibold text-slate-700">
                  <span>
                    特征大写标识码 (code) <span className="text-rose-500">*</span>
                  </span>
                  <input
                    aria-label="特征大写标识码 (code)"
                    required
                    value={form.code}
                    onChange={(event) => updateField("code", event.target.value.toUpperCase())}
                    placeholder="例如: GO_MICRO_STANDARD"
                    className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs uppercase text-slate-800 shadow-3xs/5 transition focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>
              </div>

              <label className="space-y-1.5 text-xs font-semibold text-slate-700">
                <span>审查范围描述与核心方向</span>
                <textarea
                  aria-label="审查范围描述与核心方向"
                  rows={2}
                  value={form.description}
                  onChange={(event) => updateField("description", event.target.value)}
                  placeholder="针对此类模板所应用的业务场景、过滤侧重点补充说明语..."
                  className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 shadow-3xs/5 transition focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10"
                />
              </label>

              <div className="space-y-1.5 rounded-xl border border-slate-200/60 bg-slate-50/50 p-3.5 shadow-3xs/5">
                <div className="flex flex-wrap items-center justify-between gap-1">
                  <label className="text-xs font-semibold text-slate-700">
                    匹配拦截文件后缀 (由英文逗号 `,` 分隔) <span className="text-rose-500">*</span>
                  </label>
                  <span className="text-[10px] text-slate-400">点击下方预设快速填入:</span>
                </div>

                <div className="flex flex-wrap gap-1.5 pb-2 pt-1">
                  {LANGUAGE_PRESETS.map((preset) => (
                    <button
                      key={preset.name}
                      type="button"
                      onClick={() => {
                        updateField("fileExtensionsText", preset.extensions);
                        if (form.name.trim().length === 0) {
                          updateField("name", `${preset.name}代码规范审查模版`);
                        }
                        if (form.code.trim().length === 0) {
                          updateField("code", preset.code);
                        }
                      }}
                      className="rounded border border-slate-200 bg-white px-2 py-0.5 text-[10px] text-slate-600 shadow-3xs transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-650"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>

                <input
                  aria-label="匹配拦截文件后缀 (由英文逗号 `,` 分隔)"
                  required
                  value={form.fileExtensionsText}
                  onChange={(event) => updateField("fileExtensionsText", event.target.value)}
                  placeholder="ts, tsx, js, jsx, css"
                  className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 shadow-3xs/5 transition focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10"
                />
                <p className="mt-1 text-[10.5px] font-sans leading-normal text-slate-400">
                  只有后缀名在列表内的修改文件，才会被大模型纳入该模板审查流程中。
                </p>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700">
                    审查大模型系统级提示词模板 (review_prompt_template){" "}
                    <span className="text-rose-500">*</span>
                  </label>
                  <span className="font-mono text-[10px] font-medium text-indigo-600">
                    System Prompt
                  </span>
                </div>
                <textarea
                  aria-label="审查大模型系统级提示词模板 (review_prompt_template)"
                  required
                  rows={5}
                  value={form.reviewPromptTemplate}
                  onChange={(event) =>
                    updateField("reviewPromptTemplate", event.target.value)
                  }
                  placeholder="请输入用于审查的核心 Prompt..."
                  className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2.5 font-mono text-xs leading-relaxed text-slate-800 shadow-3xs/5 transition focus:border-indigo-500 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10"
                />
                <p className="text-[10px] text-slate-400">
                  大模型扮演的角色声明、缺陷扫描深度度量标准或安全基线提示。
                </p>
              </div>

              <div className="flex items-center justify-between rounded-xl border border-slate-200/80 bg-slate-50 p-3.5 shadow-3xs transition">
                <div className="space-y-0.5 text-left">
                  <label className="block select-none text-xs font-bold text-slate-700">
                    立即启用该项目审查决策模版配置 (is_active)
                  </label>
                  <p className="text-[10px] text-slate-400">
                    启用后，系统检测到匹配该后缀拦截的 PR 自动交由该模型模版流转。
                  </p>
                </div>
                <button
                  type="button"
                  aria-label={form.isActive ? "停用新模板" : "启用新模板"}
                  onClick={() => updateField("isActive", !form.isActive)}
                  className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full p-0.5 transition-colors ${
                    form.isActive ? "bg-indigo-650" : "bg-slate-200"
                  }`}
                >
                  <div
                    className={`h-4 w-4 transform rounded-full bg-white shadow-3xs transition-transform ${
                      form.isActive ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              <div className="flex justify-end gap-2.5 border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-650 transition hover:bg-slate-50 hover:text-slate-800"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={saveMutation.isPending}
                  className="rounded-lg bg-[#0a0b14] px-4 py-2 text-xs font-bold text-white shadow-2xs transition hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {saveMutation.isPending ? "保存中..." : "确认保存"}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {successMessage ? (
        <div className="fixed bottom-4 right-4 z-50 w-[320px]">
          <ConsoleToast title="操作成功" message={successMessage} tone="success" />
        </div>
      ) : null}
      {errorMessage && !isModalOpen ? (
        <div className="fixed bottom-4 left-4 z-50 w-[320px]">
          <ConsoleToast title="操作失败" message={errorMessage} tone="danger" />
        </div>
      ) : null}
    </>
  );
}
