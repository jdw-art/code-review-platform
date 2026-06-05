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
  const settings = project.settings ?? {};

  return {
    id: project.id,
    name: project.name,
    key: project.key,
    platformType: project.platform_type,
    enabled: project.is_active,
    reviewEnabled: project.review_enabled,
    language: typeof settings.language === "string" && settings.language.length > 0
      ? settings.language
      : "TypeScript",
    description: project.description ?? "No description provided.",
    owner: typeof settings.owner === "string" && settings.owner.length > 0
      ? settings.owner
      : "system",
    scoreAverage:
      typeof settings.average_score === "number" ? settings.average_score : 0,
    lastReviewAt:
      typeof settings.last_review_at === "string" ? settings.last_review_at : "",
  };
}
