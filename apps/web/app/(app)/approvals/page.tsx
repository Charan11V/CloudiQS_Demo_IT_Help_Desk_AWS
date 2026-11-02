"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { approvals } from "@/lib/api-client";
import { Clock } from "lucide-react";
import { cn, formatDate } from "@/lib/utils";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  EmptyState,
  Skeleton,
} from "@/components/helio";

type FilterKey = "pending" | "approved" | "rejected";

type ApprovalRow = {
  approval_id: string;
  action_type?: string;
  rationale?: string;
  status?: string;
  created_at?: string;
  expires_at?: string;
  target_user_id?: string;
  requester_id?: string;
  action?: {
    action?: string;
    target_user_id?: string;
    device_id?: string;
  };
  rejection_reason?: string;
};

type LocalDecision = {
  status: "approved" | "rejected";
  rejection_reason?: string;
  decided_at: string;
};

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: "pending", label: "Yet to review" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];

function humanizeAction(type?: string): string {
  if (!type) return "Approval request";
  const map: Record<string, string> = {
    identity_account_unlock: "Account unlock",
    vpn_certificate_renewal: "VPN certificate renewal",
    software_install: "Software install",
  };
  return map[type] || type.replace(/_/g, " ");
}

function approvalTone(status?: string): "warning" | "success" | "danger" | "neutral" {
  if (status === "pending") return "warning";
  if (status === "approved") return "success";
  if (status === "rejected") return "danger";
  return "neutral";
}

function statusLabel(status?: string): string {
  if (status === "pending") return "Yet to review";
  if (status === "approved") return "Approved";
  if (status === "rejected") return "Rejected";
  return status || "Unknown";
}

function normalizeRow(raw: ApprovalRow): ApprovalRow {
  const actionType = raw.action_type || raw.action?.action;
  const target = raw.target_user_id || raw.action?.target_user_id;
  return {
    ...raw,
    action_type: actionType,
    target_user_id: target,
    created_at: raw.created_at || raw.expires_at,
  };
}

export default function ApprovalsPage() {
  const [filter, setFilter] = useState<FilterKey>("pending");
  const [localDecisions, setLocalDecisions] = useState<Record<string, LocalDecision>>({});
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const { data: approvalsData, isLoading } = useQuery({
    queryKey: ["approvals"],
    queryFn: () => approvals.list(),
  });

  const approvalsList = useMemo(() => {
    const rows = (approvalsData?.approvals || []).map(normalizeRow);
    return rows.map((row) => {
      const local = localDecisions[row.approval_id];
      if (!local) return row;
      return {
        ...row,
        status: local.status,
        rejection_reason: local.rejection_reason,
        created_at: row.created_at,
      };
    });
  }, [approvalsData, localDecisions]);

  const filtered = useMemo(
    () => approvalsList.filter((a) => (a.status || "pending") === filter),
    [approvalsList, filter]
  );

  const counts = useMemo(
    () => ({
      pending: approvalsList.filter((a) => (a.status || "pending") === "pending").length,
      approved: approvalsList.filter((a) => a.status === "approved").length,
      rejected: approvalsList.filter((a) => a.status === "rejected").length,
    }),
    [approvalsList]
  );

  const markApproved = (id: string) => {
    setLocalDecisions((prev) => ({
      ...prev,
      [id]: { status: "approved", decided_at: new Date().toISOString() },
    }));
    setRejectingId(null);
    setRejectReason("");
  };

  const markRejected = (id: string) => {
    const reason = rejectReason.trim();
    if (!reason) return;
    setLocalDecisions((prev) => ({
      ...prev,
      [id]: {
        status: "rejected",
        rejection_reason: reason,
        decided_at: new Date().toISOString(),
      },
    }));
    setRejectingId(null);
    setRejectReason("");
  };

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Governance"
        title="Approvals"
        description="Review requests, approve, or reject with a short note."
      />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => {
          const active = filter === f.key;
          return (
            <button
              key={f.key}
              type="button"
              onClick={() => setFilter(f.key)}
              className={cn(
                "inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm transition-colors border",
                active
                  ? "bg-[var(--signal-soft)] border-[var(--signal)]/30 text-[var(--signal)] font-medium"
                  : "border-[var(--stroke)] text-[var(--ink-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--ink)]"
              )}
            >
              {f.label}
              <span
                className={cn(
                  "min-w-[1.25rem] rounded-md px-1.5 py-0.5 text-xs tabular-nums",
                  active ? "bg-[var(--surface)] text-[var(--signal)]" : "bg-[var(--signal-soft)]/40 text-[var(--ink-tertiary)]"
                )}
              >
                {counts[f.key]}
              </span>
            </button>
          );
        })}
      </div>

      <Surface className="p-5 sm:p-6">
        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            title={
              filter === "pending"
                ? "Nothing yet to review"
                : filter === "approved"
                  ? "No approved requests"
                  : "No rejected requests"
            }
            description="Switch filters to see other approval states."
          />
        ) : (
          <ul className="space-y-3">
            {filtered.map((approval) => {
              const when = approval.created_at;
              const isPending = (approval.status || "pending") === "pending";
              const isRejecting = rejectingId === approval.approval_id;

              return (
                <li
                  key={approval.approval_id}
                  className="rounded-xl border border-[var(--stroke)] p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-[var(--ink)]">
                        {humanizeAction(approval.action_type)}
                      </p>
                      {approval.rationale ? (
                        <p className="mt-1 text-sm text-[var(--ink-secondary)]">
                          {approval.rationale}
                        </p>
                      ) : approval.target_user_id ? (
                        <p className="mt-1 text-sm text-[var(--ink-secondary)]">
                          Target: {approval.target_user_id}
                        </p>
                      ) : null}
                      {approval.status === "rejected" && approval.rejection_reason ? (
                        <p className="mt-2 text-sm text-[var(--danger)]">
                          Rejected: {approval.rejection_reason}
                        </p>
                      ) : null}
                    </div>
                    <StatusChip tone={approvalTone(approval.status || "pending")}>
                      {statusLabel(approval.status || "pending")}
                    </StatusChip>
                  </div>

                  {when ? (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-[var(--ink-tertiary)]">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatDate(when)}</span>
                    </div>
                  ) : null}

                  {isPending ? (
                    <div className="mt-4 space-y-3">
                      {!isRejecting ? (
                        <div className="flex flex-wrap gap-2">
                          <HelioButton size="sm" onClick={() => markApproved(approval.approval_id)}>
                            Approve
                          </HelioButton>
                          <HelioButton
                            size="sm"
                            variant="destructive"
                            className="border border-[var(--danger)]/40"
                            onClick={() => {
                              setRejectingId(approval.approval_id);
                              setRejectReason("");
                            }}
                          >
                            Reject
                          </HelioButton>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <label className="block text-sm text-[var(--ink-secondary)]">
                            Why are you rejecting this?
                          </label>
                          <textarea
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            rows={3}
                            placeholder="Describe the reason for rejection…"
                            className="w-full rounded-xl border border-[var(--stroke-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)]"
                          />
                          <div className="flex flex-wrap gap-2">
                            <HelioButton
                              size="sm"
                              variant="destructive"
                              className="border border-[var(--danger)]/40"
                              disabled={!rejectReason.trim()}
                              onClick={() => markRejected(approval.approval_id)}
                            >
                              Confirm reject
                            </HelioButton>
                            <HelioButton
                              size="sm"
                              variant="secondary"
                              onClick={() => {
                                setRejectingId(null);
                                setRejectReason("");
                              }}
                            >
                              Cancel
                            </HelioButton>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}
      </Surface>
    </div>
  );
}
