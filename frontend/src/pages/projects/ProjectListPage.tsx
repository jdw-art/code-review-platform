import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ChevronLeft,
  ChevronRight,
  FileCode,
  Pencil,
  Play,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import {
  createProject,
  deleteProject,
  getProjectOptions,
  listProjects,
  triggerProjectManualReview,
  updateProject,
  updateProjectStatus,
  type ProjectPayload,
} from "../../features/projects/api";
import {
  type ConsoleProjectCard,
  toConsoleProjectCard,
} from "../../features/projects/serializers";
import type { ProjectResponse } from "../../lib/api/types";
import { normalizeOptionalText } from "../../lib/forms/serializers";

interface ProjectFormState {
  name: string;
  key: string;
  platform_type: string;
  repo_url: string;
  default_branch: string;
  language: string;
  owner: string;
  description: string;
  review_enabled: boolean;
  template_id: string;
  external_project_id: string;
  gitlab_project_path: string;
  external_repo_full_name: string;
}

const languageOptions = [
  "TypeScript",
  "React",
  "Go",
  "Python",
  "Java",
  "Rust",
  "SQL",
];

const emptyProjectForm: ProjectFormState = {
  name: "",
  key: "",
  platform_type: "gitlab",
  repo_url: "",
  default_branch: "main",
  language: "TypeScript",
  owner: "",
  description: "",
  review_enabled: true,
  template_id: "",
  external_project_id: "",
  gitlab_project_path: "",
  external_repo_full_name: "",
};

function buildProjectForm(project: ProjectResponse): ProjectFormState {
  const settings = project.settings ?? {};

  return {
    name: project.name,
    key: project.key,
    platform_type: project.platform_type,
    repo_url: project.repo_url ?? "",
    default_branch: project.default_branch,
    language:
      project.language ??
      (typeof settings.language === "string" && settings.language.length > 0
        ? settings.language
        : "TypeScript"),
    owner:
      project.owner ??
      (typeof settings.owner === "string" && settings.owner.length > 0
        ? settings.owner
        : ""),
    description: project.description ?? "",
    review_enabled: project.review_enabled,
    template_id: project.template?.id === undefined ? "" : String(project.template.id),
    external_project_id:
      typeof settings.external_project_id === "string"
        ? settings.external_project_id
        : "",
    gitlab_project_path:
      typeof settings.gitlab_project_path === "string"
        ? settings.gitlab_project_path
        : "",
    external_repo_full_name:
      typeof settings.external_repo_full_name === "string"
        ? settings.external_repo_full_name
        : "",
  };
}

function buildProjectPayload(form: ProjectFormState): ProjectPayload {
  const settings: Record<string, unknown> = {
    language: form.language,
  };

  const owner = normalizeOptionalText(form.owner);
  if (owner !== null) {
    settings.owner = owner;
  }

  const externalProjectId = normalizeOptionalText(form.external_project_id);
  if (externalProjectId !== null) {
    settings.external_project_id = externalProjectId;
  }

  const gitlabProjectPath = normalizeOptionalText(form.gitlab_project_path);
  if (gitlabProjectPath !== null) {
    settings.gitlab_project_path = gitlabProjectPath;
  }

  const externalRepoFullName = normalizeOptionalText(form.external_repo_full_name);
  if (externalRepoFullName !== null) {
    settings.external_repo_full_name = externalRepoFullName;
  }

  return {
    name: form.name.trim(),
    key: form.key.trim(),
    platform_type: form.platform_type.trim(),
    repo_url: normalizeOptionalText(form.repo_url),
    default_branch: form.default_branch.trim(),
    description: normalizeOptionalText(form.description),
    template_id:
      form.template_id.trim() === "" ? null : Number.parseInt(form.template_id, 10),
    review_enabled: form.review_enabled,
    settings,
  };
}

function formatReviewDate(value: string | null) {
  if (!value) {
    return "从未审查";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function platformLabel(value: string) {
  const normalized = value.toLowerCase();
  if (normalized === "github") {
    return "GitHub";
  }
  if (normalized === "gitlab") {
    return "GitLab";
  }
  if (normalized === "gitea") {
    return "Gitea";
  }
  if (normalized === "bitbucket") {
    return "Bitbucket";
  }
  return value;
}

function templateSummary(card: ConsoleProjectCard) {
  if (card.templateId === null) {
    return "未绑定模板";
  }
  return card.templateCode
    ? `${card.templateName} (${card.templateCode})`
    : card.templateName;
}

/**
 * 项目管理页按原型重建为卡片管理台，同时恢复真实分页、编辑和模板绑定能力。
 */
export function ProjectListPage() {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearchQuery = useDeferredValue(searchQuery);
  const [selectedLang, setSelectedLang] = useState("All");
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [pageSize, setPageSize] = useState(6);
  const [currentPage, setCurrentPage] = useState(1);
  const [editingProject, setEditingProject] = useState<ProjectResponse | null>(null);
  const [form, setForm] = useState<ProjectFormState>(emptyProjectForm);
  const [bannerMessage, setBannerMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const listQueryParams = useMemo(
    () => ({
      page: currentPage,
      page_size: pageSize,
      ...(deferredSearchQuery.trim() === ""
        ? {}
        : { search: deferredSearchQuery.trim() }),
      ...(selectedLang === "All" ? {} : { language: selectedLang }),
    }),
    [currentPage, deferredSearchQuery, pageSize, selectedLang]
  );

  const { data, isLoading } = useQuery({
    queryKey: ["projects", "list", listQueryParams],
    queryFn: () => listProjects(listQueryParams),
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
      const successMessage = editingProject === null ? "项目已创建" : "项目已更新";
      setShowProjectForm(false);
      setEditingProject(null);
      setForm(emptyProjectForm);
      setErrorMessage(null);
      setBannerMessage(successMessage);
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存项目失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (card: ConsoleProjectCard) =>
      updateProjectStatus(card.id, !card.enabled),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (card: ConsoleProjectCard) => deleteProject(card.id),
    onSuccess: async () => {
      setBannerMessage("项目已删除");
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
  });

  const manualReviewMutation = useMutation({
    mutationFn: async (card: ConsoleProjectCard) => triggerProjectManualReview(card.id),
    onSuccess: async () => {
      setBannerMessage("手动审查任务已入队");
      await queryClient.invalidateQueries({ queryKey: ["projects", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["review-records", "list"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard", "overview"] });
    },
  });

  useEffect(() => {
    setCurrentPage(1);
  }, [deferredSearchQuery, pageSize, selectedLang]);

  useEffect(() => {
    if (!showProjectForm || editingProject !== null) {
      return;
    }
    setForm((current) => ({
      ...current,
      platform_type: options?.platform_types[0]?.value ?? current.platform_type,
    }));
  }, [editingProject, options, showProjectForm]);

  const projects = data?.items ?? [];
  const cards = useMemo(
    () => projects.map((project) => toConsoleProjectCard(project)),
    [projects]
  );

  const availableLanguages = useMemo(() => {
    const values = new Set<string>(["All", ...languageOptions]);
    cards.forEach((card) => values.add(card.language || "TypeScript"));
    return Array.from(values);
  }, [cards]);

  const totalItems = data?.total ?? 0;
  const totalPages = Math.max(1, data?.total_pages ?? 1);
  const startIndex = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const endIndex = totalItems === 0 ? 0 : startIndex + cards.length - 1;

  function updateField<KeyT extends keyof ProjectFormState>(
    field: KeyT,
    value: ProjectFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function openCreateModal() {
    setEditingProject(null);
    setBannerMessage(null);
    setErrorMessage(null);
    setForm({
      ...emptyProjectForm,
      platform_type: options?.platform_types[0]?.value ?? emptyProjectForm.platform_type,
    });
    setShowProjectForm(true);
  }

  function openEditModal(project: ProjectResponse) {
    setEditingProject(project);
    setBannerMessage(null);
    setErrorMessage(null);
    setForm(buildProjectForm(project));
    setShowProjectForm(true);
  }

  function closeProjectModal() {
    setShowProjectForm(false);
    setEditingProject(null);
    setErrorMessage(null);
    setForm(emptyProjectForm);
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    try {
      await saveMutation.mutateAsync();
    } catch (error) {
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存项目失败。");
      }
    }
  }

  async function handleDelete(card: ConsoleProjectCard) {
    if (!window.confirm(`确认删除项目 ${card.name} 吗？`)) {
      return;
    }
    await deleteMutation.mutateAsync(card);
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 p-6">
      <div className="rounded-3xl border border-slate-200 bg-white/95 px-5 py-4 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-sm font-bold text-slate-900">
              <FileCode className="h-4 w-4 text-indigo-500" />
              <span>仓库代码项目管理</span>
            </h1>
            <p className="mt-1 text-[11px] leading-5 text-slate-500">
              在此配置并开启自动 PR/MR 监听审查。核心字段已对齐 PostgreSQL{" "}
              <code className="rounded bg-slate-100 px-1 py-0.5 font-mono text-[10px] text-indigo-700">
                projects
              </code>{" "}
              表结构。
            </p>
          </div>
          <button
            type="button"
            onClick={openCreateModal}
            className="inline-flex items-center gap-1.5 rounded-xl bg-[#0a0b14] px-3.5 py-2 text-[11px] font-bold text-white transition hover:bg-slate-900"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>添加审查仓库</span>
          </button>
        </div>
      </div>

      {showProjectForm ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
          <div className="absolute inset-0" onClick={closeProjectModal} aria-hidden="true" />
          <div className="relative z-10 max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-[2rem] border border-slate-200 bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
                {editingProject === null ? (
                  <Plus className="h-5 w-5 text-indigo-500" />
                ) : (
                  <Pencil className="h-5 w-5 text-indigo-500" />
                )}
                <span>
                  {editingProject === null ? "添加新监控审查代码库" : "编辑项目配置"}
                </span>
              </h2>
              <button
                type="button"
                onClick={closeProjectModal}
                className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                aria-label="关闭项目弹窗"
              >
                ✕
              </button>
            </div>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
              {errorMessage ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errorMessage}
                </div>
              ) : null}

              <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>项目名称 (name)</span>
                  <input
                    value={form.name}
                    onChange={(event) => updateField("name", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>唯一项目标识代码 (key - 唯一约束)</span>
                  <input
                    value={form.key}
                    onChange={(event) => updateField("key", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs font-bold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>托管平台类型 (platform_type)</span>
                  <select
                    value={form.platform_type}
                    onChange={(event) => updateField("platform_type", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  >
                    {(options?.platform_types ?? []).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>默认分析分支 (default_branch)</span>
                  <input
                    value={form.default_branch}
                    onChange={(event) => updateField("default_branch", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700 md:col-span-2">
                  <span>Git 仓库 URL (repo_url)</span>
                  <input
                    value={form.repo_url}
                    onChange={(event) => updateField("repo_url", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>偏好展示主要语言</span>
                  <select
                    value={form.language}
                    onChange={(event) => updateField("language", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  >
                    {languageOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>归属负责人 (owner)</span>
                  <input
                    value={form.owner}
                    onChange={(event) => updateField("owner", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>是否启用审查拦截 (review_enabled)</span>
                  <select
                    value={form.review_enabled ? "true" : "false"}
                    onChange={(event) =>
                      updateField("review_enabled", event.target.value === "true")
                    }
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  >
                    <option value="true">是 (主动挂载 LLM 机器人)</option>
                    <option value="false">否 (只同步分析不触发审查)</option>
                  </select>
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>绑定项目模板 (template_id)</span>
                  <select
                    value={form.template_id}
                    onChange={(event) => updateField("template_id", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  >
                    <option value="">无模板</option>
                    {(options?.template_options ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>外部项目 ID (external_project_id)</span>
                  <input
                    value={form.external_project_id}
                    onChange={(event) =>
                      updateField("external_project_id", event.target.value)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>GitLab 项目路径 (gitlab_project_path)</span>
                  <input
                    value={form.gitlab_project_path}
                    onChange={(event) =>
                      updateField("gitlab_project_path", event.target.value)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700">
                  <span>GitHub 仓库全名 (external_repo_full_name)</span>
                  <input
                    value={form.external_repo_full_name}
                    onChange={(event) =>
                      updateField("external_repo_full_name", event.target.value)
                    }
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>

                <label className="space-y-1.5 text-[11px] font-bold text-slate-700 md:col-span-2">
                  <span>项目说明 (description)</span>
                  <input
                    value={form.description}
                    onChange={(event) => updateField("description", event.target.value)}
                    className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
                  />
                </label>
              </div>

              <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  type="button"
                  onClick={closeProjectModal}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-indigo-700"
                >
                  确认保存
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {bannerMessage ? (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {bannerMessage}
        </div>
      ) : null}

      <div className="flex flex-col items-center justify-between gap-4 rounded-3xl border border-slate-200 bg-white px-6 py-4 md:flex-row">
        <div className="relative w-full md:max-w-md">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="搜索项目名称、唯一标识 key 或是 仓库链接..."
            className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-10 pr-4 text-xs text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="flex w-full gap-2 overflow-x-auto md:w-auto">
          {availableLanguages.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setSelectedLang(lang)}
              className={`shrink-0 rounded-full border px-3.5 py-1.5 text-xs transition ${
                selectedLang === lang
                  ? "border-indigo-200 bg-indigo-50 font-bold text-indigo-600"
                  : "border-slate-200 bg-slate-50 text-slate-500 hover:text-slate-800"
              }`}
            >
              {lang === "All" ? "全部语言" : lang}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-12 text-center text-xs text-slate-400">
          正在加载项目数据...
        </div>
      ) : cards.length === 0 ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-12 text-center text-xs text-slate-400">
          暂无匹配的项目库数据
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {cards.map((card, index) => {
              const project = projects[index];

              return (
                <article
                  key={card.id}
                  className={`flex flex-col justify-between overflow-hidden rounded-[1.7rem] border bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
                    card.enabled ? "border-slate-200" : "border-slate-200/70 opacity-80"
                  }`}
                >
                  <div className="space-y-4 p-6">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] font-bold text-slate-500">
                            {platformLabel(card.platformType)}
                          </span>
                          <span className="rounded bg-indigo-50 px-1.5 py-0.5 font-mono text-[10px] font-bold text-indigo-600">
                            KEY: {card.key}
                          </span>
                        </div>
                        <h2 className="mt-1.5 flex items-center gap-1.5 truncate text-sm font-bold text-slate-900">
                          <FileCode className="h-4 w-4 shrink-0 text-indigo-500" />
                          <span className="truncate">{card.name}</span>
                        </h2>
                      </div>

                      <div className="flex shrink-0 flex-col items-end gap-1.5">
                        <button
                          type="button"
                          role="button"
                          aria-label={`切换 ${card.name} 启用状态`}
                          onClick={() => void statusMutation.mutateAsync(card)}
                          className={`relative inline-flex h-5 w-10 rounded-full transition ${
                            card.enabled ? "bg-emerald-500" : "bg-slate-300"
                          }`}
                        >
                          <span
                            className={`inline-block h-4 w-4 translate-y-0.5 rounded-full bg-white shadow transition ${
                              card.enabled ? "translate-x-5" : "translate-x-0.5"
                            }`}
                          />
                        </button>
                        <span className="font-mono text-[8.5px] font-semibold uppercase text-slate-400">
                          {card.enabled ? "is_active: t" : "is_active: f"}
                        </span>
                      </div>
                    </div>

                    <p className="min-h-[40px] text-xs leading-relaxed text-slate-500">
                      {card.description}
                    </p>

                    <div className="space-y-2 border-t border-slate-100 pt-2">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          主要语言 <code className="font-mono text-[9px]">(language)</code>
                        </span>
                        <span className="rounded-sm bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-700">
                          {card.language}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">
                          主审核状态{" "}
                          <code className="font-mono text-[9px]">(review_enabled)</code>
                        </span>
                        <span
                          className={`text-[10px] font-semibold ${
                            card.reviewEnabled ? "text-emerald-600" : "text-slate-400"
                          }`}
                        >
                          {card.reviewEnabled ? "开启审查中" : "已禁用审查"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">绑定模板</span>
                        <span className="max-w-[160px] truncate text-[10px] font-semibold text-slate-600">
                          {templateSummary(card)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">平均评分指标</span>
                        <span className="font-mono text-[11px] font-bold text-indigo-600">
                          {card.scoreAverage !== null ? `${card.scoreAverage}分` : "暂无数据"}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-slate-400">最近审查时间</span>
                        <span className="font-mono text-[10px] text-slate-600">
                          {formatReviewDate(card.lastReviewAt)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-6 py-4">
                    <span className="max-w-[150px] truncate rounded bg-slate-200 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                      ID: {card.id} / 归属: {card.owner}
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        aria-label={`编辑 ${card.name}`}
                        onClick={() => openEditModal(project)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        <span>编辑</span>
                      </button>
                      <Link
                        to={`/projects/${card.id}/agent`}
                        aria-label={`立即监测 ${card.name}`}
                        className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition ${
                          card.enabled
                            ? "bg-indigo-50 text-indigo-600 hover:bg-indigo-100"
                            : "pointer-events-none bg-slate-100 text-slate-400"
                        }`}
                      >
                        <Play className="h-3.5 w-3.5" />
                        <span>立即监测</span>
                      </Link>
                      <button
                        type="button"
                        aria-label={`手动审查 ${card.name}`}
                        onClick={() => void manualReviewMutation.mutateAsync(card)}
                        disabled={!card.enabled}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        <span>手动审查</span>
                      </button>
                      <button
                        type="button"
                        aria-label={`删除 ${card.name}`}
                        onClick={() => void handleDelete(card)}
                        className="rounded-lg p-1.5 text-slate-400 transition hover:bg-red-50 hover:text-red-600"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="flex flex-col items-center justify-between gap-4 rounded-[1.7rem] border border-slate-200 bg-white px-6 py-4 text-xs shadow-sm sm:flex-row">
            <div className="flex flex-col items-center gap-3 text-slate-500 sm:flex-row">
              <div>
                显示 <span className="font-semibold text-slate-800">{startIndex}</span> 至{" "}
                <span className="font-semibold text-slate-800">{endIndex}</span> 个，共{" "}
                <span className="font-semibold text-slate-800">{totalItems}</span>{" "}
                个项目库
              </div>
              <div className="flex items-center gap-1.5">
                <span>每页显示:</span>
                <select
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                  className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-800 outline-none"
                >
                  <option value={3}>3 条</option>
                  <option value={6}>6 条</option>
                  <option value={12}>12 条</option>
                  <option value={24}>24 条</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.max(page - 1, 1))}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>上一页</span>
              </button>
              <div className="px-3 font-mono text-slate-600">
                <span className="font-bold text-indigo-600">{currentPage}</span>
                <span className="px-1 text-slate-300">/</span>
                <span>{totalPages}</span>
              </div>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(page + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <span>下一页</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
