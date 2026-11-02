"use client";

import { useQuery } from "@tanstack/react-query";
import { analytics } from "@/lib/api-client";
import {
  PageHeader,
  Surface,
  EmptyState,
  Eyebrow,
  Skeleton,
} from "@/components/helio";

export default function AnalyticsPage() {
  const { data: ticketAnalytics, error: ticketError, isLoading: ticketsLoading } = useQuery({
    queryKey: ["analytics-tickets"],
    queryFn: analytics.getTickets,
    retry: false,
  });

  const { data: agentRunsData, isLoading: agentLoading } = useQuery({
    queryKey: ["analytics-agent-runs"],
    queryFn: analytics.getAgentRuns,
    retry: false,
  });

  if ((ticketError as { status?: number } | null)?.status === 403) {
    return (
      <div className="space-y-8">
        <PageHeader
          eyebrow="Insights"
          title="Analytics"
          description="Team metrics, incident trends, and operational insights."
        />
        <Surface>
          <EmptyState
            title="Access denied"
            description="You don’t have permission to view analytics. Contact your administrator if you need access."
          />
        </Surface>
      </div>
    );
  }

  const ticketStats = {
    open: ticketAnalytics?.by_status?.new || 0,
    avgResponseTime: ticketAnalytics?.avg_response_time_hours
      ? `${Math.round(ticketAnalytics.avg_response_time_hours)}h`
      : "-",
    agentRuns: agentRunsData?.total_runs || 0,
    automationRate: agentRunsData?.total_runs
      ? Math.round(
          (agentRunsData.total_runs /
            (agentRunsData.total_runs + (ticketAnalytics?.total || 0))) *
            100
        ) + "%"
      : "-",
  };

  const isLoading = ticketsLoading || agentLoading;

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Insights"
        title="Analytics"
        description="Team metrics, incident trends, and operational insights."
      />

      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: "Open tickets", value: ticketStats.open },
            { label: "Avg response time", value: ticketStats.avgResponseTime },
            { label: "Agent runs", value: ticketStats.agentRuns },
            { label: "Automation rate", value: ticketStats.automationRate },
          ].map((stat, i) => (
            <Surface
              key={stat.label}
              className={
                i === 0 ? "p-4 border-0 bg-brand-gradient text-white shadow-raised" : "p-4"
              }
            >
              <p
                className={`text-xs font-medium uppercase tracking-[0.08em] ${
                  i === 0 ? "text-white/80" : "text-[var(--ink-secondary)]"
                }`}
              >
                {stat.label}
              </p>
              <p
                className={`mt-2 text-2xl font-semibold tabular-nums ${
                  i === 0 ? "text-white" : "text-[var(--ink)]"
                }`}
              >
                {stat.value}
              </p>
            </Surface>
          ))}
        </div>
      )}

      <Surface className="p-5 sm:p-6">
        <Eyebrow className="mb-4">Ticket status breakdown</Eyebrow>
        {ticketAnalytics?.by_status ? (
          <ul className="space-y-2">
            {Object.entries(ticketAnalytics.by_status).map(([status, count]) => (
              <li
                key={status}
                className="flex items-center justify-between rounded-xl border border-[var(--stroke)] px-3 py-2.5"
              >
                <span className="capitalize text-sm text-[var(--ink)]">
                  {status.replace(/_/g, " ")}
                </span>
                <span className="font-semibold tabular-nums text-[var(--ink)]">
                  {count as number}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState
            title="No ticket data yet"
            description="Status counts will appear once tickets exist in this tenant."
            className="py-8"
          />
        )}
      </Surface>

      {agentRunsData ? (
        <Surface className="p-5 sm:p-6">
          <Eyebrow className="mb-4">Agent run statistics</Eyebrow>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <p className="text-sm text-[var(--ink-secondary)] mb-2">By status</p>
              {Object.entries(agentRunsData.status_counts || {}).map(([status, count]) => (
                <div key={status} className="flex justify-between py-1.5 text-sm">
                  <span className="capitalize text-[var(--ink)]">{status}</span>
                  <span className="font-semibold tabular-nums text-[var(--ink)]">
                    {count as number}
                  </span>
                </div>
              ))}
            </div>
            <div>
              <p className="text-sm text-[var(--ink-secondary)] mb-2">By mode</p>
              {Object.entries(agentRunsData.mode_counts || {}).map(([mode, count]) => (
                <div key={mode} className="flex justify-between py-1.5 text-sm">
                  <span className="text-[var(--ink)]">{mode}</span>
                  <span className="font-semibold tabular-nums text-[var(--ink)]">
                    {count as number}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Surface>
      ) : null}
    </div>
  );
}
