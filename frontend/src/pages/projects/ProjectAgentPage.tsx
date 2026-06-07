import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { PageCard } from "../../components/common/PageCard";
import {
  createAgentMessage,
  createAgentSession,
  listAgentSessions,
  streamAgentSession,
} from "../../features/agent/api";
import type { AgentSSEEvent, AgentSessionResponse } from "../../lib/api/types";

const inputClassName =
  "mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-cyan-300 focus:bg-white";
const labelClassName = "block text-sm font-medium text-slate-700";

interface TimelineEntry {
  id: string;
  event: string;
  label: string;
  body: string;
  createdAt: string;
}

function formatDateTime(value: string | undefined) {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("zh-CN", {
    hour12: false,
  });
}

function buildTimelineEntry(event: AgentSSEEvent): TimelineEntry | null {
  const { data } = event;
  const createdAt = data.created_at ?? new Date().toISOString();
  if (event.event === "message") {
    return {
      id: `message-${data.id ?? data.sequence ?? createdAt}`,
      event: "message",
      label: data.role === "assistant" ? "助手消息" : "用户消息",
      body: String(data.content ?? ""),
      createdAt,
    };
  }

  const payload = data.payload ?? {};
  if (event.event === "tool_called") {
    return {
      id: `tool-called-${data.id ?? data.sequence ?? createdAt}`,
      event: "tool_called",
      label: "工具调用",
      body: `${String(payload.tool_name ?? "unknown")} ${JSON.stringify(payload.tool_args ?? {}, null, 2)}`,
      createdAt,
    };
  }

  if (event.event === "tool_result") {
    return {
      id: `tool-result-${data.id ?? data.sequence ?? createdAt}`,
      event: "tool_result",
      label: "工具结果",
      body: String(payload.tool_result ?? ""),
      createdAt,
    };
  }

  if (event.event === "assistant_delta") {
    return {
      id: `assistant-delta-${data.id ?? data.sequence ?? createdAt}`,
      event: "assistant_delta",
      label: "助手输出",
      body: String(payload.delta ?? ""),
      createdAt,
    };
  }

  if (event.event === "final_answer") {
    return {
      id: `final-answer-${data.id ?? data.sequence ?? createdAt}`,
      event: "final_answer",
      label: "最终回答",
      body: String(payload.final_answer ?? ""),
      createdAt,
    };
  }

  if (event.event === "run_started") {
    return {
      id: `run-started-${data.id ?? data.sequence ?? createdAt}`,
      event: "run_started",
      label: "运行开始",
      body: `分支 ${String(payload.branch ?? "-")} @ ${String(payload.head_sha ?? "-")}`,
      createdAt,
    };
  }

  if (event.event === "ready") {
    return {
      id: `ready-${data.session_id}-${createdAt}`,
      event: "ready",
      label: "流结束",
      body: `会话 ${data.session_id} 已完成当前回放。`,
      createdAt,
    };
  }

  return {
    id: `${event.event}-${data.id ?? data.sequence ?? createdAt}`,
    event: event.event,
    label: event.event,
    body: JSON.stringify(payload, null, 2),
    createdAt,
  };
}

/**
 * 项目级仓库对话助手页面：围绕锁定分支创建持续对话，并展示基础事件流回放。
 */
export function ProjectAgentPage() {
  const { projectId = "0" } = useParams();
  const numericProjectId = Number(projectId);
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("主分支仓库助手");
  const [branch, setBranch] = useState("main");
  const [messageInput, setMessageInput] = useState("");
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [streamNonce, setStreamNonce] = useState(0);
  const [streamStatus, setStreamStatus] = useState("尚未连接");
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);

  const sessionsQuery = useQuery({
    queryKey: ["agent", "sessions", numericProjectId],
    queryFn: () => listAgentSessions(numericProjectId),
    enabled: Number.isFinite(numericProjectId) && numericProjectId > 0,
  });

  const sessions = sessionsQuery.data ?? [];
  const currentSession = useMemo(
    () => sessions.find((item) => item.id === selectedSessionId) ?? null,
    [selectedSessionId, sessions]
  );

  useEffect(() => {
    if (selectedSessionId !== null || sessions.length === 0) {
      return;
    }
    setSelectedSessionId(sessions[0].id);
  }, [selectedSessionId, sessions]);

  useEffect(() => {
    if (selectedSessionId === null) {
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    setTimeline([]);
    setStreamStatus("正在连接事件流...");

    void streamAgentSession(numericProjectId, selectedSessionId, {
      signal: controller.signal,
      onEvent: (event) => {
        if (cancelled) {
          return;
        }
        const entry = buildTimelineEntry(event);
        if (entry !== null) {
          setTimeline((current) => {
            if (current.some((item) => item.id === entry.id)) {
              return current;
            }
            return [...current, entry];
          });
        }
        setStreamStatus(event.event === "ready" ? "当前回放已完成" : `收到 ${event.event}`);
      },
    })
      .then(() => {
        if (!cancelled) {
          setStreamStatus("当前回放已完成");
        }
      })
      .catch((error: Error) => {
        if (!cancelled && error.name !== "AbortError") {
          setStreamStatus(error.message || "读取事件流失败。");
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [numericProjectId, selectedSessionId, streamNonce]);

  const createSessionMutation = useMutation({
    mutationFn: () =>
      createAgentSession(numericProjectId, {
        title,
        branch,
      }),
    onSuccess: async (session) => {
      setSelectedSessionId(session.id);
      setTimeline([]);
      await queryClient.invalidateQueries({
        queryKey: ["agent", "sessions", numericProjectId],
      });
      setStreamNonce((value) => value + 1);
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: () =>
      createAgentMessage(numericProjectId, selectedSessionId!, {
        content: messageInput,
      }),
    onSuccess: async () => {
      setMessageInput("");
      await queryClient.invalidateQueries({
        queryKey: ["agent", "sessions", numericProjectId],
      });
      setStreamNonce((value) => value + 1);
    },
  });

  return (
    <section className="space-y-6">
      <PageCard
        title="仓库对话助手"
        description="创建锁定分支的持续会话，围绕当前项目仓库进行只读分析与多轮对话。"
      >
        <div className="grid gap-6 xl:grid-cols-[320px,1fr]">
          <aside className="space-y-6">
            <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-5 py-5">
              <h2 className="text-lg font-semibold text-slate-900">创建会话</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                会话在整个生命周期内锁定到同一条分支。
              </p>
              <div className="mt-5 space-y-4">
                <label className={labelClassName}>
                  会话标题
                  <input
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                    className={inputClassName}
                  />
                </label>
                <label className={labelClassName} htmlFor="agent-branch">
                  选择分支
                  <input
                    id="agent-branch"
                    value={branch}
                    onChange={(event) => setBranch(event.target.value)}
                    className={inputClassName}
                  />
                </label>
                <button
                  type="button"
                  onClick={() => void createSessionMutation.mutateAsync()}
                  disabled={createSessionMutation.isPending}
                  className="w-full rounded-full bg-slate-950 px-4 py-3 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {createSessionMutation.isPending ? "创建中..." : "创建会话"}
                </button>
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-white">
              <header className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">已有会话</h2>
                <p className="mt-1 text-sm text-slate-600">
                  当前项目下共 {sessions.length} 条仓库对话。
                </p>
              </header>
              <div className="divide-y divide-slate-100">
                {sessionsQuery.isLoading ? (
                  <p className="px-5 py-6 text-sm text-slate-500">正在加载会话...</p>
                ) : sessions.length > 0 ? (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      onClick={() => {
                        setSelectedSessionId(session.id);
                        setStreamNonce((value) => value + 1);
                      }}
                      className={[
                        "flex w-full flex-col px-5 py-4 text-left transition",
                        selectedSessionId === session.id
                          ? "bg-cyan-50"
                          : "hover:bg-slate-50",
                      ].join(" ")}
                    >
                      <span className="font-medium text-slate-900">{session.title}</span>
                      <span className="mt-1 text-xs text-slate-500">
                        {session.branch} | {session.model ?? session.provider ?? "-"}
                      </span>
                    </button>
                  ))
                ) : (
                  <p className="px-5 py-6 text-sm text-slate-500">还没有会话，先创建一条。</p>
                )}
              </div>
            </section>
          </aside>

          <div className="space-y-6">
            <section className="rounded-[1.5rem] border border-slate-200 bg-white px-5 py-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">
                    {currentSession?.title ?? "未选择会话"}
                  </h2>
                  <p className="mt-1 text-sm text-slate-600">
                    {currentSession
                      ? `分支 ${currentSession.branch} | ${currentSession.model ?? currentSession.provider ?? "-"}`
                      : "先在左侧创建或选择一个会话。"}
                  </p>
                </div>
                <div className="rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
                  事件流状态：{streamStatus}
                </div>
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-white">
              <header className="border-b border-slate-200 px-5 py-4">
                <h2 className="text-lg font-semibold text-slate-900">消息与 Trace</h2>
                <p className="mt-1 text-sm text-slate-600">
                  展示当前 session 的消息记录、工具调用和最终回答。
                </p>
              </header>
              <div className="max-h-[520px] space-y-3 overflow-y-auto px-5 py-5">
                {timeline.length > 0 ? (
                  timeline.map((entry) => (
                    <article
                      key={entry.id}
                      className={[
                        "rounded-[1.25rem] border px-4 py-4",
                        entry.event === "message" && entry.label === "用户消息"
                          ? "border-cyan-200 bg-cyan-50"
                          : entry.event === "message"
                            ? "border-slate-200 bg-slate-50"
                            : "border-slate-200 bg-white",
                      ].join(" ")}
                    >
                      <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                        <p className="text-sm font-medium text-slate-900">{entry.label}</p>
                        <p className="text-xs text-slate-500">{formatDateTime(entry.createdAt)}</p>
                      </div>
                      <pre className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-700">
                        {entry.body || "-"}
                      </pre>
                    </article>
                  ))
                ) : (
                  <p className="text-sm text-slate-500">还没有可展示的消息或事件。</p>
                )}
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-white px-5 py-5">
              <label className={labelClassName}>
                发送消息
                <textarea
                  value={messageInput}
                  onChange={(event) => setMessageInput(event.target.value)}
                  className={`${inputClassName} min-h-28`}
                  placeholder="例如：这个仓库的核心功能是什么？"
                />
              </label>
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={() => void sendMessageMutation.mutateAsync()}
                  disabled={
                    selectedSessionId === null ||
                    messageInput.trim() === "" ||
                    sendMessageMutation.isPending
                  }
                  className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {sendMessageMutation.isPending ? "发送中..." : "发送消息"}
                </button>
              </div>
            </section>
          </div>
        </div>
      </PageCard>
    </section>
  );
}
