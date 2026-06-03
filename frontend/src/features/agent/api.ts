import { http } from "../../lib/api/http";
import { tokenStore } from "../../lib/auth/token-store";
import type {
  AgentMessageAcceptedResponse,
  AgentMessageResponse,
  AgentSessionResponse,
} from "../../lib/api/types";

export async function listAgentSessions(projectId: number) {
  const response = await http.get<AgentSessionResponse[]>(
    `/projects/${projectId}/agent/sessions`
  );
  return response.data;
}

export async function createAgentSession(projectId: number, title: string) {
  const response = await http.post<AgentSessionResponse>(
    `/projects/${projectId}/agent/sessions`,
    { title }
  );
  return response.data;
}

export async function listAgentMessages(sessionId: number) {
  const response = await http.get<AgentMessageResponse[]>(
    `/agent/sessions/${sessionId}/messages`
  );
  return response.data;
}

export async function sendAgentMessage(sessionId: number, content: string) {
  const response = await http.post<AgentMessageAcceptedResponse>(
    `/agent/sessions/${sessionId}/messages`,
    { content }
  );
  return response.data;
}

export function createAgentEventSource(sessionId: number, sinceEventId?: number) {
  const accessToken = tokenStore.load()?.access_token;
  const params = new URLSearchParams();
  if (sinceEventId !== undefined) {
    params.set("since_event_id", String(sinceEventId));
  }
  if (accessToken) {
    params.set("access_token", accessToken);
  }
  const queryString = params.toString();
  const suffix = queryString ? `?${queryString}` : "";
  return new EventSource(`/api/v1/agent/sessions/${sessionId}/stream${suffix}`);
}
