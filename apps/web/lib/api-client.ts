/**
 * API Client for HELIO backend
 * Uses relative /api-backend/* paths which are proxied via Next.js rewrites
 */

const API_BASE = "/api-backend";

export class APIError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    credentials: "include", // Send HttpOnly cookies
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Redirect to login
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new APIError(401, "unauthorized", "Session expired");
    }

    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: response.statusText };
    }

    throw new APIError(
      response.status,
      errorData.code || "unknown",
      errorData.detail || errorData.message || "Request failed"
    );
  }

  return response.json();
}

// Auth
export const auth = {
  login: (persona_key: string) =>
    fetchAPI<{ success: boolean; tenant_id: string; user_id: string }>(
      "/auth/demo-login",
      {
        method: "POST",
        body: JSON.stringify({ persona_key }),
      }
    ),

  logout: () =>
    fetchAPI<{ success: boolean }>("/auth/logout", { method: "POST" }),

  getSession: () =>
    fetchAPI<{
      tenant_id: string;
      user_id: string;
      persona_key: string;
      role?: string;
      name?: string;
      email?: string;
    }>("/auth/session"),
};

// Workspace
export const workspace = {
  getSummary: () => fetchAPI<any>("/workspace/summary"),
};

// Conversations
export const conversations = {
  create: () => fetchAPI<{ conversation_id: string }>("/conversations", {
    method: "POST",
  }),

  list: () => fetchAPI<any[]>("/conversations"),

  get: (id: string) => fetchAPI<any>(`/conversations/${id}`),

  createRun: (conversationId: string, message: string) =>
    fetchAPI<{ run_id: string; status: string }>(
      `/conversations/${conversationId}/runs`,
      {
        method: "POST",
        body: JSON.stringify({ message }),
      }
    ),
};

// Runs
export const runs = {
  get: (id: string) => fetchAPI<any>(`/runs/${id}`),

  getEvents: (id: string) => fetchAPI<any>(`/runs/${id}/events`),

  getToolEvents: (id: string) => fetchAPI<any[]>(`/runs/${id}/tool-events`),
};

// Tickets
export const tickets = {
  list: (params?: { status?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", params.limit.toString());
    return fetchAPI<{ tickets: any[]; count: number }>(
      `/tickets?${query.toString()}`
    );
  },

  get: (id: string) => fetchAPI<any>(`/tickets/${id}`),

  create: (data: {
    summary: string;
    description: string;
    category: string;
    priority?: string;
    idempotency_key?: string;
  }) =>
    fetchAPI<any>("/tickets", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  patch: (
    id: string,
    data: { status?: string; assignee_id?: string; priority?: string }
  ) =>
    fetchAPI<any>(`/tickets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  addComment: (id: string, body: string, visibility: "public" | "internal" = "public") =>
    fetchAPI<any>(`/tickets/${id}/comments`, {
      method: "POST",
      body: JSON.stringify({ body, visibility }),
    }),

  listComments: (id: string) => fetchAPI<any[]>(`/tickets/${id}/comments`),
};

// Approvals
export const approvals = {
  list: (status?: string) => {
    const query = status ? `?status=${status}` : "";
    return fetchAPI<{ approvals: any[]; count: number }>(`/approvals${query}`);
  },

  get: (id: string) => fetchAPI<any>(`/approvals/${id}`),

  decide: (id: string, decision: "approved" | "rejected", reason: string) =>
    fetchAPI<any>(`/approvals/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, reason }),
    }),

  execute: (id: string) =>
    fetchAPI<any>(`/approvals/${id}/execute`, { method: "POST" }),
};

// Actions
export const actions = {
  propose: (data: {
    action_type: "identity_account_unlock" | "vpn_certificate_renewal";
    target_user_id: string;
    device_id?: string;
    rationale: string;
  }) =>
    fetchAPI<any>("/actions/propose", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// Analytics
export const analytics = {
  getTickets: (params?: any) => fetchAPI<any>("/analytics/tickets"),
  getAgentRuns: () => fetchAPI<any>("/analytics/agent-runs"),
};

// Admin
export const admin = {
  getIntegrations: () => fetchAPI<any[]>("/admin/integrations"),
  testIntegration: (key: string) =>
    fetchAPI<any>(`/admin/integrations/${key}/test`, { method: "POST" }),
  getUsers: () => fetchAPI<any[]>("/admin/users"),
  getPolicies: () => fetchAPI<any>("/admin/policy"),
  updatePolicy: (data: {
    auto_approve_thresholds?: Record<string, unknown>;
    security_settings?: Record<string, unknown>;
  }) =>
    fetchAPI<any>("/admin/policy", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getAudit: () => fetchAPI<any[]>("/admin/audit"),
};

// Notifications
export const notifications = {
  list: () => fetchAPI<any[]>("/notifications"),
  markRead: (id: string) =>
    fetchAPI<{ ok: boolean }>(`/notifications/${id}/read`, { method: "POST" }),
};

// Devices
export const devices = {
  list: () => fetchAPI<any[]>("/devices"),
  get: (id: string) => fetchAPI<any>(`/devices/${id}`),
};

// Evaluations
export const evaluations = {
  listRuns: () => fetchAPI<any[]>("/evaluations/runs"),
  startRun: (data?: { suite?: "curated" | "safety"; max_cases?: number }) =>
    fetchAPI<any>("/evaluations/runs", {
      method: "POST",
      body: JSON.stringify(data || { suite: "curated", max_cases: 10 }),
    }),
  getRun: (id: string) => fetchAPI<any>(`/evaluations/runs/${id}`),
  getTests: (id: string) => fetchAPI<any[]>(`/evaluations/runs/${id}/tests`),
};

// Security
export const security = {
  getFindings: () => fetchAPI<any>("/security/findings"),
  createEscalation: (data: {
    reason: string;
    severity?: "low" | "medium" | "high" | "critical";
    ticket_id?: string;
    evidence_ids?: string[];
  }) =>
    fetchAPI<any>("/security/escalations", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listEscalations: () => fetchAPI<any[]>("/security/escalations"),
};
