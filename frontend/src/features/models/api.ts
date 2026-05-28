import { http } from "../../lib/api/http";
import type { LlmModelResponse, PageResponse } from "../../lib/api/types";

export interface LlmModelPayload {
  name: string;
  provider: string;
  model_code: string;
  base_url: string | null;
  api_key?: string;
  temperature: number | null;
  max_tokens: number | null;
  top_p: number | null;
  prompt_template: string | null;
  is_default: boolean;
  is_active: boolean;
}

/**
 * 查询大模型配置列表。
 */
export async function listModels() {
  const response = await http.get<PageResponse<LlmModelResponse>>("/models", {
    params: { page: 1, page_size: 20 },
  });
  return response.data;
}

/**
 * 创建模型配置。
 */
export async function createModel(payload: LlmModelPayload) {
  const response = await http.post<LlmModelResponse>("/models", payload);
  return response.data;
}

/**
 * 更新模型配置。
 */
export async function updateModel(modelId: number, payload: LlmModelPayload) {
  const response = await http.put<LlmModelResponse>(`/models/${modelId}`, payload);
  return response.data;
}

/**
 * 更新模型启停状态。
 */
export async function updateModelStatus(modelId: number, isActive: boolean) {
  const response = await http.patch<LlmModelResponse>(`/models/${modelId}/status`, {
    is_active: isActive,
  });
  return response.data;
}
