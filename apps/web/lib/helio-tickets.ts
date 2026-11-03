/**
 * HELIO Tickets UX merges two sources:
 * - Bakery Postgres (guided helpdesk / Others / escalations → INC-*)
 * - Enterprise mock via agent-api (legacy ITSM demo tickets)
 *
 * Source of truth for Get help tickets is bakery DB (not seed JSON).
 */

import { auth, tickets as enterpriseTickets } from "@/lib/api-client";
import { bakery } from "@/lib/bakery-client";
import { resolveBakeryUserId } from "@/lib/helio-bakery-persona";

export type HelioTicket = {
  ticket_id: string;
  summary?: string;
  description?: string;
  status?: string;
  priority?: string;
  category?: string;
  issue_code?: string;
  assigned_team?: string;
  requester?: string;
  created_at?: string;
  updated_at?: string;
  source?: "bakery" | "enterprise";
};

function isBakeryTicketId(ticketId: string): boolean {
  // Bakery generate_id("INC") → INC-XXXXXXXX; enterprise uses tenant-prefixed ids.
  return /^INC-[A-Z0-9]+$/i.test(ticketId);
}

/** Stable past ISO time from ticket id when seed dates are missing/future. */
function pastTimestampFromId(ticketId: string): string {
  let hash = 0;
  for (let i = 0; i < ticketId.length; i++) {
    hash = (hash * 31 + ticketId.charCodeAt(i)) >>> 0;
  }
  const days = 1 + (hash % 60);
  const hours = hash % 24;
  const minutes = Math.floor(hash / 7) % 60;
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - days);
  d.setUTCHours(hours, minutes, 0, 0);
  return d.toISOString();
}

/** Prefer real/past timestamps; never show future seed dates in the Tickets UI. */
function sanitizeTicketTimestamp(
  ticketId: string,
  raw?: string | null
): string | undefined {
  if (!raw) return pastTimestampFromId(ticketId);
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return pastTimestampFromId(ticketId);
  if (parsed.getTime() > Date.now() + 60_000) return pastTimestampFromId(ticketId);
  return parsed.toISOString();
}

async function ensureBakerySession(helioUserId?: string | null): Promise<string> {
  const bakeryUserId = resolveBakeryUserId(helioUserId);
  await bakery.demoLogin(bakeryUserId);
  return bakeryUserId;
}

function normalizeBakeryTicket(t: Record<string, unknown>): HelioTicket {
  const ticketId = String(t.ticket_id);
  return {
    ticket_id: ticketId,
    summary: t.summary as string | undefined,
    description: t.description as string | undefined,
    status: (t.status as string | undefined) || "open",
    priority: t.priority as string | undefined,
    category: (t.category as string | undefined) || (t.issue_code as string | undefined),
    issue_code: t.issue_code as string | undefined,
    assigned_team: t.assigned_team as string | undefined,
    requester: t.requester as string | undefined,
    created_at: sanitizeTicketTimestamp(ticketId, t.created_at as string | undefined),
    updated_at: sanitizeTicketTimestamp(
      ticketId,
      (t.updated_at as string | undefined) || (t.created_at as string | undefined)
    ),
    source: "bakery",
  };
}

function normalizeEnterpriseTicket(t: Record<string, unknown>): HelioTicket {
  const ticketId = String(t.ticket_id);
  const rawCreated =
    (t.created_at as string | undefined) || (t.opened_at as string | undefined);
  return {
    ticket_id: ticketId,
    summary: (t.summary as string | undefined) || (t.title as string | undefined),
    description: t.description as string | undefined,
    status: t.status as string | undefined,
    priority: t.priority as string | undefined,
    category: t.category as string | undefined,
    requester: (t.requester as string | undefined) || (t.requester_id as string | undefined),
    created_at: sanitizeTicketTimestamp(ticketId, rawCreated),
    updated_at: sanitizeTicketTimestamp(
      ticketId,
      (t.updated_at as string | undefined) || rawCreated
    ),
    source: "enterprise",
  };
}

/** List tickets: bakery (guided) first, then enterprise mock; dedupe by ticket_id. */
export async function listHelioTickets(params?: {
  status?: string;
  limit?: number;
}): Promise<{ tickets: HelioTicket[]; count: number }> {
  let helioUserId: string | undefined;
  try {
    const session = await auth.getSession();
    helioUserId = session.user_id || session.persona_key;
  } catch {
    /* bakery login still attempted with default persona */
  }

  let bakeryList: HelioTicket[] = [];
  try {
    await ensureBakerySession(helioUserId);
    const data = await bakery.listMyTickets();
    bakeryList = (data.tickets || []).map((t) =>
      normalizeBakeryTicket(t as unknown as Record<string, unknown>)
    );
  } catch {
    bakeryList = [];
  }

  let enterpriseList: HelioTicket[] = [];
  try {
    const data = await enterpriseTickets.list(params);
    enterpriseList = (data.tickets || []).map((t) =>
      normalizeEnterpriseTicket(t as Record<string, unknown>)
    );
  } catch {
    enterpriseList = [];
  }

  const seen = new Set<string>();
  const merged: HelioTicket[] = [];
  for (const t of [...bakeryList, ...enterpriseList]) {
    if (seen.has(t.ticket_id)) continue;
    seen.add(t.ticket_id);
    merged.push(t);
  }

  merged.sort((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
    return tb - ta;
  });

  let filtered = merged;
  if (params?.status) {
    const want = params.status.toLowerCase();
    filtered = merged.filter((t) => {
      const s = (t.status || "").toLowerCase();
      if (want === "new") return s === "new" || s === "open";
      return s === want;
    });
  }

  const limit = params?.limit;
  const tickets = typeof limit === "number" ? filtered.slice(0, limit) : filtered;
  return { tickets, count: tickets.length };
}

/** Fetch a single ticket from bakery or enterprise based on id shape / fallback. */
export async function getHelioTicket(ticketId: string): Promise<HelioTicket> {
  const preferBakery = isBakeryTicketId(ticketId);

  const tryBakery = async (): Promise<HelioTicket | null> => {
    try {
      let helioUserId: string | undefined;
      try {
        const session = await auth.getSession();
        helioUserId = session.user_id || session.persona_key;
      } catch {
        /* default persona */
      }
      await ensureBakerySession(helioUserId);
      const t = await bakery.getTicket(ticketId);
      return normalizeBakeryTicket(t as unknown as Record<string, unknown>);
    } catch {
      return null;
    }
  };

  const tryEnterprise = async (): Promise<HelioTicket | null> => {
    try {
      const t = await enterpriseTickets.get(ticketId);
      return normalizeEnterpriseTicket(t as Record<string, unknown>);
    } catch {
      return null;
    }
  };

  if (preferBakery) {
    const bakeryTicket = await tryBakery();
    if (bakeryTicket) return bakeryTicket;
    const enterpriseTicket = await tryEnterprise();
    if (enterpriseTicket) return enterpriseTicket;
  } else {
    const enterpriseTicket = await tryEnterprise();
    if (enterpriseTicket) return enterpriseTicket;
    const bakeryTicket = await tryBakery();
    if (bakeryTicket) return bakeryTicket;
  }

  throw new Error("Ticket not found");
}

/** Close/resolve a ticket — bakery PATCH for INC-*, enterprise mock PATCH otherwise. */
export async function resolveOrCloseHelioTicket(
  ticketId: string,
  currentStatus?: string
): Promise<HelioTicket> {
  const status = (currentStatus || "").toLowerCase();
  if (isBakeryTicketId(ticketId)) {
    let helioUserId: string | undefined;
    try {
      const session = await auth.getSession();
      helioUserId = session.user_id || session.persona_key;
    } catch {
      /* default */
    }
    await ensureBakerySession(helioUserId);
    const next = status === "resolved" ? "closed" : "closed";
    const t = await bakery.updateTicketStatus(ticketId, next);
    return normalizeBakeryTicket(t as unknown as Record<string, unknown>);
  }

  // Enterprise mock transitions: in_progress → resolved; most others → closed
  let next = "closed";
  if (status === "in_progress") next = "resolved";
  else if (status === "resolved") next = "closed";
  const t = await enterpriseTickets.patch(ticketId, { status: next });
  return normalizeEnterpriseTicket(t as Record<string, unknown>);
}

export function isClosedStatus(status?: string): boolean {
  const s = (status || "").toLowerCase();
  return s === "closed" || s === "resolved";
}

/** Employee-facing: treat non-closed tickets as in progress. */
export function isActiveStatus(status?: string): boolean {
  return !isClosedStatus(status);
}

export { isBakeryTicketId, ensureBakerySession };
