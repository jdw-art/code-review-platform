import type {
  AgentMessageResponse,
  AgentSessionResponse,
  AgentSSEEvent,
} from "../../lib/api/types";

export function toConsoleAgentSession(session: AgentSessionResponse) {
  return {
    id: session.id,
    projectId: session.project_id,
    title: session.title,
    status: session.status,
    branch: session.branch,
    provider: session.provider,
    model: session.model,
    lastMessageAt: session.last_message_at,
  };
}

export function toConsoleAgentMessage(message: AgentMessageResponse) {
  return {
    id: message.id,
    sessionId: message.session_id,
    role: message.role,
    content: message.content,
    status: message.status,
    sequence: message.sequence,
    createdAt: message.created_at,
  };
}

export function toConsoleAgentStreamEvent(event: AgentSSEEvent) {
  return {
    type: event.event,
    payload: event.data,
  };
}
