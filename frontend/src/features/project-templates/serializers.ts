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
  const fileExtensions = Array.isArray(template.file_extensions)
    ? template.file_extensions.filter(
        (extension): extension is string => typeof extension === "string"
      )
    : [];

  return {
    id: template.id,
    name: template.name,
    code: template.code,
    description: template.description ?? "",
    fileExtensions,
    fileExtensionsLabel: fileExtensions.join(", "),
    reviewPromptConfigured: template.review_prompt_configured,
    enabled: template.is_active,
  };
}
