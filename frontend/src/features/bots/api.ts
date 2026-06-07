import { http } from "../../lib/api/http";
import type { NotificationBotResponse, PageResponse } from "../../lib/api/types";

export interface NotificationBotPayload {
  name: string;
  bot_type: string;
  webhook_url: string;
  secret?: string;
  mention_strategy: string | null;
  template_config: Record<string, unknown>;
  is_active: boolean;
}

/**
 * 查询通知机器人列表。
 */
export async function listBots() {
  const response = await http.get<PageResponse<NotificationBotResponse>>(
    "/notification-bots",
    {
      params: { page: 1, page_size: 20 },
    }
  );
  return response.data;
}

/**
 * 创建通知机器人。
 */
export async function createBot(payload: NotificationBotPayload) {
  const response = await http.post<NotificationBotResponse>(
    "/notification-bots",
    payload
  );
  return response.data;
}

/**
 * 更新通知机器人。
 */
export async function updateBot(botId: number, payload: NotificationBotPayload) {
  const response = await http.put<NotificationBotResponse>(
    `/notification-bots/${botId}`,
    payload
  );
  return response.data;
}

/**
 * 更新通知机器人启停状态。
 */
export async function updateBotStatus(botId: number, isActive: boolean) {
  const response = await http.patch<NotificationBotResponse>(
    `/notification-bots/${botId}/status`,
    {
      is_active: isActive,
    }
  );
  return response.data;
}

/**
 * 触发通知机器人连通性测试。
 */
export async function testBot(botId: number) {
  const response = await http.post<NotificationBotResponse>(
    `/notification-bots/${botId}/test`
  );
  return response.data;
}
