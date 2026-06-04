import { tokenStore } from "../../lib/auth/token-store";
import { http } from "../../lib/api/http";
import type {
  AgentMessageResponse,
  AgentSSEEvent,
  AgentSSEEventPayload,
  AgentSessionResponse,
} from "../../lib/api/types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export interface AgentSessionPayload {
  title: string;
  branch: string;
}

export interface AgentMessagePayload {
  content: string;
}

export async function createAgentSession(
  projectId: number,
  payload: AgentSessionPayload
) {
  const response = await http.post<AgentSessionResponse>(
    `/projects/${projectId}/agent/sessions`,
    payload
  );
  return response.data;
}

export async function listAgentSessions(projectId: number) {
  const response = await http.get<AgentSessionResponse[]>(
    `/projects/${projectId}/agent/sessions`
  );
  return response.data;
}

export async function createAgentMessage(
  projectId: number,
  sessionId: number,
  payload: AgentMessagePayload
) {
  const response = await http.post<AgentMessageResponse>(
    `/projects/${projectId}/agent/sessions/${sessionId}/messages`,
    payload
  );
  return response.data;
}

export async function streamAgentSession(
  projectId: number,
  sessionId: number,
  options: {
    signal?: AbortSignal;
    onEvent: (event: AgentSSEEvent) => void;
  }
) {
  const tokenPair = tokenStore.load();
  const headers = new Headers({
    Accept: "text/event-stream",
  });
  if (tokenPair?.access_token) {
    headers.set("Authorization", `Bearer ${tokenPair.access_token}`);
  }

  const response = await fetch(
    `${API_BASE_URL}/projects/${projectId}/agent/sessions/${sessionId}/stream`,
    {
      method: "GET",
      headers,
      signal: options.signal,
    }
  );
  if (!response.ok) {
    throw new Error(`订阅会话流失败（${response.status}）。`);
  }
  if (response.body === null) {
    throw new Error("浏览器当前不支持读取流式响应。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    buffer = emitSSEChunks(buffer, options.onEvent);
  }

  const tail = decoder.decode();
  if (tail) {
    buffer += tail;
  }
  emitSSEChunks(`${buffer}\n\n`, options.onEvent);
}

function emitSSEChunks(
  buffer: string,
  onEvent: (event: AgentSSEEvent) => void
) {
  let remainder = buffer;
  while (true) {
    const boundaryIndex = remainder.indexOf("\n\n");
    if (boundaryIndex < 0) {
      break;
    }
    const chunk = remainder.slice(0, boundaryIndex).trim();
    remainder = remainder.slice(boundaryIndex + 2);
    if (!chunk) {
      continue;
    }
    const parsed = parseSSEChunk(chunk);
    if (parsed !== null) {
      onEvent(parsed);
    }
  }
  return remainder;
}

function parseSSEChunk(chunk: string): AgentSSEEvent | null {
  let eventName = "message";
  const dataLines: string[] = [];
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  const dataText = dataLines.join("\n");
  let payload: AgentSSEEventPayload = { session_id: 0 };
  if (dataText) {
    payload = JSON.parse(dataText) as AgentSSEEventPayload;
  }
  return {
    event: eventName,
    data: payload,
  };
}
