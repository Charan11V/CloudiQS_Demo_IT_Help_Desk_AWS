"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { workspace } from "@/lib/api-client";
import { listHelioTickets } from "@/lib/helio-tickets";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowUpRight, Clock, Laptop } from "lucide-react";
import {
  PageHeader,
  Surface,
  StatusChip,
  HelioButton,
  Skeleton,
  EmptyState,
} from "@/components/helio";
import { GuidedHelpdeskPanel } from "@/components/guided-helpdesk-panel";
import { cn, formatDate } from "@/lib/utils";

function greetingForNow() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function statusTone(status?: string): "success" | "warning" | "danger" | "neutral" | "info" {
  const s = (status || "").toLowerCase();
  if (["resolved", "closed", "active", "assigned", "healthy"].includes(s)) return "success";
  if (["pending", "awaiting", "in_progress"].some((x) => s.includes(x))) return "warning";
  if (["open", "new", "triaged"].includes(s)) return "info";
  if (["failed", "rejected", "blocked"].includes(s)) return "danger";
  return "neutral";
}

export default function OverviewPage() {
  const router = useRouter();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["workspace-summary"],
    queryFn: workspace.getSummary,
  });

  const { data: ticketData } = useQuery({
    queryKey: ["tickets", "home-recent"],
    queryFn: () => listHelioTickets({ limit: 8 }),
  });

  const identity = data?.identity;
  const devices = data?.devices || [];
  const tickets = ticketData?.tickets?.length
    ? ticketData.tickets
    : data?.recent_tickets || [];
  const firstName = useMemo(() => {
    const name = identity?.name || identity?.display_name || "";
    return name.split(/\s/)[0] || "there";
  }, [identity]);

  const openTickets = tickets.filter(
    (t: { status?: string }) => !["closed", "resolved"].includes((t.status || "").toLowerCase())
  );

  const primaryDevice = devices[0];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-48 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <EmptyState
        title="Couldn't load your workspace"
        description="The summary API didn't respond. You can still open Get help."
        action={
          <HelioButton variant="secondary" onClick={() => refetch()}>
            Retry
          </HelioButton>
        }
      />
    );
  }

  return (
    <div className="space-y-6 sm:space-y-10">
      <PageHeader
        eyebrow={`Your workspace · ${new Date().toLocaleString("en-US", { month: "long", year: "numeric" })}`}
        title={`${greetingForNow()}, ${firstName}.`}
        description="Everything you need to keep work moving, in one place."
      />

      {/* Choice-based guided agent (same as Get help) */}
      <div className="h-[min(72vh,820px)] min-h-[520px]">
        <GuidedHelpdeskPanel preferredUserId={identity?.user_id} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Surface className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold tracking-[-0.02em] text-[var(--ink)]">Your requests</h3>
            <Link href="/tickets" className="text-sm font-medium text-[var(--signal)] hover:text-[var(--signal-hover)] hover:underline">
              View all
            </Link>
          </div>
          {openTickets.length === 0 && tickets.length === 0 ? (
            <EmptyState
              title="No requests yet"
              description="When you open a ticket from Get help, it will show up here."
              className="py-8"
            />
          ) : (
            <ul className="space-y-3">
              {(openTickets.length ? openTickets : tickets).slice(0, 5).map(
                (ticket: {
                  ticket_id: string;
                  summary?: string;
                  title?: string;
                  status?: string;
                  created_at?: string;
                }) => (
                  <li key={ticket.ticket_id}>
                    <Link
                      href={`/tickets/${ticket.ticket_id}`}
                      className="flex items-center justify-between gap-3 rounded-xl px-3 py-3 hover:bg-[var(--surface-hover)] transition-colors"
                    >
                      <div className="min-w-0 flex-1">
                        <span className="block text-sm font-medium text-[var(--ink)] truncate">
                          {ticket.summary || ticket.title || ticket.ticket_id}
                        </span>
                        <span className="mt-0.5 inline-flex items-center gap-1 text-xs text-[var(--ink-tertiary)]">
                          <Clock className="h-3 w-3" />
                          {ticket.created_at
                            ? formatDate(ticket.created_at)
                            : "Timestamp unavailable"}
                        </span>
                      </div>
                      <StatusChip tone={statusTone(ticket.status)}>
                        {ticket.status || "open"}
                      </StatusChip>
                    </Link>
                  </li>
                )
              )}
            </ul>
          )}
        </Surface>

        <Surface className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold tracking-[-0.02em] text-[var(--ink)]">My environment</h3>
            <Link href="/devices" className="text-sm font-medium text-[var(--signal)] hover:text-[var(--signal-hover)] hover:underline">
              Devices
            </Link>
          </div>
          {!primaryDevice ? (
            <EmptyState
              title="No devices assigned"
              description="Assigned hardware will appear here when available from the API."
              className="py-8"
            />
          ) : (
            <div>
              <div className="flex items-start gap-3">
                <div className="h-11 w-11 rounded-xl bg-[var(--signal-soft)] flex items-center justify-center text-[var(--signal)]">
                  <Laptop className="h-5 w-5" strokeWidth={1.75} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-[var(--ink)]">
                      {primaryDevice.hostname ||
                        primaryDevice.device_name ||
                        primaryDevice.name ||
                        primaryDevice.device_id}
                    </p>
                    <StatusChip tone={statusTone(primaryDevice.status || primaryDevice.lifecycle)}>
                      {primaryDevice.status || primaryDevice.lifecycle || "assigned"}
                    </StatusChip>
                  </div>
                  <p className="mt-1 text-sm text-[var(--ink-secondary)]">
                    {[
                      primaryDevice.model,
                      primaryDevice.device_type
                        ? String(primaryDevice.device_type).charAt(0).toUpperCase() +
                          String(primaryDevice.device_type).slice(1)
                        : null,
                      primaryDevice.os,
                      primaryDevice.site,
                    ]
                      .filter(Boolean)
                      .join(" · ") || "Corporate device"}
                  </p>
                </div>
              </div>
              <p className="mt-5 text-sm text-[var(--ink-secondary)]">
                Having trouble with this device? CloudiQS Demo agent can guide you through the right next step.
              </p>
              <HelioButton
                variant="secondary"
                size="sm"
                className="mt-4"
                onClick={() => router.push("/support?topic=devices")}
              >
                Troubleshoot
                <ArrowUpRight className="h-3.5 w-3.5" />
              </HelioButton>
              {devices.length > 1 ? (
                <p className={cn("mt-3 text-xs text-[var(--ink-tertiary)]")}>
                  +{devices.length - 1} more assigned device{devices.length > 2 ? "s" : ""}
                </p>
              ) : null}
            </div>
          )}
        </Surface>
      </div>
    </div>
  );
}
