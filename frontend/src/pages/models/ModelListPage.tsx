import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { DataTable, type DataTableColumn } from "../../components/common/DataTable";
import { DrawerForm } from "../../components/common/DrawerForm";
import { PageCard } from "../../components/common/PageCard";
import { StatusBadge } from "../../components/common/StatusBadge";
import {
  createModel,
  listModels,
  updateModel,
  updateModelStatus,
  type LlmModelPayload,
} from "../../features/models/api";
import { normalizeOptionalText } from "../../lib/forms/serializers";
import type { LlmModelResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";

interface ModelFormState {
  name: string;
  provider: string;
  model_code: string;
  base_url: string;
  api_key: string;
  temperature: string;
  max_tokens: string;
  top_p: string;
  prompt_template: string;
  is_default: boolean;
  is_active: boolean;
}

const emptyModelForm: ModelFormState = {
  name: "",
  provider: "openai",
  model_code: "",
  base_url: "",
  api_key: "",
  temperature: "",
  max_tokens: "",
  top_p: "",
  prompt_template: "",
  is_default: false,
  is_active: true,
};

function buildModelPayload(
  form: ModelFormState,
  editingModel: LlmModelResponse | null
): LlmModelPayload {
  const payload: LlmModelPayload = {
    name: form.name.trim(),
    provider: form.provider.trim(),
    model_code: form.model_code.trim(),
    base_url: normalizeOptionalText(form.base_url),
    temperature: form.temperature === "" ? null : Number(form.temperature),
    max_tokens: form.max_tokens === "" ? null : Number(form.max_tokens),
    top_p: form.top_p === "" ? null : Number(form.top_p),
    prompt_template: normalizeOptionalText(form.prompt_template),
    is_default: form.is_default,
    is_active: form.is_active,
  };

  if (form.api_key.trim() !== "") {
    payload.api_key = form.api_key.trim();
  } else if (editingModel === null) {
    payload.api_key = undefined;
  }

  return payload;
}

function buildModelForm(row: LlmModelResponse): ModelFormState {
  return {
    name: row.name,
    provider: row.provider,
    model_code: row.model_code,
    base_url: row.base_url ?? "",
    api_key: "",
    temperature: row.temperature === null ? "" : String(row.temperature),
    max_tokens: row.max_tokens === null ? "" : String(row.max_tokens),
    top_p: row.top_p === null ? "" : String(row.top_p),
    prompt_template: row.prompt_template ?? "",
    is_default: row.is_default,
    is_active: row.is_active,
  };
}

/**
 * 模型管理页接入新增、编辑与启停，方便直接维护模型配置。
 */
export function ModelListPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<LlmModelResponse | null>(null);
  const [form, setForm] = useState<ModelFormState>(emptyModelForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["models", "list"],
    queryFn: () => listModels(),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = buildModelPayload(form, editingModel);
      if (editingModel === null) {
        return createModel(payload);
      }
      return updateModel(editingModel.id, payload);
    },
    onSuccess: async () => {
      setDrawerOpen(false);
      setEditingModel(null);
      setForm(emptyModelForm);
      setErrorMessage(null);
      await queryClient.invalidateQueries({ queryKey: ["models", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存模型配置失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: LlmModelResponse) =>
      updateModelStatus(row.id, !row.is_active),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["models", "list"] });
    },
  });

  function openCreateDrawer() {
    setEditingModel(null);
    setForm(emptyModelForm);
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function openEditDrawer(row: LlmModelResponse) {
    setEditingModel(row);
    setForm(buildModelForm(row));
    setErrorMessage(null);
    setDrawerOpen(true);
  }

  function updateField<KeyT extends keyof ModelFormState>(
    field: KeyT,
    value: ModelFormState[KeyT]
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
      if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("保存模型配置失败。");
      }
    }
  }

  const modelColumns: DataTableColumn<LlmModelResponse>[] = [
    {
      key: "name",
      title: "模型名称",
    },
    {
      key: "provider",
      title: "提供方",
    },
    {
      key: "model_code",
      title: "模型标识",
    },
    {
      key: "api_key_masked",
      title: "API Key",
      render: (row) => row.api_key_masked || "-",
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
      <PageCard
        title="模型管理"
        description="查看模型提供方、连接状态与脱敏后的密钥摘要。"
        actions={
          <button
            type="button"
            onClick={openCreateDrawer}
            className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            新建模型
          </button>
        }
      >
        <DataTable
          columns={modelColumns}
          rows={data?.items ?? []}
          loading={isLoading}
          emptyText="暂无模型配置"
        />
      </PageCard>

      <DrawerForm
        open={drawerOpen}
        title={editingModel === null ? "创建模型配置" : "编辑模型配置"}
        description="维护模型提供方、基础连接参数与默认配置。"
        onClose={() => setDrawerOpen(false)}
      >
        <form className="space-y-5" onSubmit={handleSubmit}>
          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <label className={labelClassName}>
            模型名称
            <input
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            提供方
            <input
              value={form.provider}
              onChange={(event) => updateField("provider", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            模型标识
            <input
              value={form.model_code}
              onChange={(event) => updateField("model_code", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            Base URL
            <input
              value={form.base_url}
              onChange={(event) => updateField("base_url", event.target.value)}
              className={inputClassName}
            />
          </label>

          <label className={labelClassName}>
            API Key
            <input
              value={form.api_key}
              onChange={(event) => updateField("api_key", event.target.value)}
              className={inputClassName}
              type="password"
              placeholder={editingModel ? "留空表示不修改" : ""}
            />
          </label>

          <div className="grid gap-4 md:grid-cols-3">
            <label className={labelClassName}>
              Temperature
              <input
                value={form.temperature}
                onChange={(event) => updateField("temperature", event.target.value)}
                className={inputClassName}
                type="number"
                step="0.1"
              />
            </label>
            <label className={labelClassName}>
              Max Tokens
              <input
                value={form.max_tokens}
                onChange={(event) => updateField("max_tokens", event.target.value)}
                className={inputClassName}
                type="number"
              />
            </label>
            <label className={labelClassName}>
              Top P
              <input
                value={form.top_p}
                onChange={(event) => updateField("top_p", event.target.value)}
                className={inputClassName}
                type="number"
                step="0.1"
              />
            </label>
          </div>

          <label className={labelClassName}>
            提示词模板
            <textarea
              value={form.prompt_template}
              onChange={(event) => updateField("prompt_template", event.target.value)}
              className={`${inputClassName} min-h-32`}
            />
          </label>

          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_default}
              onChange={(event) => updateField("is_default", event.target.checked)}
            />
            设为默认模型
          </label>

          <label className="flex items-center gap-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => updateField("is_active", event.target.checked)}
            />
            启用模型
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
              {saveMutation.isPending ? "保存中..." : "保存模型"}
            </button>
          </div>
        </form>
      </DrawerForm>
    </>
  );
}
