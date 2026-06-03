import { startTransition, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PageCard } from "../../components/common/PageCard";
import {
  createAgentEventSource,
  createAgentSession,
  listAgentMessages,
  listAgentSessions,
  sendAgentMessage,
} from "../../features/agent/api";
import type {
  AgentMessageResponse,
  AgentSessionResponse,
} from "../../lib/api/types";

interface AgentStreamEnvelope {
  id: number;
  event_type: string;
  payload: Record<string, unknown>;
}

function buildMessage(
  id: number,
  sessionId: number,
  role: "user" | "assistant",
  content: string,
  status: string
): AgentMessageResponse {
  return {
    id,
    session_id: sessionId,
    run_id: null,
    role,
    content,
    content_format: "markdown",
    status,
    sequence: id,
    metadata: {},
    created_at: new Date().toISOString(),
  };
}

export function ProjectAgentPage() {
  const { projectId } = useParams();
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const lastEventIdRef = useRef(0);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [messages, setMessages] = useState<AgentMessageResponse[]>([]);
  const [toolEvents, setToolEvents] = useState<string[]>([]);
  const [streamState, setStreamState] = useState("idle");
  const numericProjectId = Number(projectId);

  const sessionsQuery = useQuery({
    queryKey: ["agent", "sessions", numericProjectId],
    queryFn: () => listAgentSessions(numericProjectId),
    enabled: Number.isFinite(numericProjectId),
  });
  const sessions = sessionsQuery.data ?? [];
  const selectedSession = useMemo(
    () => sessions.find((item) => item.id === selectedSessionId) ?? null,
    [selectedSessionId, sessions]
  );

  useEffect(() => {
    if (selectedSessionId !== null || sessions.length === 0) {
      return;
    }
    setSelectedSessionId(sessions[0].id);
  }, [selectedSessionId, sessions]);

  const messagesQuery = useQuery({
    queryKey: ["agent", "messages", selectedSessionId],
    queryFn: () => listAgentMessages(selectedSessionId as number),
    enabled: selectedSessionId !== null,
  });

  useEffect(() => {
    if (!messagesQuery.data) {
      return;
    }
    startTransition(() => {
      setMessages(messagesQuery.data);
    });
  }, [messagesQuery.data]);

  useEffect(() => {
    lastEventIdRef.current = 0;
    setToolEvents([]);
  }, [selectedSessionId]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, []);

  const createSessionMutation = useMutation({
    mutationFn: async () => createAgentSession(numericProjectId, "仓库助手"),
    onSuccess: async (session) => {
      await queryClient.invalidateQueries({
        queryKey: ["agent", "sessions", numericProjectId],
      });
      setSelectedSessionId(session.id);
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      let sessionId = selectedSessionId;
      if (sessionId === null) {
        const created = await createSessionMutation.mutateAsync();
        sessionId = created.id;
      }
      const accepted = await sendAgentMessage(sessionId, content);
      return { accepted, sessionId };
    },
    onSuccess: async ({ accepted, sessionId }, content) => {
      startTransition(() => {
        setMessages((current) => [
          ...current,
          buildMessage(accepted.user_message_id, sessionId, "user", content, "completed"),
          buildMessage(accepted.assistant_message_id, sessionId, "assistant", "", "streaming"),
        ]);
        setStreamState("streaming");
      });
      setMessageDraft("");
      openEventStream(sessionId);
      await queryClient.invalidateQueries({
        queryKey: ["agent", "messages", sessionId],
      });
    },
  });

  function openEventStream(sessionId: number) {
    eventSourceRef.current?.close();
    const source = createAgentEventSource(sessionId, lastEventIdRef.current);
    eventSourceRef.current = source;

    source.addEventListener("assistant_delta", (event) => {
      const envelope = JSON.parse((event as MessageEvent).data) as AgentStreamEnvelope;
      lastEventIdRef.current = Math.max(lastEventIdRef.current, envelope.id);
      const delta = String(envelope.payload.delta ?? "");
      startTransition(() => {
        setMessages((current) => {
          const next = [...current];
          const targetIndex = [...next]
            .reverse()
            .findIndex((item) => item.role === "assistant");
          if (targetIndex === -1) {
            return current;
          }
          const index = next.length - 1 - targetIndex;
          next[index] = {
            ...next[index],
            content: next[index].content + delta,
            status: "streaming",
          };
          return next;
        });
      });
    });

    source.addEventListener("assistant_message", (event) => {
      const envelope = JSON.parse((event as MessageEvent).data) as AgentStreamEnvelope;
      lastEventIdRef.current = Math.max(lastEventIdRef.current, envelope.id);
      const content = String(envelope.payload.content ?? "");
      const messageId = Number(envelope.payload.message_id ?? 0);
      startTransition(() => {
        setMessages((current) =>
          current.map((item) =>
            item.id === messageId
              ? {
                  ...item,
                  content,
                  status: "completed",
                }
              : item
          )
        );
      });
    });

    source.addEventListener("tool_result", (event) => {
      const envelope = JSON.parse((event as MessageEvent).data) as AgentStreamEnvelope;
      lastEventIdRef.current = Math.max(lastEventIdRef.current, envelope.id);
      const name = String(envelope.payload.name ?? "tool");
      const output = String(envelope.payload.output ?? "");
      startTransition(() => {
        setToolEvents((current) => [`${name}: ${output}`, ...current].slice(0, 6));
      });
    });

    source.addEventListener("final", (event) => {
      const envelope = JSON.parse((event as MessageEvent).data) as AgentStreamEnvelope;
      lastEventIdRef.current = Math.max(lastEventIdRef.current, envelope.id);
      startTransition(() => {
        setStreamState("completed");
      });
      source.close();
      eventSourceRef.current = null;
    });

    source.addEventListener("error", () => {
      startTransition(() => {
        setStreamState("error");
      });
      source.close();
      eventSourceRef.current = null;
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = messageDraft.trim();
    if (!trimmed) {
      return;
    }
    await sendMessageMutation.mutateAsync(trimmed);
  }

  return (
    <div className="space-y-6">
      <PageCard
        title="仓库理解助手"
        description="围绕当前项目建立持续对话，保留最近消息、快照状态和工具阅读轨迹。"
        actions={
          <Link
            to="/projects"
            className="rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
          >
            返回项目列表
          </Link>
        }
      >
        <div className="grid gap-6 xl:grid-cols-[17rem_minmax(0,1fr)_18rem]">
          <aside className="space-y-4">
            <section className="rounded-[1.5rem] border border-slate-200 bg-slate-50/80 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                    Sessions
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-900">
                    对话会话
                  </h2>
                </div>
                <button
                  type="button"
                  onClick={() => void createSessionMutation.mutateAsync()}
                  className="rounded-full bg-slate-950 px-3 py-2 text-xs font-medium text-white transition hover:bg-slate-800"
                >
                  新建
                </button>
              </div>
              <div className="mt-4 space-y-3">
                {sessions.length === 0 ? (
                  <p className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                    还没有会话，点击右上角创建第一条。
                  </p>
                ) : (
                  sessions.map((session) => (
                    <button
                      key={session.id}
                      type="button"
                      onClick={() => setSelectedSessionId(session.id)}
                      className={[
                        "w-full rounded-2xl border px-4 py-3 text-left transition",
                        selectedSessionId === session.id
                          ? "border-cyan-300 bg-white shadow-sm"
                          : "border-slate-200 bg-white/70 hover:border-slate-300",
                      ].join(" ")}
                    >
                      <p className="text-sm font-semibold text-slate-900">{session.title}</p>
                      <p className="mt-1 text-xs text-slate-500">
                        session #{session.id}
                      </p>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                Snapshot
              </p>
              <div className="mt-3 space-y-3 text-sm text-slate-600">
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <p className="text-xs text-slate-500">Project</p>
                  <p className="mt-1 font-medium text-slate-900">#{numericProjectId}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <p className="text-xs text-slate-500">Snapshot ID</p>
                  <p className="mt-1 font-medium text-slate-900">
                    {selectedSession?.snapshot_id ?? "-"}
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <p className="text-xs text-slate-500">Stream</p>
                  <p className="mt-1 font-medium text-slate-900">{streamState}</p>
                </div>
              </div>
            </section>
          </aside>

          <section className="rounded-[1.75rem] border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-5 py-4">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                Conversation
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-900">
                针对当前仓库的持续问答
              </h2>
            </div>
            <div className="space-y-4 px-5 py-5">
              <div className="min-h-[24rem] space-y-4">
                {messages.length === 0 ? (
                  <div className="rounded-[1.5rem] border border-dashed border-slate-300 bg-slate-50 px-5 py-10 text-sm text-slate-500">
                    可以直接问“后端入口在哪里”或“刚才提到的模块和权限链路有什么关系”。
                  </div>
                ) : (
                  messages.map((message) => (
                    <article
                      key={message.id}
                      className={[
                        "rounded-[1.5rem] px-4 py-4",
                        message.role === "user"
                          ? "ml-auto max-w-[85%] bg-slate-950 text-white"
                          : "max-w-[90%] border border-slate-200 bg-slate-50 text-slate-900",
                      ].join(" ")}
                    >
                      <p className="text-xs uppercase tracking-[0.22em] opacity-60">
                        {message.role === "user" ? "User" : "Assistant"}
                      </p>
                      <p className="mt-2 whitespace-pre-wrap text-sm leading-7">
                        {message.content || (message.status === "streaming" ? "正在生成回答..." : "")}
                      </p>
                    </article>
                  ))
                )}
              </div>

              <form onSubmit={handleSubmit} className="space-y-3 border-t border-slate-200 pt-4">
                <label className="block text-sm font-medium text-slate-700">
                  新问题
                  <textarea
                    value={messageDraft}
                    onChange={(event) => setMessageDraft(event.target.value)}
                    placeholder="例如：基于刚才的回答，接下来我应该先读哪几个文件？"
                    className="mt-2 min-h-28 w-full rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 outline-none transition focus:border-cyan-300 focus:bg-white"
                  />
                </label>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-slate-500">
                    支持多轮追问，消息会结合当前 session 和记忆状态持续理解。
                  </p>
                  <button
                    type="submit"
                    disabled={sendMessageMutation.isPending}
                    className="rounded-full bg-slate-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {sendMessageMutation.isPending ? "发送中..." : "发送"}
                  </button>
                </div>
              </form>
            </div>
          </section>

          <aside className="space-y-4">
            <section className="rounded-[1.5rem] border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                Tool Trail
              </p>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">最近工具事件</h2>
              <div className="mt-4 space-y-3">
                {toolEvents.length === 0 ? (
                  <p className="rounded-2xl border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
                    当前还没有工具事件，等模型触发读取或搜索后会显示在这里。
                  </p>
                ) : (
                  toolEvents.map((item) => (
                    <div
                      key={item}
                      className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700"
                    >
                      {item}
                    </div>
                  ))
                )}
              </div>
            </section>

            <section className="rounded-[1.5rem] border border-cyan-100 bg-cyan-50/70 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-cyan-700">
                Fingerprint
              </p>
              <p className="mt-3 text-sm leading-7 text-slate-700">
                {selectedSession?.workspace_fingerprint
                  ? `${selectedSession.workspace_fingerprint.slice(0, 18)}...`
                  : "会在会话创建后生成。"}
              </p>
            </section>
          </aside>
        </div>
      </PageCard>
    </div>
  );
}
