import type { ProjectResponse } from "../../lib/api/types";

export interface ConsoleProjectCard {
  id: number;
  name: string;
  key: string;
  platformType: string;
  enabled: boolean;
  reviewEnabled: boolean;
  language: string;
  description: string;
  owner: string;
  scoreAverage: number;
  lastReviewAt: string;
}

export function toConsoleProjectCard(project: ProjectResponse): ConsoleProjectCard {
  return {
    id: project.id,
    name: project.name,
    key: project.key,
    platformType: project.platform_type,
    enabled: project.is_active,
    reviewEnabled: project.review_enabled,
    language: project.settings.language ?? "TypeScript",
    description: project.description ?? "No description provided.",
    owner: project.settings.owner ?? "system",
    scoreAverage: project.settings.average_score ?? 0,
    lastReviewAt: project.settings.last_review_at ?? "",
  };
}
