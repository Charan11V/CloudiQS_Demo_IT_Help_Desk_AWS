"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { admin } from "@/lib/api-client";
import { toast } from "sonner";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  EmptyState,
  Skeleton,
  Eyebrow,
} from "@/components/helio";

export default function AdminPage() {
  const queryClient = useQueryClient();

  const { data: integrationsData, isLoading, error: integrationsError } = useQuery({
    queryKey: ["admin-integrations"],
    queryFn: admin.getIntegrations,
    retry: false,
  });

  const { data: users } = useQuery({
    queryKey: ["admin-users"],
    queryFn: admin.getUsers,
    retry: false,
  });

  const { data: policy, error: policyError } = useQuery({
    queryKey: ["admin-policy"],
    queryFn: admin.getPolicies,
    retry: false,
  });

  const { data: auditLog, error: auditError } = useQuery({
    queryKey: ["admin-audit"],
    queryFn: admin.getAudit,
    retry: false,
  });

  const testIntegrationMutation = useMutation({
    mutationFn: (key: string) => admin.testIntegration(key),
    onSuccess: (data) => {
      toast.success(`${data.integration_key} test: ${data.status}`);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Test failed");
    },
  });

  const savePolicyMutation = useMutation({
    mutationFn: (body: {
      auto_approve_thresholds?: Record<string, unknown>;
      security_settings?: Record<string, unknown>;
    }) => admin.updatePolicy(body),
    onSuccess: (data) => {
      toast.success(data.message || "Policy saved");
      void queryClient.invalidateQueries({ queryKey: ["admin-policy"] });
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Policy save failed");
    },
  });

  const integrations = integrationsData || [];

  const isUnauthorized =
    (integrationsError as { status?: number } | null)?.status === 403 ||
    (policyError as { status?: number } | null)?.status === 403 ||
    (auditError as { status?: number } | null)?.status === 403;

  if (isUnauthorized) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Tenant"
          title="Admin"
          description="Manage integrations, policies, users, and system settings."
        />
        <Surface>
          <EmptyState
            title="Access denied"
            description="You don’t have permission to access admin features. Contact your administrator if you need access."
          />
        </Surface>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Tenant"
        title="Admin"
        description="Manage integrations, policies, users, and system settings."
      />

      <Surface className="p-5 sm:p-6">
        <Eyebrow className="mb-4">Integrations</Eyebrow>
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : integrations.length === 0 ? (
          <EmptyState
            title="No integrations configured"
            description="Connected systems will appear here when available."
            className="py-8"
          />
        ) : (
          <ul className="space-y-3">
            {integrations.map(
              (integration: {
                key: string;
                name?: string;
                type?: string;
                status?: string;
              }) => (
                <li
                  key={integration.key}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-[var(--stroke)] p-4"
                >
                  <div>
                    <p className="font-medium text-[var(--ink)]">{integration.name}</p>
                    <p className="text-sm text-[var(--ink-secondary)]">{integration.type}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusChip
                      tone={
                        ["error", "failed", "disconnected"].includes(
                          (integration.status || "").toLowerCase()
                        )
                          ? "danger"
                          : "success"
                      }
                    >
                      {integration.status || "connected_mock"}
                    </StatusChip>
                    <HelioButton
                      size="sm"
                      variant="secondary"
                      onClick={() => testIntegrationMutation.mutate(integration.key)}
                      disabled={testIntegrationMutation.isPending}
                      loading={testIntegrationMutation.isPending}
                    >
                      Test
                    </HelioButton>
                  </div>
                </li>
              )
            )}
          </ul>
        )}
      </Surface>

      {policy ? (
        <Surface className="p-5 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <Eyebrow>Policy configuration</Eyebrow>
            <HelioButton
              size="sm"
              variant="secondary"
              disabled={savePolicyMutation.isPending}
              loading={savePolicyMutation.isPending}
              onClick={() =>
                savePolicyMutation.mutate({
                  auto_approve_thresholds: policy.auto_approve_thresholds || {
                    note: "demo_ack",
                  },
                  security_settings: policy.security_settings || {
                    require_approval_for_sensitive: true,
                  },
                })
              }
            >
              Save policy
            </HelioButton>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between gap-4 py-2 border-b border-[var(--stroke)]">
              <span className="text-[var(--ink-secondary)]">Auto-approve threshold</span>
              <span className="font-medium text-[var(--ink)] text-right">
                {policy.auto_approve_threshold ||
                  (policy.auto_approve_thresholds
                    ? JSON.stringify(policy.auto_approve_thresholds).slice(0, 40)
                    : "None")}
              </span>
            </div>
            <div className="flex justify-between gap-4 py-2 border-b border-[var(--stroke)]">
              <span className="text-[var(--ink-secondary)]">
                Require approval for sensitive actions
              </span>
              <span className="font-medium text-[var(--ink)]">
                {policy.require_approval_for_sensitive ??
                policy.security_settings?.require_approval_for_sensitive
                  ? "Yes"
                  : "No"}
              </span>
            </div>
            <p className="text-xs text-[var(--ink-tertiary)] pt-2">
              Demo mode: Save acknowledges the current policy snapshot via PATCH /admin/policy.
            </p>
          </div>
        </Surface>
      ) : null}

      {users && users.length > 0 ? (
        <Surface className="p-5 sm:p-6">
          <Eyebrow className="mb-4">Users ({users.length})</Eyebrow>
          <ul className="space-y-2">
            {users.slice(0, 10).map(
              (user: {
                user_id?: string;
                id?: string;
                displayName?: string;
                email?: string;
                mail?: string;
                accountEnabled?: boolean;
                status?: string;
              }) => (
                <li
                  key={user.user_id || user.id}
                  className="flex items-center justify-between gap-3 rounded-xl border border-[var(--stroke)] p-3"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-[var(--ink)] truncate">
                      {user.displayName || user.email || user.user_id}
                    </p>
                    <p className="text-xs text-[var(--ink-tertiary)] truncate">
                      {user.mail || user.email}
                    </p>
                  </div>
                  <StatusChip
                    tone={
                      user.accountEnabled || user.status === "active" ? "success" : "neutral"
                    }
                  >
                    {user.accountEnabled || user.status === "active" ? "Active" : "Inactive"}
                  </StatusChip>
                </li>
              )
            )}
          </ul>
        </Surface>
      ) : null}

      {auditLog && auditLog.length > 0 ? (
        <Surface className="p-5 sm:p-6">
          <Eyebrow className="mb-4">Recent audit log</Eyebrow>
          <ul className="space-y-2 text-sm">
            {auditLog.slice(0, 10).map(
              (
                entry: {
                  event_type?: string;
                  action?: string;
                  actor?: string;
                  timestamp?: string;
                },
                idx: number
              ) => (
                <li
                  key={idx}
                  className="rounded-xl border border-[var(--stroke)] p-3"
                >
                  <p className="font-medium text-[var(--ink)]">
                    {entry.event_type || entry.action}
                  </p>
                  <p className="text-xs text-[var(--ink-tertiary)] mt-1">
                    {entry.actor}
                    {entry.timestamp
                      ? ` · ${new Date(entry.timestamp).toLocaleString()}`
                      : ""}
                  </p>
                </li>
              )
            )}
          </ul>
        </Surface>
      ) : null}
    </div>
  );
}
