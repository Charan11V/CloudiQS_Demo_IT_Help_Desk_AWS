import type {
  User,
  Category,
  ConversationResponse,
  Ticket,
  Approval,
  MeResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_BAKERY_API_URL || '/api';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error', message: 'Unknown error' }));
      throw new Error(error.detail || error.message || `API error: ${response.status}`);
    }

    return response.json();
  }

  async demoLogin(credentials: { user_id: string; password?: string }) {
    return this.request<{ user: User; success: boolean }>('/auth/demo-login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async logout() {
    return this.request<{ success: boolean }>('/auth/logout', {
      method: 'POST',
    });
  }

  async getMe(): Promise<MeResponse> {
    return this.request<MeResponse>('/auth/me');
  }

  async getCatalog() {
    return this.request<{ root_options: Category[]; issues: unknown[] }>('/catalog');
  }

  async createConversation() {
    return this.request<ConversationResponse>('/conversations', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getConversation(conversationId: string) {
    return this.request<ConversationResponse>(`/conversations/${conversationId}`);
  }

  async sendTurn(
    conversationId: string,
    payload: {
      option_id?: string;
      option_ids?: string[];
      free_text?: string;
      control?: string;
    }
  ) {
    return this.request<ConversationResponse>(
      `/conversations/${conversationId}/turns`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  }

  async getMyTickets() {
    return this.request<{ tickets: Ticket[] }>('/tickets/mine');
  }

  async getTicket(ticketId: string) {
    return this.request<Ticket>(`/tickets/${ticketId}`);
  }

  async consentAction(actionId: string) {
    return this.request<{ state: string; action_id: string; approval_id?: string; requires_approval?: boolean }>(
      `/actions/${actionId}/consent`,
      {
        method: 'POST',
        body: JSON.stringify({ consented: true }),
      }
    );
  }

  async executeAction(actionId: string) {
    return this.request<{ state: string; execution_id: string; result?: unknown }>(
      `/actions/${actionId}/execute`,
      {
        method: 'POST',
        body: JSON.stringify({}),
      }
    );
  }

  async getPendingApprovals() {
    return this.request<{ approvals: Approval[]; count: number }>('/approvals/pending');
  }

  async decideApproval(
    approvalId: string,
    decision: { approved: boolean; reason?: string }
  ) {
    return this.request<{ decision: string; approval_id: string }>(
      `/approvals/${approvalId}/decision`,
      {
        method: 'POST',
        body: JSON.stringify({
          decision: decision.approved ? 'approved' : 'rejected',
          reason: decision.reason,
        }),
      }
    );
  }
}

export const apiClient = new ApiClient();
