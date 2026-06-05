import type { NotificationBotResponse } from "../../lib/api/types";

export interface ConsoleBot {
  id: number;
  name: string;
  type: string;
  webhookUrl: string;
  secretMasked: string | null;
  mentionStrategy: string | null;
  lastTestStatus: string | null;
  lastTestAt: string | null;
  enabled: boolean;
}

export function toConsoleBot(bot: NotificationBotResponse): ConsoleBot {
  return {
    id: bot.id,
    name: bot.name,
    type: bot.bot_type,
    webhookUrl: bot.webhook_url,
    secretMasked: bot.secret_masked,
    mentionStrategy: bot.mention_strategy,
    lastTestStatus: bot.last_test_status,
    lastTestAt: bot.last_test_at,
    enabled: bot.is_active,
  };
}
