import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "motion/react";
import { type FormEvent, useMemo, useState } from "react";
import {
  CheckCircle2,
  Cpu,
  Edit2,
  Plus,
  Trash2,
} from "lucide-react";

import { ConsoleToast } from "../../components/console/ConsoleToast";
import {
  createModel,
  listModels,
  updateModel,
  updateModelStatus,
  type LlmModelPayload,
} from "../../features/models/api";
import { normalizeOptionalText } from "../../lib/forms/serializers";
import type { LlmModelResponse } from "../../lib/api/types";

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
  temperature: "0.2",
  max_tokens: "16384",
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

export function ModelListPage() {
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<LlmModelResponse | null>(null);
  const [form, setForm] = useState<ModelFormState>(emptyModelForm);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const { data } = useQuery({
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
      const isEditing = editingModel !== null;
      setIsCreateOpen(false);
      setEditingModel(null);
      setForm(emptyModelForm);
      setErrorMessage(null);
      setSuccessMessage(isEditing ? "模型节点已更新。" : "模型节点已部署。");
      await queryClient.invalidateQueries({ queryKey: ["models", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "保存模型配置失败。");
    },
  });

  const statusMutation = useMutation({
    mutationFn: async (row: LlmModelResponse) =>
      updateModelStatus(row.id, !row.is_active),
    onSuccess: async (_, row) => {
      setSuccessMessage(row.is_active ? `${row.name} 已停用。` : `${row.name} 已激活。`);
      await queryClient.invalidateQueries({ queryKey: ["models", "list"] });
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || "更新模型状态失败。");
    },
  });

  const models = useMemo(() => data?.items ?? [], [data?.items]);

  function updateField<KeyT extends keyof ModelFormState>(
    field: KeyT,
    value: ModelFormState[KeyT]
  ) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function openCreateModal() {
    setEditingModel(null);
    setForm(emptyModelForm);
    setErrorMessage(null);
    setIsCreateOpen(true);
  }

  function openEditModal(row: LlmModelResponse) {
    setEditingModel(row);
    setForm(buildModelForm(row));
    setErrorMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
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

  const activeModalTitle =
    editingModel === null ? "部署新的审查 AI 节点" : `编辑智算审查节点配置 (${editingModel.name})`;

  const modalBody = (
    <form onSubmit={handleSubmit} className="space-y-6">
      {errorMessage ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] text-rose-700">
          {errorMessage}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-5 text-left md:grid-cols-2">
        <div className="space-y-1.5 md:col-span-2">
          <label className="block text-[11px] font-bold text-slate-700">
            模型展示别名 (name)
          </label>
          <input
            aria-label="模型展示别名 (name)"
            type="text"
            required
            value={form.name}
            onChange={(event) => updateField("name", event.target.value)}
            placeholder="例如: DeepSeek R1 满血版"
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] font-bold text-slate-700">
            接口提供商 (provider)
          </label>
          <select
            value={form.provider}
            onChange={(event) => updateField("provider", event.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-hidden focus:ring-2 focus:ring-indigo-500/10"
          >
            <option value="openai">OpenAI Endpoint</option>
            <option value="DeepSeek">DeepSeek API</option>
            <option value="Gemini">Google Gemini SDK</option>
            <option value="Custom">接入自建大模型</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] font-bold text-slate-700">
            唯一接口代码标识 (model_code)
          </label>
          <input
            aria-label="唯一接口代码标识 (model_code)"
            type="text"
            required
            value={form.model_code}
            onChange={(event) => updateField("model_code", event.target.value)}
            placeholder="例如: deepseek-reasoner"
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5 md:col-span-2">
          <label className="block text-[11px] font-bold text-slate-700">
            自建 Base URL 端点 (可选) (base_url)
          </label>
          <input
            aria-label="自建 Base URL 端点 (可选) (base_url)"
            type="text"
            value={form.base_url}
            onChange={(event) => updateField("base_url", event.target.value)}
            placeholder="https://api.deepseek.com/v1"
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5 md:col-span-2">
          <label className="block text-[11px] font-bold text-slate-700">
            密钥令牌掩码 (加密保存) (api_key_masked)
          </label>
          <input
            aria-label="密钥令牌掩码 (加密保存) (api_key_masked)"
            type="password"
            required={editingModel === null}
            value={form.api_key}
            onChange={(event) => updateField("api_key", event.target.value)}
            placeholder={editingModel === null ? "自动保存加密上下文" : "留空表示不修改"}
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 font-mono text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] font-bold text-slate-700">
            核温系数 (temperature)
          </label>
          <input
            aria-label="核温系数 (temperature)"
            type="number"
            step="0.1"
            min="0"
            max="1.5"
            value={form.temperature}
            onChange={(event) => updateField("temperature", event.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] font-bold text-slate-700">
            约束标记 (max_tokens)
          </label>
          <input
            aria-label="约束标记 (max_tokens)"
            type="number"
            step="1024"
            min="1024"
            max="131072"
            value={form.max_tokens}
            onChange={(event) => updateField("max_tokens", event.target.value)}
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>

        <div className="space-y-1.5 md:col-span-2">
          <label className="block text-[11px] font-bold text-slate-700">
            特选 Prompt 模板 (可选) (prompt_template)
          </label>
          <input
            aria-label="特选 Prompt 模板 (可选) (prompt_template)"
            type="text"
            value={form.prompt_template}
            onChange={(event) => updateField("prompt_template", event.target.value)}
            placeholder="不填则使用系统预置 project_templates 主模板"
            className="w-full rounded-lg border border-slate-200 bg-white px-3.5 py-2 text-xs text-slate-800 outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10"
          />
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_default}
            onChange={(event) => updateField("is_default", event.target.checked)}
          />
          <span>设为默认模型</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => updateField("is_active", event.target.checked)}
          />
          <span>启用模型</span>
        </label>
      </div>

      <div className="flex justify-end gap-3 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => {
            setIsCreateOpen(false);
            setEditingModel(null);
          }}
          className="cursor-pointer rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
        >
          取消
        </button>
        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="cursor-pointer rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-2xs transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {editingModel === null ? "部署生效" : "保存更新"}
        </button>
      </div>
    </form>
  );

  return (
    <>
      <div className="mx-auto max-w-7xl space-y-4 p-6">
        <div className="flex flex-col items-start justify-between gap-3 rounded-xl border border-slate-200/80 bg-white px-5 py-3.5 shadow-3xs sm:flex-row sm:items-center">
          <div>
            <h2 className="flex items-center gap-1.5 font-sans text-sm font-bold text-slate-800">
              <Cpu className="h-4 w-4 shrink-0 text-indigo-500" />
              <span>审查模型与计算智能矩阵</span>
            </h2>
            <p className="mt-0.5 text-[11px] text-slate-500">
              配置并调整用于自动代码审查的 LLM 模型。参数属性对齐 PostgreSQL{" "}
              <code className="rounded bg-slate-100 px-1 text-[10px] font-mono text-indigo-650">
                llm_models
              </code>{" "}
              表结构。
            </p>
          </div>
          <button
            type="button"
            onClick={openCreateModal}
            className="flex cursor-pointer items-center gap-1.5 rounded-lg bg-[#0c0d1b] px-3.5 py-1.5 text-[11px] font-bold text-white shadow-2xs transition-all active:scale-[0.98] hover:bg-slate-900"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>部署新模型智算</span>
          </button>
        </div>

        <div className="grid grid-cols-1 gap-6 pb-12 md:grid-cols-3">
          {models.map((model) => {
            const isActiveNode = model.is_active;
            const isDefaultNode = model.is_default;
            return (
              <div
                key={model.id}
                className={`flex flex-col justify-between space-y-5 rounded-2xl border bg-white p-6 transition-all ${
                  isActiveNode
                    ? "border-indigo-500 ring-2 ring-indigo-500/5 shadow-md"
                    : "border-slate-200 shadow-xs hover:border-slate-300"
                }`}
              >
                <div className="space-y-4">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate rounded-sm bg-slate-100 px-2 py-0.5 font-mono text-[9px] font-bold uppercase tracking-wider text-slate-600">
                        {model.provider}
                      </span>
                      {isDefaultNode ? (
                        <span className="shrink-0 rounded-sm border border-indigo-100/60 bg-indigo-50 px-1.5 py-0.5 text-[9px] font-bold text-indigo-700">
                          DEFAULT
                        </span>
                      ) : null}
                    </div>

                    <button
                      type="button"
                      aria-label="设为激活"
                      onClick={() => void statusMutation.mutateAsync(model)}
                      className={`flex shrink-0 cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold transition-colors ${
                        isActiveNode
                          ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                          : "border-indigo-200 bg-white text-indigo-600 hover:bg-indigo-50"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isActiveNode ? "bg-emerald-500 animate-pulse" : "bg-slate-400"
                        }`}
                      />
                      <span>{isActiveNode ? "活动中" : "设为激活"}</span>
                    </button>
                  </div>

                  <div className="space-y-1">
                    <h3 className="flex items-center gap-1.5 text-sm font-bold text-slate-900">
                      <Cpu className="h-4 w-4 shrink-0 text-slate-400" />
                      <span className="truncate">{model.name}</span>
                    </h3>
                    <p className="font-mono text-[10px] text-slate-400">
                      CODE: {model.model_code}
                    </p>
                  </div>

                  <div className="space-y-2 border-t border-slate-100 pt-3 text-[11px] text-slate-600">
                    <div className="flex justify-between font-light">
                      <span className="text-slate-450">接口端点 (base_url)</span>
                      <span
                        className="max-w-[130px] truncate font-mono text-slate-700"
                        title={model.base_url || "系统集成 SDK"}
                      >
                        {model.base_url || "系统集成 SDK"}
                      </span>
                    </div>

                    <div className="flex justify-between font-light">
                      <span className="text-slate-450">采样核温 (temperature)</span>
                      <span className="font-mono font-semibold text-slate-800">
                        {model.temperature ?? "-"}
                      </span>
                    </div>

                    <div className="flex justify-between font-light">
                      <span className="text-slate-450">标记限制 (max_tokens)</span>
                      <span className="font-mono font-semibold text-slate-800">
                        {model.max_tokens ?? "-"}
                      </span>
                    </div>

                    <div className="flex justify-between font-light">
                      <span className="text-slate-450">累计调阅 (queries)</span>
                      <span className="font-mono font-semibold text-indigo-600">
                        {model.queries_count ?? 0} 次
                      </span>
                    </div>

                    <div className="flex items-center justify-between pt-1.5 font-light">
                      <span className="text-slate-450">最近校验状态</span>
                      <span className="flex items-center gap-1 text-[9.5px] font-medium text-emerald-600">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>
                          {model.last_test_status === "success" ? "通过 (PASSED)" : "待校验"}
                        </span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => openEditModal(model)}
                    className="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 py-1.5 text-[11px] font-semibold text-slate-600 shadow-3xs transition-colors hover:bg-indigo-50/50 hover:text-indigo-600"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                    <span>编辑参数配置</span>
                  </button>

                  {!isDefaultNode ? (
                    <button
                      type="button"
                      disabled
                      title="当前后端暂未提供模型删除接口"
                      className="cursor-not-allowed rounded-xl border border-slate-200 bg-rose-50/30 p-1.5 text-rose-400 opacity-60"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <AnimatePresence>
        {isCreateOpen ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <div className="absolute inset-0" onClick={() => setIsCreateOpen(false)} />
            <motion.div
              initial={{ scale: 0.95, y: 15, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 15, opacity: 0 }}
              transition={{ type: "spring", duration: 0.35, bounce: 0.1 }}
              className="relative z-10 max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-slate-250 bg-white p-6 shadow-2xl md:p-8"
            >
              <div className="flex items-center justify-between border-b border-slate-150 pb-3">
                <h4 className="flex items-center gap-2 font-sans text-base font-bold text-slate-900">
                  <Plus className="h-5 w-5 text-indigo-500" />
                  <span>{activeModalTitle}</span>
                </h4>
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full p-1 text-base font-bold text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>
              <div className="pt-6">{modalBody}</div>
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {editingModel ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="w-full max-w-2xl space-y-5 rounded-3xl border border-slate-250 bg-white p-6 shadow-2xl md:p-8"
            >
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 className="flex items-center gap-2 font-sans text-base font-bold text-slate-900">
                  <Edit2 className="h-5 w-5 text-indigo-500" />
                  <span>{activeModalTitle}</span>
                </h3>
                <button
                  type="button"
                  onClick={() => setEditingModel(null)}
                  className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-full p-1 text-base font-bold text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>
              {modalBody}
            </motion.div>
          </div>
        ) : null}
      </AnimatePresence>

      {successMessage ? (
        <div className="fixed bottom-4 right-4 z-50 w-[320px]">
          <ConsoleToast title="操作成功" message={successMessage} tone="success" />
        </div>
      ) : null}
    </>
  );
}
