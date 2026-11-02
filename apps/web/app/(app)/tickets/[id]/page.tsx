"use client";

import { useState, use } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { auth, tickets } from "@/lib/api-client";
import { getHelioTicket, isBakeryTicketId } from "@/lib/helio-tickets";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";
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

/** Mock ITSM transitions (enterprise mock VALID_STATUS_TRANSITIONS). */
function nextStatus(current: string): string | null {
  switch (current) {
    case "new":
      return "triaged";
    case "triaged":
      return "assigned";
    case "assigned":
      return "in_progress";
    case "in_progress":
    case "escalated":
    case "pending_user":
    case "pending_vendor":
      return "resolved";
    default:
      return null;
  }
}

function statusActionLabel(current: string): string {
  switch (current) {
    case "new":
      return "Triage";
    case "triaged":
      return "Assign";
    case "assigned":
      return "Start progress";
    case "in_progress":
    case "escalated":
    case "pending_user":
    case "pending_vendor":
      return "Mark resolved";
    default:
      return "Change status";
  }
}

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
  const s = (status || "").toLowerCase();
  if (["resolved", "closed"].includes(s)) return "success";
  if (["new", "triaged", "assigned"].includes(s)) return "info";
  if (["in_progress", "pending_user", "pending_vendor"].includes(s)) return "warning";
  if (s === "escalated") return "danger";
  return "neutral";
}

export default function TicketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const queryClient = useQueryClient();
  const [commentText, setCommentText] = useState("");
  const [showComment, setShowComment] = useState(false);

  const { data: session } = useQuery({
    queryKey: ["session"],
    queryFn: auth.getSession,
  });

  const canManageTickets = ["it_engineer", "it_manager", "tenant_admin", "security_analyst"].includes(
    session?.role || ""
  );

  const bakeryTicket = isBakeryTicketId(id);

  const { data: ticket, isLoading, isError } = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => getHelioTicket(id),
  });

  const { data: commentsData, refetch: refetchComments } = useQuery({
    queryKey: ["ticket-comments", id],
    queryFn: () => tickets.listComments(id),
    enabled: !!id && !bakeryTicket,
  });

  const comments: Array<{
    comment_id?: string;
    id?: string;
    author?: string;
    author_id?: string;
    creator_id?: string;
    created_at?: string;
    body?: string;
    text?: string;
  }> = Array.isArray(commentsData)
    ? commentsData
    : Array.isArray(ticket?.comments)
      ? ticket.comments
      : [];

  const commentMutation = useMutation({
    mutationFn: (body: string) => tickets.addComment(id, body),
    onSuccess: () => {
      toast.success("Comment added");
      setCommentText("");
      setShowComment(false);
      void queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      void refetchComments();
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to add comment");
    },
  });

  const patchMutation = useMutation({
    mutationFn: (data: { status?: string; priority?: string }) => tickets.patch(id, data),
    onSuccess: () => {
      toast.success("Ticket updated");
      void queryClient.invalidateQueries({ queryKey: ["ticket", id] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
    onError: (error: unknown) => {
      toast.error(error instanceof Error ? error.message : "Failed to update ticket");
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError || !ticket) {
    return (
      <EmptyState
        title="Ticket not found"
        description="This request may have been removed, or the link is incorrect."
        action={
          <Link href="/tickets">
            <HelioButton variant="secondary">Back to tickets</HelioButton>
          </Link>
        }
      />
    );
  }

  const isClosed = ticket.status === "closed" || ticket.status === "resolved";
  const isBakerySource = ticket.source === "bakery" || bakeryTicket;

  return (
    <div className="space-y-8">
      <div className="flex items-start gap-3">
        <Link href="/tickets">
          <HelioButton variant="quiet" size="icon" aria-label="Back to tickets">
            <ArrowLeft className="w-5 h-5" />
          </HelioButton>
        </Link>
        <PageHeader
          className="flex-1"
          eyebrow={ticket.ticket_id}
          title={ticket.summary || ticket.ticket_id}
          actions={
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip tone={priorityTone(ticket.priority)}>{ticket.priority}</StatusChip>
              <StatusChip tone={statusTone(ticket.status)}>{ticket.status}</StatusChip>
            </div>
          }
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Surface className="lg:col-span-2 p-6">
          <Eyebrow>Description</Eyebrow>
          <p className="mt-3 text-sm leading-relaxed whitespace-pre-wrap text-[var(--ink)]">
            {ticket.description}
          </p>

          {comments.length > 0 ? (
            <div className="border-t border-[var(--stroke)] mt-6 pt-5 space-y-3">
              <h3 className="text-sm font-medium text-[var(--ink)]">Comments</h3>
              {comments.map(
                (
                  comment: {
                    comment_id?: string;
                    id?: string;
                    author?: string;
                    author_id?: string;
                    creator_id?: string;
                    created_at?: string;
                    body?: string;
                    text?: string;
                  },
                  idx: number
                ) => (
                  <div
                    key={comment.comment_id || comment.id || idx}
                    className="rounded-xl border border-[var(--stroke)] bg-[var(--surface-soft)] p-3"
                  >
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <span className="text-sm font-medium text-[var(--ink)]">
                        {comment.author || comment.author_id || comment.creator_id || "User"}
                      </span>
                      <span className="text-xs text-[var(--ink-tertiary)]">
                        {comment.created_at ? formatDate(comment.created_at) : ""}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--ink-secondary)]">
                      {comment.body || comment.text}
                    </p>
                  </div>
                )
              )}
            </div>
          ) : null}

          {showComment ? (
            <div className="border-t border-[var(--stroke)] mt-6 pt-5 space-y-3">
              <input
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Add a comment…"
                disabled={commentMutation.isPending}
                className="w-full h-11 rounded-xl border border-[var(--stroke-strong)] bg-[var(--surface)] px-4 text-sm text-[var(--ink)] placeholder:text-[var(--ink-tertiary)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)]"
              />
              <div className="flex gap-2">
                <HelioButton
                  size="sm"
                  disabled={!commentText.trim() || commentMutation.isPending}
                  loading={commentMutation.isPending}
                  onClick={() => commentMutation.mutate(commentText.trim())}
                >
                  Post comment
                </HelioButton>
                <HelioButton
                  size="sm"
                  variant="quiet"
                  onClick={() => {
                    setShowComment(false);
                    setCommentText("");
                  }}
                >
                  Cancel
                </HelioButton>
              </div>
            </div>
          ) : null}
        </Surface>

        <div className="space-y-4">
          <Surface className="p-5">
            <Eyebrow>Details</Eyebrow>
            <dl className="mt-4 space-y-4 text-sm">
              <div>
                <dt className="text-[var(--ink-secondary)] mb-1">Status</dt>
                <dd>
                  <StatusChip tone={statusTone(ticket.status)}>{ticket.status}</StatusChip>
                </dd>
              </div>
              <div>
                <dt className="text-[var(--ink-secondary)] mb-1">Priority</dt>
                <dd>
                  <StatusChip tone={priorityTone(ticket.priority)}>{ticket.priority}</StatusChip>
                </dd>
              </div>
              {ticket.category ? (
                <div>
                  <dt className="text-[var(--ink-secondary)] mb-1">Category</dt>
                  <dd className="font-medium text-[var(--ink)]">{ticket.category}</dd>
                </div>
              ) : null}
              <div>
                <dt className="text-[var(--ink-secondary)] mb-1">Created</dt>
                <dd className="font-medium text-[var(--ink)]">
                  {ticket.created_at ? formatDate(ticket.created_at) : "Timestamp unavailable"}
                </dd>
              </div>
              {ticket.assigned_team ? (
                <div>
                  <dt className="text-[var(--ink-secondary)] mb-1">Assigned team</dt>
                  <dd className="font-medium text-[var(--ink)]">{ticket.assigned_team}</dd>
                </div>
              ) : null}
              {ticket.updated_at ? (
                <div>
                  <dt className="text-[var(--ink-secondary)] mb-1">Updated</dt>
                  <dd className="font-medium text-[var(--ink)]">{formatDate(ticket.updated_at)}</dd>
                </div>
              ) : null}
              {ticket.requester ? (
                <div>
                  <dt className="text-[var(--ink-secondary)] mb-1">Requester</dt>
                  <dd className="font-medium text-[var(--ink)]">{ticket.requester}</dd>
                </div>
              ) : null}
            </dl>
          </Surface>

          <Surface className="p-5">
            <Eyebrow>Actions</Eyebrow>
            <div className="mt-4 space-y-2">
              {isBakerySource ? (
                <p className="text-xs text-[var(--ink-secondary)]">
                  This ticket was raised from Get help and is stored in the bakery ticket database.
                  Status updates for bakery tickets are handled by IT in the guided workflow.
                </p>
              ) : (
                <>
                  <HelioButton
                    variant="secondary"
                    className="w-full"
                    onClick={() => setShowComment(true)}
                    disabled={commentMutation.isPending}
                  >
                    Add comment
                  </HelioButton>
                  {canManageTickets && !isClosed && nextStatus(ticket.status || "") ? (
                    <HelioButton
                      className="w-full"
                      disabled={patchMutation.isPending}
                      loading={patchMutation.isPending}
                      onClick={() => {
                        const next = nextStatus(ticket.status || "");
                        if (next) patchMutation.mutate({ status: next });
                      }}
                    >
                      {statusActionLabel(ticket.status || "")}
                    </HelioButton>
                  ) : null}
                  {canManageTickets && isClosed ? (
                    <HelioButton
                      variant="secondary"
                      className="w-full"
                      disabled={patchMutation.isPending}
                      loading={patchMutation.isPending}
                      onClick={() => patchMutation.mutate({ status: "in_progress" })}
                    >
                      Reopen ticket
                    </HelioButton>
                  ) : null}
                  {!canManageTickets ? (
                    <p className="text-xs text-[var(--ink-secondary)] pt-1">
                      Status changes require an IT role. You can still add comments on your tickets.
                    </p>
                  ) : null}
                </>
              )}
            </div>
          </Surface>
        </div>
      </div>
    </div>
  );
}
