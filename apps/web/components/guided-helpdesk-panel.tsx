"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { bakery, type BakeryConversation, type BakeryOption } from "@/lib/bakery-client";
import { resolveBakeryUserId } from "@/lib/helio-bakery-persona";
import { HelioButton, Surface, StatusChip, EmptyState, HelioLogo } from "@/components/helio";
import {
  Loader2,
  Send,
  CheckCircle2,
  Ticket,
  RotateCcw,
  ArrowLeft,
  HelpCircle,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { cn, formatDate } from "@/lib/utils";
import { RichText } from "@/components/rich-text";

type Props = {
  /** HELIO EMP id / persona key, or a Bakery user_id (NS-xxx / BC-xxx). Mapped before demo-login. */
  preferredUserId?: string;
  /** Free-text issue from home; classified by bakery into guided flow or ticket consent. */
  initialPrefill?: string | null;
  /** Root category shortcut: identity | network | devices */
  initialTopic?: string | null;
};

const TICKET_OPTION_IDS = new Set([
  "open_ticket",
  "confirm_raise_ticket",
  "still_failing",
]);

function optionLooksLikeTicket(option: BakeryOption): boolean {
  const id = (option.id || "").toLowerCase();
  const label = (option.label || "").toLowerCase();
  if (TICKET_OPTION_IDS.has(id)) return true;
  if (label.includes("raise") && label.includes("ticket")) return true;
  if (label.includes("open") && label.includes("ticket")) return true;
  return false;
}

function optionsOfferTicket(options: BakeryOption[] | undefined | null): boolean {
  return (options || []).some(optionLooksLikeTicket);
}

function optionIsOthers(option: BakeryOption): boolean {
  const id = (option.id || "").toLowerCase();
  const label = (option.label || "").trim().toLowerCase();
  const type = (option.type || "").toLowerCase();
  if (id === "cant_find" || id === "others") return true;
  if (label === "others") return true;
  if (type === "fallback" && label.includes("other")) return true;
  return false;
}

const TOPIC_TO_OPTION: Record<string, string> = {
  identity: "identity",
  account: "identity",
  network: "network",
  vpn: "network",
  devices: "device",
  device: "device",
  laptop: "device",
};

const QUICK_TOPIC_LABEL: Record<string, string> = {
  identity: "Account & access",
  account: "Account & access",
  network: "VPN / network",
  vpn: "VPN / network",
  devices: "Device issue",
  device: "Device issue",
  laptop: "Device issue",
};

type TranscriptEntry = {
  id: string;
  role: "assistant" | "user" | "system";
  content: string;
  finding?: BakeryConversation["finding"];
  action_proposal?: BakeryConversation["action_proposal"];
  ticket?: BakeryConversation["ticket"];
};

const CONTROL_META: Record<string, { label: string; icon?: typeof ArrowLeft }> = {
  back: { label: "Back", icon: ArrowLeft },
  start_over: { label: "Start over", icon: RotateCcw },
  something_else: { label: "Something else", icon: HelpCircle },
  talk_to_it: { label: "Talk to IT" },
  cancel: { label: "Cancel" },
};

function uid() {
  return `t-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function assistantEntry(conv: BakeryConversation): TranscriptEntry {
  return {
    id: uid(),
    role: "assistant",
    content: conv.assistant_message || "",
    finding: conv.finding,
    action_proposal: conv.action_proposal,
    ticket: conv.ticket,
  };
}

type ChatDraft = {
  conversationId: string;
  conversation: BakeryConversation | null;
  transcript: TranscriptEntry[];
  journey: string[];
  selectedIds: string[];
  freeText: string;
  seedApplied?: boolean;
  savedAt?: number;
};

const LAST_DRAFT_KEY = "helio.bakery.chatDraft.v2.last";

function storageKey(bakeryUserId: string) {
  return `helio.bakery.chatDraft.v2.${bakeryUserId}`;
}

function legacyConversationKey(bakeryUserId: string) {
  return `helio.bakery.activeConversation.${bakeryUserId}`;
}

function readChatDraft(bakeryUserId: string): ChatDraft | null {
  if (typeof window === "undefined") return null;
  try {
    const keys = [storageKey(bakeryUserId), LAST_DRAFT_KEY];
    for (const key of keys) {
      const raw = window.localStorage.getItem(key);
      if (!raw) continue;
      const parsed = JSON.parse(raw) as ChatDraft;
      if (parsed?.conversationId) return parsed;
    }
    // Migrate older id-only key
    const legacyId =
      window.localStorage.getItem(legacyConversationKey(bakeryUserId)) ||
      window.localStorage.getItem("helio.bakery.activeConversation");
    if (legacyId) {
      return {
        conversationId: legacyId,
        conversation: null,
        transcript: [],
        journey: [],
        selectedIds: [],
        freeText: "",
      };
    }
  } catch {
    /* ignore */
  }
  return null;
}

function writeChatDraft(bakeryUserId: string, draft: ChatDraft) {
  if (typeof window === "undefined") return;
  try {
    const payload = JSON.stringify({ ...draft, savedAt: Date.now() });
    window.localStorage.setItem(storageKey(bakeryUserId), payload);
    window.localStorage.setItem(LAST_DRAFT_KEY, payload);
    window.localStorage.setItem(legacyConversationKey(bakeryUserId), draft.conversationId);
    window.localStorage.setItem("helio.bakery.activeConversation", draft.conversationId);
  } catch {
    /* ignore quota */
  }
}

function clearChatDraft(bakeryUserId: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(storageKey(bakeryUserId));
    window.localStorage.removeItem(LAST_DRAFT_KEY);
    window.localStorage.removeItem(legacyConversationKey(bakeryUserId));
    window.localStorage.removeItem("helio.bakery.activeConversation");
  } catch {
    /* ignore */
  }
}

function transcriptFromMessages(
  messages: BakeryConversation["messages"] | undefined,
  fallback: BakeryConversation
): TranscriptEntry[] {
  const rows = messages || [];
  if (!rows.length) {
    return fallback.assistant_message ? [assistantEntry(fallback)] : [];
  }
  return rows
    .filter((m) => m.role === "user" || m.role === "assistant")
    .filter((m) => !(m.role === "user" && (m.content || "").startsWith("Control:")))
    .map((m) => ({
      id: m.message_id || uid(),
      role: m.role as "user" | "assistant",
      content: m.content || "",
      ...(m.role === "assistant" && m === rows[rows.length - 1]
        ? {
            finding: fallback.finding,
            action_proposal: fallback.action_proposal,
            ticket: fallback.ticket,
          }
        : {}),
    }));
}

export function GuidedHelpdeskPanel({
  preferredUserId,
  initialPrefill,
  initialTopic,
}: Props) {
  const queryClient = useQueryClient();
  const mappedBakeryUserId = resolveBakeryUserId(preferredUserId);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [conversation, setConversation] = useState<BakeryConversation | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [error, setError] = useState("");
  const [persona, setPersona] = useState(mappedBakeryUserId);
  const [journey, setJourney] = useState<string[]>([]);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const seedApplied = useRef(false);
  const bootedBakeryUserId = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const invalidateTicketViews = () => {
    void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    void queryClient.invalidateQueries({ queryKey: ["workspace-summary"] });
  };

  const appendAssistant = (conv: BakeryConversation) => {
    setTranscript((prev) => [...prev, assistantEntry(conv)]);
  };

  const boot = async (userId: string) => {
    // Never send HELIO EMP / persona keys to bakery demo-login
    const bakeryUserId = resolveBakeryUserId(userId);
    setPersona(bakeryUserId);
    bootedBakeryUserId.current = bakeryUserId;
    setLoading(true);
    setError("");
    seedApplied.current = false;
    try {
      await bakery.demoLogin(bakeryUserId);

      // Refresh restores full draft (chat + typed text + selections); Start over clears it.
      // Never create a new welcome chat while an in-progress draft/active chat exists.
      const draft = readChatDraft(bakeryUserId);
      let conv: BakeryConversation | null = null;
      let resumeError = "";
      if (draft?.conversationId) {
        try {
          conv = await bakery.resumeConversation(draft.conversationId);
        } catch (e) {
          resumeError = e instanceof Error ? e.message : "resume failed";
          conv = null;
        }
      }
      if (!conv) {
        try {
          conv = await bakery.getActiveConversation();
        } catch {
          conv = null;
        }
      }
      // Only start fresh when there is truly nothing to resume
      if (!conv) {
        if (draft?.conversation && draft.conversationId) {
          // Offline/API glitch: keep local draft UI rather than wiping to main menu
          conv = {
            ...draft.conversation,
            conversation_id: draft.conversationId,
            resumed: true,
          };
        } else {
          conv = await bakery.createConversation();
        }
      }
      if (resumeError && conv?.resumed) {
        // keep going with active/local draft
      }

      const serverTranscript = transcriptFromMessages(conv.messages, conv);
      const sameChat = Boolean(draft && draft.conversationId === conv.conversation_id);
      // Prefer richer local transcript if present; otherwise rebuild from server messages
      const restoredTranscript =
        sameChat && (draft!.transcript?.length || 0) >= serverTranscript.length
          ? draft!.transcript
          : serverTranscript.length
            ? serverTranscript
            : sameChat && draft?.transcript?.length
              ? draft.transcript
              : serverTranscript;
      const optionIds = new Set((conv.options || []).map((o) => o.id));
      const restoredSelected = sameChat
        ? (draft!.selectedIds || []).filter((id) => optionIds.has(id))
        : [];
      const restoredText = sameChat ? draft!.freeText || "" : "";
      const restoredJourney =
        sameChat && draft!.journey?.length
          ? draft!.journey
          : ((conv.breadcrumb || []).filter(Boolean) as string[]);

      // Server snapshot owns options/state; local draft owns in-progress text/selections/transcript
      setConversation(conv);
      setTranscript(restoredTranscript);
      setJourney(restoredJourney);
      setSelectedIds(restoredSelected);
      setFreeText(restoredText);
      if (
        sameChat ||
        conv.resumed ||
        (conv.messages && conv.messages.length > 1) ||
        draft?.seedApplied
      ) {
        seedApplied.current = true;
      }
      writeChatDraft(bakeryUserId, {
        conversationId: conv.conversation_id,
        conversation: conv,
        transcript: restoredTranscript,
        journey: restoredJourney,
        selectedIds: restoredSelected,
        freeText: restoredText,
        seedApplied: seedApplied.current,
      });
      setReady(true);
    } catch (e) {
      const raw = e instanceof Error ? e.message : "Failed to start guided helpdesk";
      const msg = typeof raw === "string" ? raw : "Bakery guided API unavailable";
      setError(msg);
      setReady(false);
      toast.error("Guided helpdesk unavailable", {
        description: "Choice menu could not start. Retry, or use freeform Get help as a backup.",
      });
    } finally {
      setLoading(false);
    }
  };

  // Boot (and re-boot) when the mapped Bakery persona changes — e.g. env identity loads late.
  useEffect(() => {
    if (bootedBakeryUserId.current === mappedBakeryUserId) return;
    void boot(mappedBakeryUserId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mappedBakeryUserId]);

  // Apply home prefill / topic once conversation is ready
  useEffect(() => {
    if (!ready || !conversation || sending || seedApplied.current) return;
    const topicKey = (initialTopic || "").toLowerCase();
    const optionId = TOPIC_TO_OPTION[topicKey];
    const prefill = (initialPrefill || "").trim();

    if (!optionId && !prefill) return;
    seedApplied.current = true;

    void (async () => {
      setSending(true);
      setError("");
      try {
        if (optionId) {
          const next = await bakery.sendTurn(conversation.conversation_id, {
            option_id: optionId,
          });
          applyNext(next, QUICK_TOPIC_LABEL[topicKey] || optionId);
        } else if (prefill) {
          const next = await bakery.sendTurn(conversation.conversation_id, {
            free_text: prefill,
          });
          applyNext(next, prefill);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not continue from your description");
        seedApplied.current = false;
      } finally {
        setSending(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, conversation?.conversation_id, initialPrefill, initialTopic]);

  useEffect(() => {
    const crumbs = (conversation?.breadcrumb || []).filter(Boolean) as string[];
    if (crumbs.length) setJourney(crumbs);
  }, [conversation?.breadcrumb]);

  // Persist full UI draft so refresh keeps text, selections, and history
  useEffect(() => {
    if (!ready || !conversation?.conversation_id) return;
    writeChatDraft(persona || mappedBakeryUserId, {
      conversationId: conversation.conversation_id,
      conversation,
      transcript,
      journey,
      selectedIds,
      freeText,
      seedApplied: seedApplied.current,
    });
  }, [
    ready,
    persona,
    mappedBakeryUserId,
    conversation,
    transcript,
    journey,
    selectedIds,
    freeText,
  ]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [transcript, conversation?.options, conversation?.finding, conversation?.ticket, sending]);

  const selectionMode: "single" | "multiple" =
    conversation?.selection_mode === "multiple" ? "multiple" : "single";

  const isRoot =
    !conversation?.breadcrumb?.filter(Boolean).length &&
    (conversation?.state === "WELCOME" || !conversation?.state);

  const toggleOption = (id: string) => {
    setSelectedIds((prev) => {
      const next =
        selectionMode === "single"
          ? prev.includes(id)
            ? []
            : [id]
          : prev.includes(id)
            ? prev.filter((x) => x !== id)
            : [...prev, id];
      const stillOthers = (conversation?.options || []).some(
        (o) => next.includes(o.id) && optionIsOthers(o)
      );
      if (!stillOthers) setFreeText("");
      return next;
    });
  };

  const applyNext = (next: BakeryConversation, userContent?: string) => {
    setTranscript((prev) => {
      const nextEntries = [...prev];
      if (userContent) {
        nextEntries.push({ id: uid(), role: "user", content: userContent });
      }
      if (next.assistant_message) {
        nextEntries.push(assistantEntry(next));
      }
      return nextEntries;
    });
    setConversation(next);
    // Clear draft inputs after a committed turn (not on refresh)
    setSelectedIds([]);
    setFreeText("");
    if (next.ticket?.ticket_id) {
      invalidateTicketViews();
      toast.success(`Ticket ${next.ticket.ticket_id} raised`, {
        description: next.ticket.created_at
          ? `Opened ${formatDate(next.ticket.created_at)}`
          : next.ticket.summary || "Visible under Your tickets",
      });
    }
  };

  const confirmSelection = async () => {
    if (!conversation || selectedIds.length === 0) return;
    const labels = (conversation.options || [])
      .filter((o) => selectedIds.includes(o.id))
      .map((o) => o.label);
    const selectedOpts = (conversation.options || []).filter((o) =>
      selectedIds.includes(o.id)
    );
    const complaint = freeText.trim();
    const othersSelected = selectedOpts.some(optionIsOthers);
    if (othersSelected && !complaint) return;
    const attachComplaint =
      (Boolean(complaint) && selectedOpts.some(optionLooksLikeTicket)) ||
      othersSelected;
    const userContent =
      othersSelected
        ? complaint
        : attachComplaint
          ? `${labels.join(", ")}: ${complaint}`
          : labels.join(", ");
    setSending(true);
    setError("");
    try {
      const next = await bakery.sendTurn(conversation.conversation_id, {
        option_id: selectedIds[0],
        option_ids: selectedIds,
        ...(attachComplaint ? { free_text: complaint } : {}),
      });
      if (attachComplaint) setFreeText("");
      if (labels.length) {
        setJourney((j) => {
          const nextJ = [...j];
          labels.forEach((l) => {
            if (!nextJ.includes(l)) nextJ.push(l);
          });
          return nextJ;
        });
      }
      applyNext(next, userContent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setSending(false);
    }
  };

  const sendFreeText = async () => {
    if (!conversation || !freeText.trim()) return;
    const text = freeText.trim();
    setSending(true);
    setError("");
    try {
      const next = await bakery.sendTurn(conversation.conversation_id, {
        free_text: text,
      });
      setFreeText("");
      applyNext(next, text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Send failed");
    } finally {
      setSending(false);
    }
  };

  const sendControl = async (control: string) => {
    if (!conversation) return;
    setSending(true);
    setError("");
    try {
      const next = await bakery.sendTurn(conversation.conversation_id, { control });
      if (control === "start_over") {
        // Start over is the only path that resets to a clean chat
        const uidKey = persona || mappedBakeryUserId;
        clearChatDraft(uidKey);
        setJourney([]);
        setTranscript(next.assistant_message ? [assistantEntry(next)] : []);
        setConversation(next);
        setSelectedIds([]);
        setFreeText("");
        seedApplied.current = true;
        writeChatDraft(uidKey, {
          conversationId: next.conversation_id,
          conversation: next,
          transcript: next.assistant_message ? [assistantEntry(next)] : [],
          journey: [],
          selectedIds: [],
          freeText: "",
          seedApplied: true,
        });
      } else if (control === "back") {
        setJourney([]);
        applyNext(
          next,
          CONTROL_META[control]?.label || control.replace(/_/g, " ")
        );
      } else {
        applyNext(
          next,
          CONTROL_META[control]?.label || control.replace(/_/g, " ")
        );
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Control failed");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <Surface className="p-10 flex flex-col items-center gap-3 h-full min-h-[50vh]">
        <Loader2 className="h-5 w-5 animate-spin text-[var(--signal)]" />
        <p className="text-sm text-[var(--ink-secondary)]">Starting guided helpdesk…</p>
      </Surface>
    );
  }

  if (!ready || !conversation) {
    return (
      <Surface className="p-6 space-y-4">
        <EmptyState
          title="Guided session not ready"
          description={
            error
              ? `${error} The choice-based helpdesk needs bakery-api. Retry in a moment.`
              : "Starting the choice-based helpdesk failed. Retry, or open freeform as a backup."
          }
        />
        <div className="flex flex-wrap gap-2 justify-center">
          <HelioButton
            variant="primary"
            onClick={() => void boot(persona || mappedBakeryUserId)}
          >
            Retry guided
          </HelioButton>
          <HelioButton
            variant="secondary"
            size="sm"
            onClick={() => {
              window.location.assign("/support?mode=describe");
            }}
          >
            Freeform backup
          </HelioButton>
        </div>
      </Surface>
    );
  }

  const sessionLocked =
    Boolean(conversation.session_locked) || conversation.state === "CLOSED";
  const options = sessionLocked ? [] : conversation.options || [];
  const selectedOpts = options.filter((o) => selectedIds.includes(o.id));
  const othersSelected = selectedOpts.some(optionIsOthers);
  const allowFreeText =
    !sessionLocked &&
    (Boolean(conversation.allow_free_text) ||
      conversation.state === "DESCRIBING_OTHER" ||
      conversation.state === "AWAITING_TICKET_DETAILS" ||
      conversation.state === "AWAITING_UNKNOWN_TICKET_CONFIRM" ||
      optionsOfferTicket(options));
  const confirmLabel =
    selectionMode === "multiple" && selectedIds.length > 0
      ? `Continue (${selectedIds.length} selected)`
      : conversation.confirm_label || "Confirm selection";
  const freeTextHint =
    conversation.free_text_hint || "Enter your complaint…";
  const freeTextSubmitLabel =
    conversation.free_text_submit_label ||
    (conversation.state === "DESCRIBING_OTHER"
      ? "Send"
      : conversation.free_text_submit_label || "Raise ticket");
  /** Compact complaint box under ticket options, or under the ask when options are empty. */
  const showComplaintUnderOptions =
    allowFreeText && options.length > 0 && !othersSelected;
  const showComplaintUnderAssistant = allowFreeText && options.length === 0;
  const confirmDisabled =
    sending ||
    selectedIds.length === 0 ||
    (othersSelected && !freeText.trim());

  const complaintComposer =
    showComplaintUnderOptions || showComplaintUnderAssistant ? (
      <div className="flex gap-2 items-center max-w-[95%] sm:max-w-[85%]">
        <input
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void sendFreeText()}
          placeholder={freeTextHint}
          disabled={sending}
          aria-label={freeTextHint}
          className="flex-1 min-w-0 h-9 rounded-lg border border-[var(--stroke-strong)] bg-[var(--surface)] px-3 text-sm text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)] focus:border-transparent shadow-soft"
        />
        <HelioButton
          className="h-9 shrink-0 px-3 text-sm"
          size="sm"
          onClick={() => void sendFreeText()}
          disabled={sending || !freeText.trim()}
          aria-label={freeTextSubmitLabel}
        >
          <Send className="h-3.5 w-3.5" />
          <span className="hidden sm:inline ml-1.5">{freeTextSubmitLabel}</span>
        </HelioButton>
      </div>
    ) : null;

  const crumbLabel =
    (conversation.breadcrumb?.filter(Boolean).length
      ? conversation.breadcrumb.filter(Boolean)
      : journey
    ).join(" › ") || "Get help";

  return (
    <div className="flex flex-col h-full min-h-0 overflow-hidden rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] shadow-raised">
      {/* Gradient agent header */}
      <div className="shrink-0 bg-brand-gradient text-white px-4 sm:px-6 py-4 sm:py-5">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-2xl bg-white/20 backdrop-blur-sm flex items-center justify-center shrink-0">
            <HelioLogo size={22} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base sm:text-lg font-semibold tracking-[-0.02em]">
                CloudiQS Demo agent
              </h2>
              <span className="inline-flex items-center gap-1 rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" aria-hidden />
                Connected
              </span>
            </div>
            <p className="text-sm text-white/85 mt-0.5 truncate">
              IT assistant · guided diagnosis &amp; tickets
            </p>
            <p className="text-[11px] text-white/70 mt-1.5 truncate flex items-center gap-1">
              <Sparkles className="h-3 w-3 shrink-0" />
              {crumbLabel}
            </p>
          </div>
          <HelioButton
            variant="secondary"
            size="sm"
            className="bg-white/15 border-white/30 text-white hover:bg-white/25 hover:border-white/40 shrink-0"
            onClick={() => void sendControl("start_over")}
            disabled={sending}
            aria-label="Start over"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Start over</span>
          </HelioButton>
        </div>
      </div>

      {/* Only this transcript area scrolls */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-4 sm:px-6 py-4 sm:py-5 space-y-4 bg-[var(--canvas)]"
      >
        {transcript.map((entry) => (
          <div
            key={entry.id}
            className={cn(
              "flex",
              entry.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            {entry.role === "user" ? (
              <div className="max-w-[85%] sm:max-w-[70%] rounded-2xl rounded-br-md bg-brand-gradient text-white px-4 py-2.5 text-sm whitespace-pre-wrap break-words shadow-soft">
                <RichText text={entry.content} />
              </div>
            ) : entry.role === "system" ? (
              <p className="text-xs text-[var(--ink-tertiary)] w-full text-center py-1">
                <RichText text={entry.content} />
              </p>
            ) : (
              <div className="max-w-[95%] sm:max-w-[85%] space-y-3">
                <div className="rounded-2xl rounded-bl-md bg-[var(--surface)] border border-[var(--stroke)] px-4 py-3 text-sm text-[var(--ink)] whitespace-pre-wrap break-words leading-relaxed shadow-soft">
                  <RichText text={entry.content} />
                </div>
                {entry.finding && (
                  <div className="rounded-2xl border border-[var(--warning)]/25 bg-[var(--warning-soft)] p-3.5 shadow-soft">
                    <div className="space-y-2 text-sm min-w-0">
                      <p className="font-semibold text-[var(--ink)]">Note:</p>
                      {entry.finding.hypothesis && (
                        <p>
                          <span className="text-[var(--ink-tertiary)] text-xs uppercase tracking-wide">
                            Likely cause ·{" "}
                          </span>
                          {entry.finding.hypothesis}
                        </p>
                      )}
                      {entry.finding.observations?.map((o, i) => (
                        <p key={i} className="text-xs font-mono text-[var(--ink-secondary)]">
                          <span className="text-[var(--ink-tertiary)]">{o.field}:</span>{" "}
                          {String(o.value)}{" "}
                          <span className="text-[var(--ink-tertiary)]">({o.source})</span>
                        </p>
                      ))}
                    </div>
                  </div>
                )}
                {entry.action_proposal && (
                  <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-3.5 text-sm shadow-soft">
                    <p className="font-semibold text-[var(--ink)] mb-1">
                      <span className="font-semibold">Note:</span> Suggested fix: review required
                    </p>
                    <p className="text-[var(--ink-secondary)]">
                      {entry.action_proposal.description || entry.action_proposal.action_code}
                    </p>
                  </div>
                )}
                {entry.ticket && (
                  <div className="rounded-2xl border border-[var(--signal)]/30 bg-[var(--signal-soft)] p-3.5 text-sm shadow-soft">
                    <div className="flex gap-2.5">
                      <Ticket className="h-4 w-4 text-[var(--signal)] mt-0.5" />
                      <div>
                        <p className="font-semibold text-[var(--ink)]">
                          Ticket {entry.ticket.ticket_id}
                        </p>
                        <p className="text-[var(--ink-secondary)] mt-0.5">
                          Status: {entry.ticket.status}
                          {entry.ticket.assigned_team
                            ? ` · ${entry.ticket.assigned_team}`
                            : ""}
                        </p>
                        {entry.ticket.created_at ? (
                          <p className="text-[var(--ink-tertiary)] mt-0.5 text-xs">
                            Opened {formatDate(entry.ticket.created_at)}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {showComplaintUnderAssistant && !sending ? (
          <div className="pt-0.5">{complaintComposer}</div>
        ) : null}

        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-[var(--surface)] border border-[var(--stroke)] px-4 py-3 text-sm text-[var(--ink-secondary)] flex items-center gap-2 shadow-soft">
              <Loader2 className="h-4 w-4 animate-spin text-[var(--signal)]" />
              Investigating…
            </div>
          </div>
        )}

        {options.length > 0 && !sending && (
          <div className="space-y-3 pt-1">
            <div className="flex items-center justify-between gap-2">
              <p className="text-xs font-medium text-[var(--ink-secondary)]">
                {conversation.selection_hint ||
                  (selectionMode === "multiple"
                    ? "Select all that apply, then continue."
                    : "Select one option, then Confirm.")}
              </p>
              <StatusChip tone="signal" className="uppercase text-[10px]">
                {selectionMode}
              </StatusChip>
            </div>
            <div
              className={cn(
                "grid gap-2.5",
                isRoot || options.length >= 4 ? "grid-cols-1 md:grid-cols-2" : "grid-cols-1"
              )}
            >
              {options.map((option: BakeryOption) => {
                const checked = selectedIds.includes(option.id);
                return (
                  <button
                    key={option.id}
                    type="button"
                    disabled={sending}
                    onClick={() => toggleOption(option.id)}
                    className={cn(
                      "group flex items-start gap-3 rounded-2xl border px-3.5 sm:px-4 py-3.5 min-h-[52px] text-left transition-all",
                      checked
                        ? "border-[var(--signal)] bg-[var(--signal-soft)] shadow-soft ring-2 ring-[var(--signal)]/15"
                        : "border-[var(--stroke)] bg-[var(--surface)] hover:border-[var(--signal)]/40 hover:shadow-soft",
                      sending && "opacity-50 pointer-events-none"
                    )}
                  >
                    <span
                      className={cn(
                        "mt-0.5 h-4 w-4 shrink-0 rounded-full border flex items-center justify-center",
                        selectionMode === "multiple" && "rounded-md",
                        checked
                          ? "border-[var(--signal)] bg-[var(--signal)]"
                          : "border-[var(--stroke-strong)]"
                      )}
                      aria-hidden
                    >
                      {checked ? (
                        <CheckCircle2 className="h-3 w-3 text-white" strokeWidth={2.5} />
                      ) : null}
                    </span>
                    <span className="flex-1 text-sm font-semibold text-[var(--ink)] leading-snug">
                      {option.label}
                    </span>
                    {isRoot ? (
                      <ArrowRight className="h-4 w-4 text-[var(--signal)] opacity-0 group-hover:opacity-100 transition-opacity" />
                    ) : null}
                  </button>
                );
              })}
            </div>
            {showComplaintUnderOptions ? complaintComposer : null}
            {othersSelected ? (
              <div className="space-y-1.5 max-w-[95%] sm:max-w-[85%]">
                <label
                  htmlFor="others-problem-description"
                  className="text-xs font-medium text-[var(--ink-secondary)]"
                >
                  Describe your problem
                </label>
                <textarea
                  id="others-problem-description"
                  value={freeText}
                  onChange={(e) => setFreeText(e.target.value)}
                  placeholder="Describe your problem…"
                  disabled={sending}
                  rows={3}
                  aria-label="Describe your problem"
                  className="w-full rounded-lg border border-[var(--stroke-strong)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--signal)] focus:border-transparent shadow-soft resize-y min-h-[72px]"
                />
              </div>
            ) : null}
          </div>
        )}

        <div ref={bottomRef} className="h-px shrink-0" />
      </div>

      {/* Footer — confirm + controls only (complaint box lives in transcript) */}
      <div className="shrink-0 border-t border-[var(--stroke)] px-4 sm:px-6 py-3 sm:py-4 space-y-3 bg-[var(--surface)] pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        {sessionLocked ? (
          <div className="rounded-xl border border-[var(--stroke)] bg-[var(--canvas)] px-3.5 py-3 text-sm text-[var(--ink-secondary)]">
            This chat is closed. Press <span className="font-medium text-[var(--ink)]">Start over</span>{" "}
            for a new request.
          </div>
        ) : null}

        {!sessionLocked &&
          options.length > 0 &&
          conversation.require_confirm !== false && (
            <div className="flex flex-wrap gap-2">
              <HelioButton
                className="flex-1 sm:flex-none"
                onClick={() => void confirmSelection()}
                disabled={confirmDisabled}
                loading={sending}
              >
                {confirmLabel}
              </HelioButton>
              {selectedIds.length > 0 && (
                <HelioButton
                  variant="secondary"
                  onClick={() => {
                    setSelectedIds([]);
                    setFreeText("");
                  }}
                >
                  Clear
                </HelioButton>
              )}
            </div>
          )}

        {conversation.controls && conversation.controls.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {(sessionLocked
              ? conversation.controls.filter((c) => c === "start_over")
              : conversation.controls
            ).map((control) => {
              const meta = CONTROL_META[control] || { label: control.replace(/_/g, " ") };
              const Icon = meta.icon;
              return (
                <HelioButton
                  key={control}
                  variant={sessionLocked ? "primary" : "secondary"}
                  size="sm"
                  disabled={sending}
                  onClick={() => void sendControl(control)}
                >
                  {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
                  {meta.label}
                </HelioButton>
              );
            })}
          </div>
        )}

        {error && <p className="text-sm text-[var(--danger)]">{error}</p>}
      </div>
    </div>
  );
}
