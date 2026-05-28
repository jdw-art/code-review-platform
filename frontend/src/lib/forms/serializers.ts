/**
 * 将空字符串折叠为 null，避免把纯空白文本提交给后端。
 */
export function normalizeOptionalText(value: string) {
  const trimmed = value.trim();
  return trimmed === "" ? null : trimmed;
}

/**
 * 将逗号分隔文本解析成字符串数组。
 */
export function parseCommaSeparatedList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item !== "");
}

/**
 * 将文本解析为对象，供 JSON 配置字段复用。
 */
export function parseJsonObject(value: string) {
  const trimmed = value.trim();
  if (trimmed === "") {
    return {};
  }

  const parsed = JSON.parse(trimmed);
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error("JSON 配置必须是对象。");
  }

  return parsed as Record<string, unknown>;
}

/**
 * 将对象格式化成更适合 textarea 编辑的 JSON 文本。
 */
export function toPrettyJson(value: Record<string, unknown>) {
  return JSON.stringify(value, null, 2);
}
