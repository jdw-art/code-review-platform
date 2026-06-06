import type { ProjectResponse } from "../../lib/api/types";

export interface ConsoleProjectCard {
  id: number;
  name: string;
  key: string;
  platformType: string;
  repoUrl: string;
  defaultBranch: string;
  enabled: boolean;
  reviewEnabled: boolean;
  language: string;
  description: string;
  owner: string;
  scoreAverage: number | null;
  lastReviewAt: string | null;
  templateId: number | null;
  templateName: string;
  templateCode: string;
  templateReviewPromptConfigured: boolean;
  settings: Record<string, unknown>;
}

export function toConsoleProjectCard(project: ProjectResponse): ConsoleProjectCard {
  const settings = project.settings ?? {};
  const language = project.language ?? (
    typeof settings.language === "string" && settings.language.length > 0
      ? settings.language
      : "TypeScript"
  );
  const owner = project.owner ?? (
    typeof settings.owner === "string" && settings.owner.length > 0
      ? settings.owner
      : "system"
  );

  return {
    id: project.id,
    name: project.name,
    key: project.key,
    platformType: project.platform_type,
    repoUrl: project.repo_url ?? "",
    defaultBranch: project.default_branch,
    enabled: project.is_active,
    reviewEnabled: project.review_enabled,
    language,
    description: project.description ?? "No description provided.",
    owner,
    scoreAverage:
      typeof project.score_average === "number"
        ? project.score_average
        : typeof settings.average_score === "number"
          ? settings.average_score
          : null,
    lastReviewAt:
      typeof project.last_review_at === "string"
        ? project.last_review_at
        : typeof settings.last_review_at === "string"
          ? settings.last_review_at
          : null,
    templateId: project.template?.id ?? null,
    templateName: project.template?.name ?? "未绑定模板",
    templateCode: project.template?.code ?? "",
    templateReviewPromptConfigured: project.template?.review_prompt_configured ?? false,
    settings,
  };
}
