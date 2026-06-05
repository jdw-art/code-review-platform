import type { ProjectTemplateResponse } from "../../lib/api/types";

export interface ConsoleProjectTemplate {
  id: number;
  name: string;
  code: string;
  description: string;
  fileExtensions: string[];
  fileExtensionsLabel: string;
  reviewPromptConfigured: boolean;
  enabled: boolean;
}

export function toConsoleProjectTemplate(
  template: ProjectTemplateResponse
): ConsoleProjectTemplate {
  return {
    id: template.id,
    name: template.name,
    code: template.code,
    description: template.description ?? "",
    fileExtensions: template.file_extensions,
    fileExtensionsLabel: template.file_extensions.join(", "),
    reviewPromptConfigured: template.review_prompt_configured,
    enabled: template.is_active,
  };
}
