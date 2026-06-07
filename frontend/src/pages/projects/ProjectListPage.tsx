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
    <div className="p-6 space-y-4 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white py-3.5 px-5 rounded-xl border border-slate-200/80 shadow-3xs gap-3">
        <div>
          <h2 className="text-sm font-bold text-slate-800 flex items-center gap-1.5">
            <FileCode className="w-4 h-4 text-indigo-500 shrink-0" />
            <span>仓库代码项目管理</span>
          </h2>
          <p className="text-[11px] text-slate-500 mt-0.5">
            在此配置并开启自动 PR/MR 监听审查。核心字段已对齐 PostgreSQL{" "}
            <code className="bg-slate-100 text-[10px] px-1 rounded text-indigo-650 font-mono">
              projects
            </code>{" "}
            表结构。
          </p>
        </div>
        <button
          type="button"
          onClick={openCreateModal}
          className="px-3.5 py-1.5 bg-[#0a0b14] hover:bg-slate-900 text-white text-[11px] font-bold rounded-lg transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>添加审查仓库</span>
        </button>
      </div>

      {showProjectForm ? (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="absolute inset-0" onClick={closeProjectModal} aria-hidden="true" />
          <div className="relative bg-white rounded-3xl w-full max-w-3xl border border-slate-250 shadow-2xl p-6 md:p-8 space-y-6 max-h-[90vh] overflow-y-auto z-10">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <h4 className="text-base font-bold text-slate-900 flex items-center gap-2 font-sans">
                {editingProject === null ? (
                  <Plus className="w-5 h-5 text-indigo-500" />
                ) : (
                  <Pencil className="w-5 h-5 text-indigo-500" />
                )}
                <span>{editingProject === null ? "添加新监控审查代码库" : "编辑项目配置"}</span>
              </h4>
              <button
                type="button"
                onClick={closeProjectModal}
                className="text-slate-400 hover:text-slate-600 font-bold p-1 cursor-pointer text-base rounded-full hover:bg-slate-100 w-8 h-8 flex items-center justify-center transition-colors border-none"
                aria-label="关闭项目弹窗"
              >
                ✕
              </button>
            </div>

            <form className="space-y-6" onSubmit={handleSubmit}>
              {errorMessage ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errorMessage}
                </div>
              ) : null}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-name" className="text-[11px] font-bold text-slate-700 block">项目名称 (name)</label>
                  <input
                    id="project-name"
                    value={form.name}
                    onChange={(event) => updateField("name", event.target.value)}
                    placeholder="例如: access-context-rbac"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-key" className="text-[11px] font-bold text-slate-700 block">唯一项目标识代码 (key - 唯一约束)</label>
                  <input
                    id="project-key"
                    value={form.key}
                    onChange={(event) => updateField("key", event.target.value)}
                    placeholder="例如: ACR (须保持大写英文唯一标识)"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono font-bold outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-platform-type" className="text-[11px] font-bold text-slate-700 block">托管平台类型 (platform_type)</label>
                  <select
                    id="project-platform-type"
                    value={form.platform_type}
                    onChange={(event) => updateField("platform_type", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                  >
                    {(options?.platform_types ?? []).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-default-branch" className="text-[11px] font-bold text-slate-700 block">默认分析分支 (default_branch)</label>
                  <input
                    id="project-default-branch"
                    value={form.default_branch}
                    onChange={(event) => updateField("default_branch", event.target.value)}
                    placeholder="例如: main"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 md:col-span-2 text-left">
                  <label htmlFor="project-repo-url" className="text-[11px] font-bold text-slate-700 block">Git 仓库 URL (repo_url)</label>
                  <input
                    id="project-repo-url"
                    value={form.repo_url}
                    onChange={(event) => updateField("repo_url", event.target.value)}
                    placeholder="例如: https://github.com/jdw-art/access-context-rbac.git"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-language" className="text-[11px] font-bold text-slate-700 block">偏好展示主要语言</label>
                  <select
                    id="project-language"
                    value={form.language}
                    onChange={(event) => updateField("language", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                  >
                    {languageOptions.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-review-enabled" className="text-[11px] font-bold text-slate-700 block">是否启用审查拦截 (review_enabled)</label>
                  <select
                    id="project-review-enabled"
                    value={form.review_enabled ? "true" : "false"}
                    onChange={(event) =>
                      updateField("review_enabled", event.target.value === "true")
                    }
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-semibold outline-hidden"
                  >
                    <option value="true">是 (主动挂载 LLM 机器人)</option>
                    <option value="false">否 (只同步分析不触发审查)</option>
                  </select>
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-owner" className="text-[11px] font-bold text-slate-700 block">归属负责人 (owner)</label>
                  <input
                    id="project-owner"
                    value={form.owner}
                    onChange={(event) => updateField("owner", event.target.value)}
                    placeholder="例如: jdw-art"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-template-id" className="text-[11px] font-bold text-slate-700 block">绑定项目模板 (template_id)</label>
                  <select
                    id="project-template-id"
                    value={form.template_id}
                    onChange={(event) => updateField("template_id", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                  >
                    <option value="">无模板</option>
                    {(options?.template_options ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-external-project-id" className="text-[11px] font-bold text-slate-700 block">外部项目 ID (external_project_id)</label>
                  <input
                    id="project-external-project-id"
                    value={form.external_project_id}
                    onChange={(event) => updateField("external_project_id", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left">
                  <label htmlFor="project-gitlab-project-path" className="text-[11px] font-bold text-slate-700 block">GitLab 项目路径 (gitlab_project_path)</label>
                  <input
                    id="project-gitlab-project-path"
                    value={form.gitlab_project_path}
                    onChange={(event) => updateField("gitlab_project_path", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 text-left md:col-span-2">
                  <label htmlFor="project-external-repo-full-name" className="text-[11px] font-bold text-slate-700 block">GitHub 仓库全名 (external_repo_full_name)</label>
                  <input
                    id="project-external-repo-full-name"
                    value={form.external_repo_full_name}
                    onChange={(event) => updateField("external_repo_full_name", event.target.value)}
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 font-mono outline-hidden"
                  />
                </div>

                <div className="space-y-1.5 md:col-span-2 text-left">
                  <label htmlFor="project-description" className="text-[11px] font-bold text-slate-700 block">项目说明 (description)</label>
                  <input
                    id="project-description"
                    value={form.description}
                    onChange={(event) => updateField("description", event.target.value)}
                    placeholder="例如: 用于验证 RBAC 初始化树的独立编译模块"
                    className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:ring-2 focus:ring-indigo-500/10 focus:border-indigo-500 text-slate-800 outline-hidden"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={closeProjectModal}
                  className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-600 rounded-xl text-xs font-semibold select-none transition cursor-pointer"
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-2xs select-none transition cursor-pointer"
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

      <div className="flex flex-col md:flex-row gap-4 items-center justify-between bg-white px-6 py-4 rounded-xl border border-slate-200/85">
        <div className="relative w-full md:max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="搜索项目名称、唯一标识 key 或是 仓库链接..."
            className="w-full pl-10 pr-4 py-2 bg-slate-50 text-slate-800 border border-slate-200 rounded-xl focus:outline-hidden focus:ring-2 focus:ring-indigo-500/10 text-xs"
          />
        </div>

        <div className="flex gap-2 items-center w-full md:w-auto overflow-x-auto select-none">
          {availableLanguages.map((lang) => (
            <button
              key={lang}
              type="button"
              onClick={() => setSelectedLang(lang)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-all shrink-0 ${
                selectedLang === lang
                  ? "bg-indigo-500/10 text-indigo-600 font-bold border border-indigo-200"
                  : "bg-slate-50 text-slate-500 hover:text-slate-800 border border-slate-200/60"
              }`}
            >
              {lang === "All" ? "全部语言" : lang}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-xs shadow-3xs">
          正在加载项目数据...
        </div>
      ) : cards.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-slate-400 text-xs shadow-3xs">
          暂无匹配的项目库数据
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards.map((card, index) => {
              const project = projects[index];
              return (
                <article
                  key={card.id}
                  onClick={() => openEditModal(project)}
                  className={`bg-white rounded-2xl border transition-all flex flex-col justify-between overflow-hidden shadow-xs hover:shadow-md cursor-pointer ${
                    card.enabled ? "border-slate-200/80" : "border-slate-200/50 opacity-80"
                  }`}
                >
                  <div className="p-6 space-y-4">
                    <div className="flex justify-between items-start gap-4">
                      <div className="space-y-1 grow min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] bg-slate-100 font-bold border border-slate-200 rounded text-slate-500 px-1 font-mono">
                            {platformLabel(card.platformType)}
                          </span>
                          <span className="text-[10px] bg-indigo-50 font-bold text-indigo-600 px-1.5 py-0.2 rounded font-mono">
                            KEY: {card.key}
                          </span>
                        </div>
                        <h3 className="text-sm font-bold text-slate-900 truncate flex items-center gap-1.5 mt-1.5">
                          <FileCode className="w-4 h-4 text-indigo-500 shrink-0" />
                          <span>{card.name}</span>
                        </h3>
                      </div>

                      <div className="flex flex-col items-end gap-1.5 shrink-0">
                        <button
                          type="button"
                          aria-label={`切换 ${card.name} 启用状态`}
                          onClick={(event) => {
                            event.stopPropagation();
                            void statusMutation.mutateAsync(card);
                          }}
                          className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-hidden ${
                            card.enabled ? "bg-emerald-500" : "bg-slate-300"
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                              card.enabled ? "translate-x-5" : "translate-x-0"
                            }`}
                          />
                        </button>
                        <span className="text-[8.5px] font-mono text-slate-450 uppercase font-semibold">
                          {card.enabled ? "is_active: t" : "is_active: f"}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-500 leading-relaxed font-light min-h-[40px]">
                      {card.description}
                    </p>

                    <div className="space-y-2 pt-2 border-t border-slate-100/80">
                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400 flex items-center gap-1">
                          主要语言 <code className="text-[9px] text-slate-400 font-mono">(language)</code>
                        </span>
                        <span className="font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded-sm text-[10px]">
                          {card.language}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400 flex items-center gap-1">
                          主审核状态 <code className="text-[9px] text-slate-400 font-mono">(review_enabled)</code>
                        </span>
                        <span className={`font-semibold text-[10px] ${card.reviewEnabled ? "text-emerald-600" : "text-slate-400"}`}>
                          {card.reviewEnabled ? "开启审查中" : "已禁用审查"}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400">绑定模板</span>
                        <span className="max-w-[160px] truncate text-[10px] font-semibold text-slate-600">
                          {templateSummary(card)}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400">平均评分指标</span>
                        <span className="font-bold text-indigo-600 font-mono text-[11px]">
                          {card.scoreAverage !== null ? `${card.scoreAverage}分` : "暂无数据"}
                        </span>
                      </div>

                      <div className="flex justify-between text-xs items-center">
                        <span className="text-slate-400">最近审查时间</span>
                        <span className="text-slate-650 font-mono text-[10px]">
                          {formatReviewDate(card.lastReviewAt)}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="px-6 py-4 bg-slate-50 border-t border-slate-100/80 flex justify-between items-center">
                    <span className="text-[10px] text-slate-400 font-mono bg-slate-200 px-1.5 py-0.5 rounded-xs truncate max-w-[120px]">
                      ID: {card.id} / 归属: {card.owner}
                    </span>

                    <div className="flex gap-2">
                      <span className="sr-only">手动审查</span>

                      <button
                        type="button"
                        aria-label={`编辑 ${card.name}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          openEditModal(project);
                        }}
                        className="sr-only"
                      >
                        编辑
                      </button>

                      <Link
                        to={`/projects/${card.id}/agent`}
                        aria-label={`立即监测 ${card.name}`}
                        onClick={(event) => event.stopPropagation()}
                        className="sr-only"
                      />

                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void manualReviewMutation.mutateAsync(card);
                        }}
                        aria-label={`手动审查 ${card.name}`}
                        className="sr-only"
                      />

                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          void manualReviewMutation.mutateAsync(card);
                        }}
                        disabled={!card.enabled}
                        title="立即触发 AI 代码全量审查"
                        className="p-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-lg text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                      >
                        <Play className="w-3.5 h-3.5" />
                        <span>立即监测</span>
                      </button>

                      <button
                        type="button"
                        aria-label={`删除 ${card.name}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          void handleDelete(card);
                        }}
                        title="移除此审查配置"
                        className="p-1.5 hover:bg-red-50 text-slate-400 hover:text-red-600 rounded-lg cursor-pointer transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-between border border-slate-200 bg-white px-6 py-4 rounded-2xl text-xs gap-4 select-none shadow-3xs">
            <div className="flex flex-col sm:flex-row items-center gap-3 text-slate-500 font-sans">
              <div>
                显示 <span className="font-semibold text-slate-800">{startIndex}</span> 至{" "}
                <span className="font-semibold text-slate-800">{endIndex}</span> 个，
                共 <span className="font-semibold text-slate-800">{totalItems}</span> 个项目库
              </div>
              <div className="flex items-center gap-1.5 ml-0 sm:ml-4">
                <span>每页显示:</span>
                <select
                  value={pageSize}
                  onChange={(event) => setPageSize(Number(event.target.value))}
                  className="border border-slate-200 bg-slate-50 text-slate-800 rounded-md px-2 py-1 font-semibold text-xs cursor-pointer focus:outline-hidden focus:ring-1 focus:ring-indigo-500/30"
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
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>上一页</span>
              </button>
              <div className="flex items-center gap-1 font-mono text-slate-600 px-3">
                <span className="font-bold text-indigo-605">{currentPage}</span>
                <span className="text-slate-300">/</span>
                <span>{totalPages}</span>
              </div>
              <button
                type="button"
                onClick={() => setCurrentPage((page) => Math.min(page + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-1 px-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-650 rounded-lg cursor-pointer transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 font-bold active:scale-[0.98]"
              >
                <span>下一页</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
