"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  listHelioTickets,
  type HelioTicket,
  isClosedStatus,
  isActiveStatus,
} from "@/lib/helio-tickets";
import { auth } from "@/lib/api-client";
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

type TicketBucket = "in_progress" | "closed";

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
  switch ((status || "").toLowerCase()) {
    case "resolved":
    case "closed":
      return "success";
    case "in_progress":
    case "pending_user":
    case "pending_vendor":
    case "open":
    case "pending":
      return "warning";
    case "escalated":
      return "danger";
    case "new":
    case "triaged":
    case "assigned":
      return "info";
    default:
      return "neutral";
  }
}

function TicketRow({ ticket }: { ticket: HelioTicket }) {
  return (
    <li>
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
              <StatusChip tone={priorityTone(ticket.priority)}>{ticket.priority}</StatusChip>
            ) : null}
            <StatusChip tone={statusTone(ticket.status)}>
              {isClosedStatus(ticket.status) ? ticket.status || "closed" : "in progress"}
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
  );
}

export default function TicketsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [bucket, setBucket] = useState<TicketBucket>("in_progress");

  const { data: session } = useQuery({
    queryKey: ["session"],
    queryFn: auth.getSession,
  });

  const isIt =
    session?.role === "it_engineer" ||
    session?.role === "it_manager" ||
    session?.role === "tenant_admin" ||
    session?.role === "security_analyst";

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["tickets", "all"],
    queryFn: () => listHelioTickets(),
  });

  const tickets: HelioTicket[] = data?.tickets || [];

  const { inProgressCount, closedCount, visible } = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch = (ticket: HelioTicket) => {
      if (!q) return true;
      return (
        (ticket.summary || "").toLowerCase().includes(q) ||
        (ticket.ticket_id || "").toLowerCase().includes(q)
      );
    };

    const inProgressAll = tickets.filter((t) => isActiveStatus(t.status));
    const closedAll = tickets.filter((t) => isClosedStatus(t.status));
    const pool = bucket === "in_progress" ? inProgressAll : closedAll;

    return {
      inProgressCount: inProgressAll.length,
      closedCount: closedAll.length,
      visible: pool.filter(matchesSearch),
    };
  }, [tickets, searchQuery, bucket]);

  return (
    <div className="space-y-5 sm:space-y-8">
      <PageHeader
        eyebrow="Requests"
        title={isIt ? "Tickets" : "Your tickets"}
        description={
          isIt
            ? "Switch between In progress and Closed. Open a ticket to resolve or close it."
            : "Switch between In progress and Closed to see where your requests stand."
        }
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

      <div
        className="grid grid-cols-2 gap-2 sm:gap-3 max-w-lg"
        role="tablist"
        aria-label="Ticket status"
      >
        <button
          type="button"
          role="tab"
          aria-selected={bucket === "in_progress"}
          onClick={() => setBucket("in_progress")}
          className={`text-left rounded-2xl border p-3 sm:p-4 min-h-[72px] transition-colors ${
            bucket === "in_progress"
              ? "border-[var(--signal)] bg-[var(--signal-soft)] shadow-soft"
              : "border-[var(--stroke)] bg-[var(--surface)] hover:border-[var(--stroke-strong)]"
          }`}
        >
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--ink-secondary)]">
            In progress
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-[var(--ink)]">
            {inProgressCount}
          </p>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={bucket === "closed"}
          onClick={() => setBucket("closed")}
          className={`text-left rounded-2xl border p-3 sm:p-4 min-h-[72px] transition-colors ${
            bucket === "closed"
              ? "border-[var(--signal)] bg-[var(--signal-soft)] shadow-soft"
              : "border-[var(--stroke)] bg-[var(--surface)] hover:border-[var(--stroke-strong)]"
          }`}
        >
          <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--ink-secondary)]">
            Closed
          </p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-[var(--ink)]">
            {closedCount}
          </p>
        </button>
      </div>

      <Surface className="p-4 sm:p-5">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--ink-tertiary)]" />
          <input
            placeholder="Search by summary or ticket id…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-11 rounded-xl border border-[var(--stroke-strong)] bg-[var(--surface)] pl-10 pr-4 text-sm text-[var(--ink)] placeholder:text-[var(--ink-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)]"
          />
        </div>
      </Surface>

      <Surface className="p-5 sm:p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold tracking-[-0.02em] text-[var(--ink)]">
            {bucket === "in_progress" ? "In progress" : "Closed"}
            <span className="ml-2 text-sm font-normal text-[var(--ink-tertiary)] tabular-nums">
              ({visible.length})
            </span>
          </h2>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : visible.length === 0 ? (
          <EmptyState
            title={
              searchQuery
                ? "No tickets match your search"
                : bucket === "in_progress"
                  ? "Nothing in progress"
                  : "No closed tickets"
            }
            description={
              searchQuery
                ? "Try a different keyword, or switch In progress / Closed."
                : bucket === "in_progress"
                  ? "Open tickets will appear here until IT resolves them."
                  : "Resolved and closed tickets show up when you select Closed."
            }
            action={
              !searchQuery && bucket === "in_progress" ? (
                <Link href="/support">
                  <HelioButton>Get help</HelioButton>
                </Link>
              ) : undefined
            }
          />
        ) : (
          <ul className="space-y-3">
            {visible.map((ticket) => (
              <TicketRow key={ticket.ticket_id} ticket={ticket} />
            ))}
          </ul>
        )}
      </Surface>
    </div>
  );
}
