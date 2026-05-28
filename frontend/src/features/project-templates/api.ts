import { http } from "../../lib/api/http";
import type {
  PageResponse,
  ProjectTemplateOptionsResponse,
  ProjectTemplateResponse,
} from "../../lib/api/types";

export interface ProjectTemplateCreatePayload {
  name: string;
  code: string;
  description: string | null;
  file_extensions: string[];
  review_prompt_template: string | null;
  prompt_metadata: Record<string, unknown>;
  is_active: boolean;
}

export interface ProjectTemplateUpdatePayload {
  name: string;
  code: string;
  description: string | null;
  file_extensions: string[];
  review_prompt_template: string | null;
  prompt_metadata: Record<string, unknown>;
}

/**
 * 查询项目模板分页列表。
 */
export async function listProjectTemplates(params: {
  page: number;
  page_size: number;
}) {
  const response = await http.get<PageResponse<ProjectTemplateResponse>>(
    "/project-templates",
    {
      params,
    }
  );
  return response.data;
}

/**
 * 查询项目模板管理页所需的静态选项。
 */
export async function getProjectTemplateOptions() {
  const response = await http.get<ProjectTemplateOptionsResponse>(
    "/project-templates/options"
  );
  return response.data;
}

/**
 * 创建项目模板。
 */
export async function createProjectTemplate(payload: ProjectTemplateCreatePayload) {
  const response = await http.post<ProjectTemplateResponse>(
    "/project-templates",
    payload
  );
  return response.data;
}

/**
 * 更新项目模板。
 */
export async function updateProjectTemplate(
  templateId: number,
  payload: ProjectTemplateUpdatePayload
) {
  const response = await http.put<ProjectTemplateResponse>(
    `/project-templates/${templateId}`,
    payload
  );
  return response.data;
}

/**
 * 更新项目模板启停状态。
 */
export async function updateProjectTemplateStatus(
  templateId: number,
  isActive: boolean
) {
  const response = await http.patch<ProjectTemplateResponse>(
    `/project-templates/${templateId}/status`,
    {
      is_active: isActive,
    }
  );
  return response.data;
}
