/** Client for Agentic Bakery guided helpdesk (proxied via /bakery-api). */

export type BakeryOption = {
  id: string;
  label: string;
  type?: string;
  description?: string;
};

export type BakeryConversation = {
  conversation_id: string;
  case_id?: string;
  state: string;
  assistant_message: string;
  breadcrumb?: string[];
  options?: BakeryOption[];
  controls?: string[];
  finding?: {
    hypothesis?: string;
    observations?: Array<{ field: string; value: string; source: string }>;
  };
  action_proposal?: {
    action_id?: string;
    action_code?: string;
    description?: string;
    impact?: string;
    requires_approval?: boolean;
  };
  ticket?: {
    ticket_id: string;
    summary?: string;
    status?: string;
    assigned_team?: string;
    description?: string;
    issue_code?: string;
    created_at?: string;
    source?: string;
  };
  demo_mode?: boolean;
  selection_mode?: "single" | "multiple";
  require_confirm?: boolean;
  confirm_label?: string;
  selection_hint?: string;
  /** True only on Others / describe path — show the free-text composer. */
  allow_free_text?: boolean;
  free_text_hint?: string;
  free_text_submit_label?: string;
  /** After Others ticket: no further input until Start over. */
  session_locked?: boolean;
  /** Present when resuming after refresh */
  resumed?: boolean;
  messages?: Array<{
    message_id?: string;
    role: string;
    content: string;
    timestamp?: string | null;
  }>;
};

const BASE = "/bakery-api";

async function bakeryFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || `Bakery API ${res.status}`);
  }
  return res.json();
}

export type BakeryTicket = {
  ticket_id: string;
  summary?: string;
  description?: string;
  status?: string;
  priority?: string;
  issue_code?: string;
  category?: string;
  assigned_team?: string;
  requester?: string;
  created_at?: string;
  updated_at?: string;
  source?: string;
};

export const bakery = {
  demoLogin(user_id: string) {
    return bakeryFetch<{ success: boolean; user: { user_id: string; display_name: string } }>(
      "/auth/demo-login",
      { method: "POST", body: JSON.stringify({ user_id }) }
    );
  },
  createConversation() {
    return bakeryFetch<BakeryConversation>("/conversations", {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  getActiveConversation() {
    return bakeryFetch<BakeryConversation>("/conversations/active");
  },
  resumeConversation(conversationId: string) {
    return bakeryFetch<BakeryConversation>(
      `/conversations/${encodeURIComponent(conversationId)}`
    );
  },
  sendTurn(
    conversationId: string,
    payload: {
      option_id?: string;
      option_ids?: string[];
      free_text?: string;
      control?: string;
    }
  ) {
    return bakeryFetch<BakeryConversation>(`/conversations/${conversationId}/turns`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listMyTickets() {
    return bakeryFetch<{ tickets: BakeryTicket[]; count: number }>("/tickets/mine");
  },
  getTicket(ticketId: string) {
    return bakeryFetch<BakeryTicket>(`/tickets/${encodeURIComponent(ticketId)}`);
  },
  updateTicketStatus(ticketId: string, status: "open" | "in_progress" | "resolved" | "closed") {
    return bakeryFetch<BakeryTicket>(`/tickets/${encodeURIComponent(ticketId)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  },
  listTicketEvents(ticketId: string) {
    return bakeryFetch<{
      ticket_id: string;
      assigned_team?: string;
      status?: string;
      events: Array<{
        event_id: string;
        actor?: string;
        prior_status?: string;
        next_status?: string;
        reason?: string;
        occurred_at?: string;
      }>;
      count: number;
    }>(`/tickets/${encodeURIComponent(ticketId)}/events`);
  },
};
