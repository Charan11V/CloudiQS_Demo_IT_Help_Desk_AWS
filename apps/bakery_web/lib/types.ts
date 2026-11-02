// API Types
export interface User {
  user_id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: 'employee' | 'it_engineer' | 'it_manager' | 'tenant_admin';
  department?: string;
}

export interface Device {
  device_id: string;
  device_name: string;
  platform: string;
  asset_id: string;
  health_status?: string;
  disk_free_gb?: number;
  disk_total_gb?: number;
}

export interface Category {
  id: string;
  label: string;
  description?: string;
}

export interface Option {
  id: string;
  label: string;
  type: 'category' | 'subcategory' | 'issue' | 'action' | 'control' | 'answer' | 'checklist' | 'symptom' | 'multi' | string;
  description?: string;
}

export interface Finding {
  issue_code: string;
  confidence: number;
  hypothesis: string;
  observations: Array<{
    field: string;
    value: string;
    source: string;
  }>;
  proposed_action_code?: string;
  requires_approval: boolean;
}

export interface ActionProposal {
  action_id: string;
  action_code: string;
  description: string;
  impact: string;
  requires_approval: boolean;
  approval_status?: 'pending' | 'approved' | 'rejected';
}

export interface Ticket {
  ticket_id: string;
  conversation_id?: string;
  case_id?: string;
  status: string;
  priority: string;
  summary: string;
  description?: string;
  created_at: string;
  updated_at?: string;
  assigned_team?: string;
  requester_id?: string;
}

export interface ConversationResponse {
  conversation_id: string;
  case_id?: string;
  state: string;
  assistant_message: string;
  breadcrumb?: string[];
  options?: Option[];
  controls?: string[];
  finding?: Finding;
  action_proposal?: ActionProposal;
  ticket?: Ticket;
  demo_mode: boolean;
  selection_mode?: 'single' | 'multiple';
  require_confirm?: boolean;
  confirm_label?: string;
  selection_hint?: string;
  allow_free_text?: boolean;
  free_text_hint?: string;
  free_text_submit_label?: string;
  session_locked?: boolean;
}

export interface Approval {
  approval_id: string;
  action_id: string;
  requester_id: string;
  requester_name: string;
  action_code: string;
  description: string;
  impact: string;
  target_resource: string;
  created_at: string;
  expires_at: string;
  status: 'pending' | 'approved' | 'rejected';
}

export interface MeResponse {
  user: User;
  devices: Device[];
  tenant_name: string;
  demo_mode: boolean;
  tenant_id?: string;
  user_id?: string;
  display_name?: string;
  full_name?: string;
  role?: string;
  email?: string;
}
