"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listHelioTickets, type HelioTicket } from "@/lib/helio-tickets";
import Link from "next/link";
import { Search, Clock } from "lucide-react";
import { formatDate } from "@/lib/utils";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  EmptyState,
  Skeleton,
} from "@/components/helio";

function priorityTone(priority?: string): "danger" | "warning" | "neutral" {
  switch (priority) {
    case "high":
    case "critical":
    case "P1":
    case "P2":
      return "danger";
    case "medium":
    case "P3":
      return "warning";
    default:
      return "neutral";
  }
}

function statusTone(status?: string): "success" | "warning" | "danger" | "info" | "neutral" {
  switch (status) {
    case "resolved":
    case "closed":
      return "success";
    case "in_progress":
    case "pending_user":
    case "pending_vendor":
      return "warning";
    case "escalated":
      return "danger";
    case "new":
    case "open":
    case "triaged":
    case "assigned":
      return "info";
    default:
      return "neutral";
  }
}

function matchesStatusBucket(ticket: HelioTicket, bucket: string): boolean {
  const s = (ticket.status || "").toLowerCase();
  if (bucket === "new") return s === "new" || s === "open";
  return s === bucket;
}

export default function TicketsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["tickets", statusFilter],
    queryFn: () => listHelioTickets({ status: statusFilter }),
  });

  const tickets: HelioTicket[] = data?.tickets || [];
  const filteredTickets = tickets.filter((ticket) =>
    (ticket.summary || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Counts from unfiltered bakery+enterprise merge (refetch without status for chips)
  const { data: allData } = useQuery({
    queryKey: ["tickets", "all-counts"],
    queryFn: () => listHelioTickets(),
  });
  const allTickets: HelioTicket[] = allData?.tickets || tickets;

  const statusCounts = {
    all: allTickets.length,
    new: allTickets.filter((t) => matchesStatusBucket(t, "new")).length,
    in_progress: allTickets.filter((t) => matchesStatusBucket(t, "in_progress")).length,
    resolved: allTickets.filter((t) => matchesStatusBucket(t, "resolved")).length,
  };

  return (
    <div className="space-y-5 sm:space-y-8">
      <PageHeader
        eyebrow="Requests"
        title="Your tickets"
        description="Track support requests you’ve opened and see where each one stands."
        actions={
          <div className="flex w-full sm:w-auto gap-2">
            <HelioButton
              variant="secondary"
              className="w-full sm:w-auto"
              loading={isFetching}
              onClick={() => void refetch()}
            >
              Refresh
            </HelioButton>
            <Link href="/support" className="w-full sm:w-auto">
              <HelioButton className="w-full sm:w-auto">Get help</HelioButton>
            </Link>
          </div>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3">
        {Object.entries(statusCounts).map(([status, count]) => {
          const active = statusFilter === status || (!statusFilter && status === "all");
          return (
            <button
              key={status}
              type="button"
              onClick={() => setStatusFilter(status === "all" ? undefined : status)}
              className={`text-left rounded-2xl border p-3 sm:p-4 min-h-[72px] transition-colors ${
                active
                  ? "border-[var(--signal)] bg-[var(--signal-soft)] shadow-soft"
                  : "border-[var(--stroke)] bg-[var(--surface)] hover:border-[var(--stroke-strong)]"
              }`}
            >
              <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--ink-secondary)]">
                {status.replace("_", " ")}
              </p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-[var(--ink)]">{count}</p>
            </button>
          );
        })}
      </div>

      <Surface className="p-4 sm:p-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--ink-tertiary)]" />
            <input
              placeholder="Search by summary…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-11 rounded-xl border border-[var(--stroke-strong)] bg-[var(--surface)] pl-10 pr-4 text-sm text-[var(--ink)] placeholder:text-[var(--ink-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)]"
            />
          </div>
          {statusFilter ? (
            <HelioButton variant="secondary" onClick={() => setStatusFilter(undefined)}>
              Clear status filter
            </HelioButton>
          ) : null}
        </div>
      </Surface>

      <Surface className="p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--ink)]">
            {filteredTickets.length} {filteredTickets.length === 1 ? "ticket" : "tickets"}
          </h2>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : filteredTickets.length === 0 ? (
          <EmptyState
            title={searchQuery ? "No tickets match your search" : "No tickets yet"}
            description={
              searchQuery
                ? "Try a different keyword or clear the status filter."
                : "When you open a request from Get help, it will show up here."
            }
            action={
              !searchQuery ? (
                <Link href="/support">
                  <HelioButton>Get help</HelioButton>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <ul className="space-y-3">
            {filteredTickets.map((ticket) => (
              <li key={ticket.ticket_id}>
                <Link
                  href={`/tickets/${ticket.ticket_id}`}
                  className="block rounded-xl border border-[var(--stroke)] p-4 hover:border-[var(--signal)] hover:bg-[var(--surface-hover)] transition-colors"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-[var(--ink)] truncate">
                        {ticket.summary || ticket.ticket_id}
                      </p>
                      {ticket.description ? (
                        <p className="mt-1 text-sm text-[var(--ink-secondary)] line-clamp-2">
                          {ticket.description}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex gap-2 shrink-0">
                      {ticket.priority ? (
                        <StatusChip tone={priorityTone(ticket.priority)}>
                          {ticket.priority}
                        </StatusChip>
                      ) : null}
                      <StatusChip tone={statusTone(ticket.status)}>
                        {ticket.status || "open"}
                      </StatusChip>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--ink-tertiary)]">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {ticket.created_at ? formatDate(ticket.created_at) : "Timestamp unavailable"}
                    </span>
                    <span className="font-mono">{ticket.ticket_id}</span>
                    {ticket.category ? (
                      <span className="rounded-lg bg-[var(--surface-soft)] px-2 py-0.5 text-[var(--ink-secondary)]">
                        {ticket.category}
                      </span>
                    ) : null}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Surface>
    </div>
  );
}
