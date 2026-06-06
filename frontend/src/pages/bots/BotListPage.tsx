import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { ConsolePageHeader } from "../../components/console/ConsolePageHeader";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  createBot,
  listBots,
  testBot,
  updateBot,
  updateBotStatus,
  type NotificationBotPayload,
} from "../../features/bots/api";
import {
  normalizeOptionalText,
  parseJsonObject,
  toPrettyJson,
} from "../../lib/forms/serializers";
import type { NotificationBotResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";

interface BotFormState {
  name: string;
  bot_type: string;
  webhook_url: string;
  secret: string;
  mention_strategy: string;
  template_config_text: string;
  is_active: boolean;
}

const emptyBotForm: BotFormState = {
  name: "",
  bot_type: "dingtalk",
  webhook_url: "",
  secret: "",
  mention_strategy: "",
  template_config_text: "{}",
  is_active: true,
};

function buildBotPayload(
  form: BotFormState,
  editingBot: NotificationBotResponse | null
): NotificationBotPayload {
  const payload: NotificationBotPayload = {
    name: form.name.trim(),
    bot_type: form.bot_type.trim(),
    webhook_url: form.webhook_url.trim(),
    mention_strategy: normalizeOptionalText(form.mention_strategy),
    template_config: parseJsonObject(form.template_config_text),
    is_active: form.is_active,
  };

  if (form.secret.trim() !== "") {
    payload.secret = form.secret.trim();
  } else if (editingBot === null) {
    payload.secret = undefined;
  }

  return payload;
}

function buildBotForm(row: NotificationBotResponse): BotFormState {
  return {
    name: row.name,
    bot_type: row.bot_type,
    webhook_url: row.webhook_url,
    secret: "",
    mention_strategy: row.mention_strategy ?? "",
    template_config_text: toPrettyJson(row.template_config),
    is_active: row.is_active,
  };
}

/**
 * 机器人管理页接入新增、编辑与启停，方便直接验证通知配置维护流程。
 */
export function BotListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingBot, setEditingBot] = useState<NotificationBotResponse | null>(null);
  const [form, setForm] = useState<BotFormState>(emptyBotForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["notification-bots", "list"],
    queryFn: () => listBots(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = buildBotPayload(form, editingBot);
      if (editingBot === null) {
        return createBot(payload);
      }
      return updateBot(editingBot.id, payload);
    },
    onSuccess: async () => {
      setDrawerOpen(false);
      setEditingBot(null);
      setForm(emptyBotForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["notification-bots", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存机器人失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: NotificationBotResponse) =>
      updateBotStatus(row.id, !row.is_active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-bots", "list"] });
    },
  });

  const testMutation = useMutation({
    mutationFn: async (row: NotificationBotResponse) => testBot(row.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-bots", "list"] });
    },
  });

  function openCreateDrawer() {
    setEditingBot(null);
    setForm(emptyBotForm);
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: NotificationBotResponse) {
    setEditingBot(row);
    setForm(buildBotForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function updateField<KeyT extends keyof BotFormState>(
    field: KeyT,
    value: BotFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    try {
      await saveMutation.mutateAsync();
    } catch (error) {
      if (error instanceof SyntaxError) {
        setErrorMessage("模板配置 JSON 解析失败，请检查格式。");
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存机器人失败。");
      }
    }
  }

  const botColumns: DataTableColumn<NotificationBotResponse>[] = [
    {
      key: "name",
      title: "机器人名称",
    },
    {
      key: "bot_type",
      title: "类型",
    },
    {
      key: "webhook_url",
      title: "Webhook",
    },
    {
      key: "secret_masked",
      title: "Secret",
      render: (row) => row.secret_masked || "-",
    },
    {
      key: "last_test_status",
      title: "连通性",
      render: (row) => <StatusBadge value={row.last_test_status} />,
    },
    {
      key: "is_active",
      title: "状态",
      render: (row) => <StatusBadge value={row.is_active} />,
    },
    {
      key: "actions",
      title: "操作",
      render: (row) => (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => openEditDrawer(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={() => void testMutation.mutateAsync(row)}
            className="rounded-full border border-cyan-200 px-3 py-1 text-xs text-cyan-700 transition hover:border-cyan-300 hover:bg-cyan-50"
          >
            测试
          </button>
          <button
            type="button"
            onClick={() => void statusMutation.mutateAsync(row)}
            className="rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            {row.is_active ? "停用" : "启用"}
          </button>
        </div>
      ),
    },
  ];

  return (
    <>
      <div className="space-y-4 rounded-[2rem] border border-slate-200 bg-gradient-to-br from-slate-50 via-white to-cyan-50/50 p-4 shadow-sm">
        <ConsolePageHeader
          title="通知机器人控制台"
          description="在这里维护通知渠道配置、脱敏 secret 与测试状态回显。"
          action={
            <button
              type="button"
              onClick={openCreateDrawer}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
            >
              新建机器人
            </button>
          }
        />
        <section className="rounded-[1.75rem] border border-slate-200 bg-white p-6 shadow-sm">
          <DataTable
            columns={botColumns}
            rows={data?.items ?? []}
            loading={isLoading}
            emptyText="暂无机器人配置"
          />
        </section>
      </div>

      <DrawerForm
        open={drawerOpen}
        title={editingBot === null ? "创建通知机器人" : "编辑通知机器人"}
        description="维护通知渠道类型、Webhook 与模板配置。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-5" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            机器人名称
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            类型
            <input
              value={form.bot_type}
              onChange={(event) => updateField("bot_type", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            Webhook URL
            <input
              value={form.webhook_url}
              onChange={(event) => updateField("webhook_url", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            Secret
            <input
              value={form.secret}
              onChange={(event) => updateField("secret", event.target.value)}
              className={inputClassName}
              type="password"
              placeholder={editingBot ? "留空表示不修改" : ""}
            />
          </label>

          <label className={labelClassName}>
            Mention Strategy
            <input
              value={form.mention_strategy}
              onChange={(event) => updateField("mention_strategy", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            模板配置 JSON
            <textarea
              value={form.template_config_text}
              onChange={(event) =>
                updateField("template_config_text", event.target.value)
              }
              className={`${inputClassName} min-h-32 font-mono text-xs`}
            />
          </label>

          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => updateField("is_active", event.target.checked)}
            />
            启用机器人
          </label>

          <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={saveMutation.isPending}
              className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saveMutation.isPending ? "保存中..." : "保存机器人"}
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
