"use client";

import { useQuery } from "@tanstack/react-query";
import { security } from "@/lib/api-client";
import { AlertTriangle } from "lucide-react";
import {
  PageHeader,
  Surface,
  StatusChip,
  EmptyState,
  Skeleton,
  Eyebrow,
} from "@/components/helio";

function severityTone(severity?: string): "danger" | "warning" | "neutral" {
  switch (severity) {
    case "critical":
    case "high":
      return "danger";
    case "medium":
      return "warning";
    default:
      return "neutral";
  }
}

export default function SecurityPage() {
  const { data: findingsData, isLoading, error: findingsError } = useQuery({
    queryKey: ["security-findings"],
    queryFn: security.getFindings,
    retry: false,
  });

  const { data: escalations, error: escError } = useQuery({
    queryKey: ["security-escalations"],
    queryFn: security.listEscalations,
    retry: false,
  });

  if ((findingsError as { status?: number } | null)?.status === 403) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Risk"
          title="Security"
          description="Findings, escalations, and risk reviews for your tenant."
        />
        <Surface>
          <EmptyState
            title="Access restricted"
            description="Security visibility is limited to security and admin roles."
          />
        </Surface>
      </div>
    );
  }

  const findings = findingsData?.findings || [];
  const escList = Array.isArray(escalations) ? escalations : [];
  const highCritical = findings.filter(
    (f: { severity?: string }) => f.severity === "high" || f.severity === "critical"
  ).length;
  const openEscalations =
    (escError as { status?: number } | null)?.status === 403
      ? "-"
      : escList.filter((e: { status?: string }) => e.status === "open").length;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Risk"
        title="Security"
        description="Findings, escalations, and risk reviews for your tenant."
      />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { label: "Total findings", value: findings.length },
          { label: "High / critical", value: highCritical },
          { label: "Open escalations", value: openEscalations },
        ].map((stat) => (
          <Surface key={stat.label} className="p-4">
            <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--ink-secondary)]">
              {stat.label}
            </p>
            <p
              className={`mt-2 text-2xl font-semibold tabular-nums ${
                stat.label === "High / critical" && Number(stat.value) > 0
                  ? "text-[var(--danger)]"
                  : "text-[var(--ink)]"
              }`}
            >
              {stat.value}
            </p>
          </Surface>
        ))}
      </div>

      <Surface className="p-5 sm:p-6">
        <Eyebrow className="mb-4">Security findings</Eyebrow>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : findings.length === 0 ? (
          <EmptyState
            title="No security findings"
            description="Nothing flagged for review right now."
          />
        ) : (
          <ul className="space-y-3">
            {findings.map(
              (finding: {
                finding_id: string;
                title?: string;
                severity?: string;
                kind?: string;
                hris_status?: string;
                user_id?: string;
                employee_id?: string;
                raw?: unknown;
              }) => (
                <li
                  key={finding.finding_id}
                  className="rounded-xl border border-[var(--stroke)] p-4"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <AlertTriangle
                        className={`w-4 h-4 shrink-0 ${
                          finding.severity === "high" || finding.severity === "critical"
                            ? "text-[var(--danger)]"
                            : "text-[var(--warning)]"
                        }`}
                      />
                      <p className="font-medium text-[var(--ink)]">{finding.title}</p>
                    </div>
                    <StatusChip tone={severityTone(finding.severity)}>
                      {finding.severity || "info"}
                    </StatusChip>
                  </div>
                  <p className="text-sm text-[var(--ink-secondary)]">
                    {finding.kind}:{" "}
                    {finding.hris_status || finding.user_id || finding.employee_id}
                  </p>
                  {finding.raw ? (
                    <pre className="mt-2 text-xs text-[var(--ink-tertiary)] font-mono overflow-x-auto">
                      {JSON.stringify(finding.raw, null, 2).substring(0, 150)}…
                    </pre>
                  ) : null}
                </li>
              )
            )}
          </ul>
        )}
      </Surface>

      {(escError as { status?: number } | null)?.status !== 403 && escList.length > 0 ? (
        <Surface className="p-5 sm:p-6">
          <Eyebrow className="mb-4">Escalations</Eyebrow>
          <ul className="space-y-3">
            {escList.map(
              (esc: {
                escalation_id: string;
                reason?: string;
                severity?: string;
                ticket_id?: string;
                created_at?: string;
              }) => (
                <li
                  key={esc.escalation_id}
                  className="rounded-xl border border-[var(--stroke)] p-4"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <p className="font-medium text-sm text-[var(--ink)]">{esc.reason}</p>
                    <StatusChip tone={severityTone(esc.severity)}>
                      {esc.severity || "info"}
                    </StatusChip>
                  </div>
                  <p className="text-xs text-[var(--ink-tertiary)]">
                    {esc.escalation_id}
                    {esc.ticket_id ? ` · ticket ${esc.ticket_id}` : ""}
                    {esc.created_at
                      ? ` · ${new Date(esc.created_at).toLocaleString()}`
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
