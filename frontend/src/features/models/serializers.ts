import type { LlmModelResponse } from "../../lib/api/types";

export interface ConsoleModel extends LlmModelResponse {
  isActive: boolean;
  queriesCount: number;
}

export function toConsoleModel(model: LlmModelResponse): ConsoleModel {
  return {
    ...model,
    isActive: model.is_active,
    queriesCount: model.queries_count ?? 0,
  };
}
