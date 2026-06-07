import { http } from "../../lib/api/http";
import type {
  PageResponse,
  ProjectManualReviewResponse,
  ProjectOptionsResponse,
  ProjectResponse,
} from "../../lib/api/types";

export interface ProjectPayload {
  name: string;
  key: string;
  platform_type: string;
  repo_url: string | null;
  default_branch: string;
  description: string | null;
  template_id: number | null;
  review_enabled: boolean;
  settings: Record<string, unknown>;
}

/**
 * 查询项目分页列表。
 */
export async function listProjects(params: {
  page: number;
  page_size: number;
  search?: string;
  language?: string;
}) {
  const response = await http.get<PageResponse<ProjectResponse>>("/projects", {
    params,
  });
  return response.data;
}

/**
 * 查询项目管理页面初始化选项。
 */
export async function getProjectOptions() {
  const response = await http.get<ProjectOptionsResponse>("/projects/options");
  return response.data;
}

/**
 * 创建项目。
 */
export async function createProject(payload: ProjectPayload) {
  const response = await http.post<ProjectResponse>("/projects", payload);
  return response.data;
}

/**
 * 更新项目。
 */
export async function updateProject(projectId: number, payload: ProjectPayload) {
  const response = await http.put<ProjectResponse>(`/projects/${projectId}`, payload);
  return response.data;
}

/**
 * 更新项目启停状态。
 */
export async function updateProjectStatus(projectId: number, isActive: boolean) {
  const response = await http.patch<ProjectResponse>(`/projects/${projectId}/status`, {
    is_active: isActive,
  });
  return response.data;
}

/**
 * 删除项目。
 */
export async function deleteProject(projectId: number) {
  await http.delete(`/projects/${projectId}`);
}

/**
 * 手动触发项目审查。
 */
export async function triggerProjectManualReview(projectId: number) {
  const response = await http.post<ProjectManualReviewResponse>(
    `/projects/${projectId}/manual-review`
  );
  return response.data;
}
