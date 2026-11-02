"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { conversations, runs, workspace, tickets, actions, security } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Send, Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { GuidedHelpdeskPanel } from "@/components/guided-helpdesk-panel";
import { RichText } from "@/components/rich-text";
import { Surface } from "@/components/helio";

type LocalMessage = {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
  pending?: boolean;
};

type AgentOutput = {
  headline?: string;
  summary?: string;
  findings?: Array<{
    kind?: string;
    label?: string;
    explanation?: string;
  }>;
  suggested_steps?: Array<{
    title?: string;
    why?: string;
    action_type?: "open_ticket" | "request_approval" | "safe_instruction" | "view_evidence" | "escalate";
    requires_confirmation?: boolean;
  }>;
};

export default function SupportPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"guided" | "freeform">("guided");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [lastOutput, setLastOutput] = useState<AgentOutput | null>(null);
  const [optimistic, setOptimistic] = useState<LocalMessage[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [selectedStepIdx, setSelectedStepIdx] = useState<number | null>(null);
  const [postActionFollowUp, setPostActionFollowUp] = useState(false);
  const [followUpChoice, setFollowUpChoice] = useState<"yes" | "no" | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [guidedPrefill, setGuidedPrefill] = useState<string | null>(null);
  const [guidedTopic, setGuidedTopic] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    // Explicit freeform only when requested — home describe stays in guided bakery flow
    if (params.get("mode") === "describe" && !params.get("prefill") && !params.get("topic")) {
      setMode("freeform");
    }
    const prefill = params.get("prefill");
    if (prefill) {
      setGuidedPrefill(prefill);
      setMode("guided");
      setMessage(prefill);
    }
    const topic = params.get("topic");
    if (topic) {
      setGuidedTopic(topic);
      setMode("guided");
    }
  }, []);

  const { data: env } = useQuery({
    queryKey: ["workspace-summary"],
    queryFn: workspace.getSummary,
  });

  // Get or create conversation
  const { isLoading: convosLoading, isError: convosError } = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const convos = await conversations.list();
      if (Array.isArray(convos) && convos.length > 0) {
        setConversationId(convos[0].conversation_id);
        return convos;
      }
      const newConvo = await conversations.create();
      setConversationId(newConvo.conversation_id);
      return [newConvo];
    },
  });

  const { data: conversation, refetch: refetchConversation } = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => conversations.get(conversationId!),
    enabled: !!conversationId,
    refetchInterval: currentRunId ? 1500 : false,
  });

  const { data: runData } = useQuery({
    queryKey: ["run", currentRunId],
    queryFn: () => runs.get(currentRunId!),
    enabled: !!currentRunId,
    refetchInterval: (query) => {
      const data = query.state.data as { status?: string } | undefined;
      return data?.status === "running" || data?.status === "queued" ? 800 : false;
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async (text: string) => {
      let cid = conversationId;
      if (!cid) {
        const created = await conversations.create();
        cid = created.conversation_id;
        setConversationId(cid);
      }
      return conversations.createRun(cid, text);
    },
    onMutate: async (text: string) => {
      const pending: LocalMessage = {
        message_id: `local-${Date.now()}`,
        role: "user",
        content: text,
        pending: true,
      };
      setOptimistic((prev) => [...prev, pending]);
      setMessage("");
      setLastOutput(null);
    },
    onSuccess: async (data) => {
      setCurrentRunId(data.run_id);
      await refetchConversation();
      setOptimistic([]);
    },
    onError: (error: unknown) => {
      setOptimistic([]);
      const msg = error instanceof Error ? error.message : "Failed to send message";
      toast.error(typeof msg === "string" ? msg : "Failed to send message");
    },
  });

  const createTicketMutation = useMutation({
    mutationFn: async (data: { summary: string; description: string; category: string }) =>
      tickets.create(data),
    onSuccess: (data) => {
      toast.success("Support ticket created", {
        description: `Ticket #${data.ticket_id || "created"} - ${data.summary || ""}`,
        action: data.ticket_id ? {
          label: "View ticket",
          onClick: () => window.location.href = `/tickets/${data.ticket_id}`,
        } : undefined,
      });
      setPostActionFollowUp(true);
      setFollowUpChoice(null);
      setSelectedStepIdx(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-summary"] });
    },
    onError: (error: unknown) => {
      const msg = error instanceof Error ? error.message : "Failed to create ticket";
      toast.error("Could not create ticket", { description: msg });
    },
  });

  const proposeActionMutation = useMutation({
    mutationFn: async (data: {
      action_type: "identity_account_unlock" | "vpn_certificate_renewal";
      target_user_id: string;
      device_id?: string;
      rationale: string;
    }) => actions.propose(data),
    onSuccess: (data) => {
      toast.success("Approval request created", {
        description: data.approval_id ? `Approval #${data.approval_id} pending review` : "Request submitted",
        action: data.approval_id ? {
          label: "View approval",
          onClick: () => window.location.href = `/approvals/${data.approval_id}`,
        } : undefined,
      });
      setPostActionFollowUp(true);
      setFollowUpChoice(null);
      setSelectedStepIdx(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-summary"] });
    },
    onError: (error: unknown) => {
      const msg = error instanceof Error ? error.message : "Failed to create approval request";
      toast.error("Could not request approval", { description: msg });
    },
  });

  const escalateMutation = useMutation({
    mutationFn: async (payload: {
      summary: string;
      description: string;
      category: string;
      role?: string;
      reason: string;
    }) => {
      // Mock SoD: P1 declaration requires IT role; employees escalate via P2 ticket.
      const canDeclareP1 =
        payload.role === "security_analyst" ||
        payload.role === "it_engineer" ||
        payload.role === "it_manager" ||
        payload.role === "tenant_admin";
      const priority = canDeclareP1 ? "P1" : "P2";
      const ticket = await tickets.create({
        summary: payload.summary,
        description: payload.description,
        category: payload.category,
        priority,
      });
      let escalation: { escalation_id?: string } | null = null;
      if (payload.role === "security_analyst" || payload.role === "it_engineer") {
        try {
          escalation = await security.createEscalation({
            reason: payload.reason,
            severity: "high",
            ticket_id: ticket.ticket_id,
            evidence_ids: (displayOutput?.findings || [])
              .map((f) => f.label)
              .filter(Boolean) as string[],
          });
        } catch {
          // Ticket still created; escalation API is role-gated upstream.
        }
      }
      return { ticket, escalation, priority };
    },
    onSuccess: ({ ticket, escalation, priority }) => {
      const escPart = escalation?.escalation_id
        ? ` · Escalation ${escalation.escalation_id}`
        : "";
      toast.success("Escalated to human support", {
        description: `Priority ${priority} ticket ${ticket.ticket_id || "created"}${escPart}`,
        action: ticket.ticket_id
          ? {
              label: "View ticket",
              onClick: () => {
                window.location.href = `/tickets/${ticket.ticket_id}`;
              },
            }
          : undefined,
      });
      setPostActionFollowUp(true);
      setFollowUpChoice(null);
      setSelectedStepIdx(null);
      void queryClient.invalidateQueries({ queryKey: ["workspace-summary"] });
    },
    onError: (error: unknown) => {
      const msg = error instanceof Error ? error.message : "Failed to escalate";
      toast.error("Could not escalate", { description: msg });
    },
  });

  const handleSend = (text?: string) => {
    const payload = (text ?? message).trim();
    if (!payload || sendMessageMutation.isPending || !!currentRunId) return;
    sendMessageMutation.mutate(payload);
  };

  const handleActionClick = (step: NonNullable<AgentOutput["suggested_steps"]>[number]) => {
    if (!step.action_type) {
      toast.error("Action type not specified");
      return;
    }

    switch (step.action_type) {
      case "safe_instruction":
        toast.info(step.title || "Follow the instructions", {
          description: step.why,
        });
        setPostActionFollowUp(true);
        setFollowUpChoice(null);
        setSelectedStepIdx(null);
        break;

      case "open_ticket": {
        // Extract context from the conversation to build ticket
        const summary = step.title || "Support request from AI chat";
        const description = `${step.why || ""}\n\nContext from conversation:\n${
          displayOutput?.summary || conversation?.messages?.slice(-2).map((m: any) => m.content).join("\n\n") || ""
        }`;
        const category = determineCategory(displayOutput);
        
        createTicketMutation.mutate({
          summary,
          description,
          category,
        });
        break;
      }

      case "request_approval": {
        if (!env?.identity?.user_id) {
          toast.error("User identity not available");
          return;
        }

        // Determine action type from context
        const actionType = determineActionType(step, displayOutput);
        const deviceId = env?.devices?.[0]?.device_id;

        proposeActionMutation.mutate({
          action_type: actionType,
          target_user_id: env.identity.user_id,
          device_id: actionType === "vpn_certificate_renewal" ? deviceId : undefined,
          rationale: step.why || step.title || "Approval requested from AI support chat",
        });
        break;
      }

      case "view_evidence": {
        const findings = displayOutput?.findings || [];
        if (findings.length > 0) {
          const lines = findings
            .slice(0, 4)
            .map((f) => `• ${f.label || f.kind || "finding"}${f.explanation ? `: ${f.explanation}` : ""}`)
            .join("\n");
          toast.info(`Evidence (${findings.length} finding${findings.length === 1 ? "" : "s"})`, {
            description: lines,
            duration: 10000,
            action: {
              label: "Security",
              onClick: () => router.push("/security"),
            },
          });
        } else {
          toast.info("No agent findings in this response", {
            description: "Open Security for tenant findings if your role allows.",
            action: {
              label: "Open Security",
              onClick: () => router.push("/security"),
            },
          });
        }
        break;
      }

      case "escalate": {
        const summary = `[ESCALATED] ${step.title || "Support escalation from AI chat"}`;
        const description = `${step.why || "User requested escalation"}\n\nAgent summary:\n${
          displayOutput?.summary || ""
        }\n\nFindings:\n${
          (displayOutput?.findings || [])
            .map((f) => `- ${f.label}: ${f.explanation || ""}`)
            .join("\n") || "(none)"
        }`;
        const category = determineCategory(displayOutput) === "device"
          ? "security"
          : determineCategory(displayOutput);
        const reason =
          (step.why || step.title || "Escalation from AI support chat").length >= 10
            ? step.why || step.title || "Escalation from AI support chat"
            : "Escalation from AI support chat: human review requested";
        escalateMutation.mutate({
          summary,
          description,
          category,
          role: env?.identity?.role,
          reason,
        });
        break;
      }

      default:
        toast.error("Unknown action type");
    }
  };

  // Helper to determine ticket category from agent output
  const determineCategory = (output: AgentOutput | null): string => {
    const summary = output?.summary?.toLowerCase() || "";
    const headline = output?.headline?.toLowerCase() || "";
    const text = `${summary} ${headline}`;

    if (text.includes("vpn") || text.includes("certificate")) return "vpn";
    if (text.includes("account") || text.includes("locked") || text.includes("identity")) return "identity";
    if (text.includes("device") || text.includes("laptop") || text.includes("cpu") || text.includes("disk")) return "device";
    if (text.includes("email")) return "email";
    if (text.includes("software") || text.includes("app")) return "software";
    if (text.includes("network")) return "network";
    if (text.includes("security")) return "security";
    
    return "device"; // default
  };

  // Helper to determine action type for approval requests
  const determineActionType = (
    step: NonNullable<AgentOutput["suggested_steps"]>[number],
    output: AgentOutput | null
  ): "identity_account_unlock" | "vpn_certificate_renewal" => {
    const text = `${step.title} ${step.why} ${output?.summary || ""} ${output?.headline || ""}`.toLowerCase();
    
    if (text.includes("vpn") || text.includes("certificate")) {
      return "vpn_certificate_renewal";
    }
    
    return "identity_account_unlock";
  };

  useEffect(() => {
    if (!runData) return;
    if (runData.status === "completed") {
      if (runData.output) setLastOutput(runData.output as AgentOutput);
      setCurrentRunId(null);
      void refetchConversation().then(() => setOptimistic([]));
      void queryClient.invalidateQueries({ queryKey: ["conversations"] });
    } else if (runData.status === "failed") {
      toast.error(runData.error || "Agent run failed");
      setCurrentRunId(null);
      void refetchConversation();
    }
  }, [runData, refetchConversation, queryClient]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages, optimistic, lastOutput, currentRunId]);

  const suggestedPrompts = [
    "Fix my VPN connection",
    "Why is my laptop slow?",
    "My account is locked",
    "Check my device status",
  ];

  const serverMessages: LocalMessage[] = conversation?.messages || [];
  const messages =
    optimistic.length > 0
      ? [
          ...serverMessages.filter(
            (m) => !optimistic.some((o) => o.content === m.content && o.role === m.role)
          ),
          ...optimistic,
        ]
      : serverMessages;

  const isProcessing = sendMessageMutation.isPending || !!currentRunId;
  const displayOutput = (runData?.output as AgentOutput | undefined) || lastOutput;

  return (
    <div className="h-full min-h-0 flex flex-col overflow-hidden">
      {convosError && mode === "freeform" && (
        <p className="text-sm text-[var(--danger)] shrink-0 pb-2">
          Could not reach agent API. Check Docker agent-api health.
        </p>
      )}

      {mode === "guided" ? (
        <div className="flex-1 min-h-0 overflow-hidden">
          <GuidedHelpdeskPanel
            preferredUserId={env?.identity?.user_id}
            initialPrefill={guidedPrefill}
            initialTopic={guidedTopic}
          />
        </div>
      ) : (
      <div className="flex-1 min-h-0 overflow-hidden">
        <div className="h-full min-h-0 flex flex-col">
          <Surface className="flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-4 sm:p-6 space-y-4">
              {convosLoading && messages.length === 0 && (
                <div className="text-center py-12 text-muted-foreground text-sm">
                  Connecting to support session…
                </div>
              )}

              {messages.length === 0 && !isProcessing && !convosLoading && (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" className="text-primary">
                      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="2" />
                      <circle cx="12" cy="5" r="2" fill="currentColor" />
                      <circle cx="12" cy="19" r="2" fill="currentColor" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium mb-2">How can I help you today?</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    Single choice: select a prompt, then Confirm
                  </p>
                  <div className="flex flex-col gap-2 max-w-lg mx-auto text-left">
                    {suggestedPrompts.map((prompt) => (
                      <label
                        key={prompt}
                        className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer ${
                          selectedPrompt === prompt
                            ? "border-primary bg-primary/10"
                            : "border-border"
                        }`}
                      >
                        <input
                          type="radio"
                          name="starter-prompt"
                          className="mt-1"
                          checked={selectedPrompt === prompt}
                          onChange={() => setSelectedPrompt(prompt)}
                          disabled={isProcessing || !conversationId}
                        />
                        <span className="text-sm">{prompt}</span>
                      </label>
                    ))}
                    <Button
                      className="mt-2"
                      disabled={!selectedPrompt || isProcessing || !conversationId}
                      onClick={() => selectedPrompt && handleSend(selectedPrompt)}
                    >
                      Confirm selection
                    </Button>
                  </div>
                </div>
              )}

              {messages.map((msg) => {
                const isLatestAssistant =
                  msg.role === "assistant" &&
                  messages[messages.length - 1]?.message_id === msg.message_id;
                const showStructured = isLatestAssistant && displayOutput;

                return (
                  <div
                    key={msg.message_id}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl p-4 shadow-soft ${
                        msg.role === "user"
                          ? "bg-brand-gradient text-white rounded-br-md"
                          : "bg-[var(--surface)] border border-[var(--stroke)] text-[var(--ink)] rounded-bl-md"
                      }`}
                    >
                      {showStructured ? (
                        <div className="space-y-3">
                          {displayOutput.headline && (
                            <div className="font-medium text-lg">{displayOutput.headline}</div>
                          )}
                          <p className="text-sm leading-relaxed whitespace-pre-wrap">
                            <RichText text={displayOutput.summary || msg.content} />
                          </p>

                          {displayOutput.findings && displayOutput.findings.length > 0 && (
                            <div className="space-y-2 mt-4">
                              <div className="text-xs font-medium text-muted-foreground uppercase">
                                Findings
                              </div>
                              {displayOutput.findings.map((finding, idx) => (
                                <div
                                  key={idx}
                                  className="p-3 rounded-lg bg-surface-1 border border-border"
                                >
                                  <div className="flex items-start gap-2 mb-2">
                                    {finding.kind === "confirmed" && (
                                      <CheckCircle className="w-4 h-4 text-success mt-0.5" />
                                    )}
                                    {finding.kind === "likely" && (
                                      <AlertCircle className="w-4 h-4 text-warning mt-0.5" />
                                    )}
                                    <span className="font-medium text-sm">{finding.label}</span>
                                  </div>
                                  <p className="text-xs text-muted-foreground">
                                    {finding.explanation}
                                  </p>
                                </div>
                              ))}
                            </div>
                          )}

                          {displayOutput.suggested_steps &&
                            displayOutput.suggested_steps.length > 0 && (
                              <div className="mt-4 space-y-2">
                                <div className="text-xs font-medium text-muted-foreground uppercase">
                                  Recommended Actions · single choice
                                </div>
                                {displayOutput.suggested_steps.map((step, idx) => (
                                  <label
                                    key={idx}
                                    className={`flex w-full items-start gap-3 rounded-lg border p-3 cursor-pointer text-left ${
                                      selectedStepIdx === idx
                                        ? "border-primary bg-primary/10"
                                        : "border-border"
                                    }`}
                                  >
                                    <input
                                      type="radio"
                                      name="suggested-step"
                                      className="mt-1"
                                      checked={selectedStepIdx === idx}
                                      onChange={() => setSelectedStepIdx(idx)}
                                      disabled={
                                        createTicketMutation.isPending ||
                                        proposeActionMutation.isPending ||
                                        escalateMutation.isPending
                                      }
                                    />
                                    <span className="flex-1">
                                      <span className="block font-medium text-sm">{step.title}</span>
                                      <span className="block text-xs text-muted-foreground mt-1">
                                        {step.why}
                                      </span>
                                    </span>
                                  </label>
                                ))}
                                <Button
                                  className="w-full"
                                  disabled={
                                    selectedStepIdx === null ||
                                    createTicketMutation.isPending ||
                                    proposeActionMutation.isPending ||
                                    escalateMutation.isPending
                                  }
                                  onClick={() => {
                                    if (selectedStepIdx === null) return;
                                    const step = displayOutput.suggested_steps?.[selectedStepIdx];
                                    if (step) handleActionClick(step);
                                  }}
                                >
                                  Confirm selection
                                </Button>
                              </div>
                            )}

                          {postActionFollowUp && (
                            <div className="mt-4 space-y-2 rounded-lg border border-border p-3">
                              <p className="text-sm font-medium">
                                That step is done. Is there anything else I can help you with?
                              </p>
                              <label className="flex items-center gap-2 text-sm">
                                <input
                                  type="radio"
                                  name="anything-else"
                                  checked={followUpChoice === "yes"}
                                  onChange={() => setFollowUpChoice("yes")}
                                />
                                Yes, I have another issue
                              </label>
                              <label className="flex items-center gap-2 text-sm">
                                <input
                                  type="radio"
                                  name="anything-else"
                                  checked={followUpChoice === "no"}
                                  onChange={() => setFollowUpChoice("no")}
                                />
                                No, I&apos;m done for now
                              </label>
                              <Button
                                size="sm"
                                disabled={!followUpChoice}
                                onClick={() => {
                                  if (followUpChoice === "yes") {
                                    setPostActionFollowUp(false);
                                    setFollowUpChoice(null);
                                    setLastOutput(null);
                                    setSelectedPrompt(null);
                                    toast.message("Sure. Describe your next issue below.");
                                  } else if (followUpChoice === "no") {
                                    setPostActionFollowUp(false);
                                    setFollowUpChoice(null);
                                    toast.success("You're all set. Come back anytime.");
                                  }
                                }}
                              >
                                Confirm selection
                              </Button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <p className="text-sm opacity-90 whitespace-pre-wrap">
                          <RichText text={msg.content} />
                          {msg.pending ? " …" : ""}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}

              {isProcessing && (
                <div className="flex justify-start">
                  <div className="bg-card border border-border rounded-lg p-4 max-w-[80%]">
                    <div className="flex items-center gap-3">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm text-muted-foreground">
                        {currentRunId
                          ? "Simulator workflow · checking identity, devices, VPN…"
                          : "Sending…"}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="shrink-0 border-t border-border p-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
              <div className="flex gap-2">
                <Input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={
                    conversationId
                      ? "Describe your issue…"
                      : "Preparing conversation…"
                  }
                  disabled={isProcessing || !conversationId}
                  className="flex-1"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={!message.trim() || isProcessing || !conversationId}
                  aria-label="Send"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                Enter to send · Shift+Enter newline · Offline Simulator
              </p>
            </div>
          </Surface>
        </div>
      </div>
      )}
    </div>
  );
}
