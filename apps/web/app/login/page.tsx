"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api-client";
import { PERSONAS, type Persona, type PersonaSection } from "@/lib/personas";
import { toast } from "sonner";
import {
  HelioLogo,
  HelioButton,
  DemoIndicator,
} from "@/components/helio";
import { cn } from "@/lib/utils";

const SECTIONS: { id: PersonaSection; title: string; blurb: string }[] = [
  {
    id: "employees",
    title: "Employees",
    blurb: "End users requesting IT help with their own devices and accounts.",
  },
  {
    id: "it_support",
    title: "IT Support staff",
    blurb: "Engineers, managers, admins, and security who handle tickets and approvals.",
  },
];

export default function LoginPage() {
  const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleLogin = async () => {
    if (!selectedPersona) return;
    const persona = PERSONAS.find((p) => p.key === selectedPersona);
    if (!persona) return;
    if (persona.disabled) {
      toast.error(persona.disabledReason || "This account is disabled");
      return;
    }
    setIsLoading(true);
    try {
      await auth.login(selectedPersona);
      // Full navigation so the session cookie is included on the next document request
      window.location.assign("/");
      return;
    } catch (error: unknown) {
      toast.error(error instanceof Error ? error.message : "Login failed");
      setIsLoading(false);
    }
  };

  const initials = (p: Persona) =>
    p.name
      .split(/\s/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase())
      .join("");

  const renderPersonaButton = (p: Persona) => {
    const active = selectedPersona === p.key;
    return (
      <button
        key={p.key}
        type="button"
        disabled={p.disabled}
        onClick={() => setSelectedPersona(p.key)}
        className={cn(
          "w-full flex items-center gap-3 rounded-2xl border px-3.5 py-3.5 min-h-[56px] text-left transition-all shadow-soft",
          p.disabled && "opacity-45 cursor-not-allowed shadow-none",
          active
            ? "border-[var(--signal)] bg-[var(--signal-soft)] ring-2 ring-[var(--signal)]/20"
            : "border-[var(--stroke)] bg-[var(--surface)] hover:border-[var(--stroke-strong)] hover:bg-[var(--surface-hover)]"
        )}
      >
        <div
          className={cn(
            "h-10 w-10 rounded-full flex items-center justify-center text-sm font-medium shrink-0",
            active
              ? "bg-brand-gradient text-white"
              : "bg-[var(--surface-soft)] text-[var(--ink-secondary)]"
          )}
        >
          {initials(p)}
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium text-[var(--ink)]">{p.name}</div>
          <div className="text-xs text-[var(--ink-secondary)]">
            {p.disabled
              ? p.disabledReason || "Unavailable"
              : [p.role, p.department].filter(Boolean).join(" · ")}
          </div>
        </div>
      </button>
    );
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-canvas">
      <div className="relative w-full lg:w-[52%] bg-brand-gradient text-white px-5 py-6 sm:px-8 sm:py-10 lg:px-14 lg:py-14 flex flex-col overflow-hidden shrink-0">
        <div className="flex items-center gap-3 relative z-10">
          <span className="rounded-xl bg-white/15 p-1.5 backdrop-blur-sm">
            <HelioLogo size={28} />
          </span>
          <span className="text-lg sm:text-xl font-semibold tracking-[-0.03em] leading-tight">
            CloudiQS Demo agent
          </span>
        </div>

        <div className="relative z-10 mt-5 lg:mt-auto lg:mb-auto max-w-xl">
          <h1 className="text-[28px] sm:text-[48px] font-semibold tracking-[-0.045em] leading-[1.08]">
            Clarity, when work gets complicated.
          </h1>
          <p className="mt-3 sm:mt-5 text-sm sm:text-base text-white/85 leading-relaxed max-w-md">
            Guided IT support with real diagnosis, consent, and tickets, running on
            simulated enterprise data in this demo environment.
          </p>
        </div>

        <div className="relative z-10 mt-4 lg:mt-0 hidden sm:block">
          <DemoIndicator className="bg-white/15 border-white/25 text-white/90" />
        </div>
      </div>

      <div className="flex-1 flex items-start sm:items-center justify-center px-4 py-6 sm:px-10 sm:py-10 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div className="w-full max-w-[460px]">
          <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-[var(--ink-tertiary)]">
            Enter workspace
          </p>
          <h2 className="mt-2 text-[22px] sm:text-[26px] font-semibold tracking-[-0.03em] text-[var(--ink)]">
            Choose a demo persona
          </h2>
          <p className="mt-2 text-sm text-[var(--ink-secondary)]">
            No passwords. Pick a Northstar role to explore CloudiQS Demo agent with
            synthetic data.
          </p>

          <div className="mt-4 sm:mt-5 space-y-5 max-h-[min(420px,52vh)] sm:max-h-[min(480px,56vh)] overflow-y-auto overscroll-contain pr-1 pb-20 lg:pb-0">
            {SECTIONS.map((section) => {
              const people = PERSONAS.filter((p) => p.section === section.id);
              if (people.length === 0) return null;
              return (
                <div key={section.id}>
                  <div className="mb-2.5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--signal)]">
                      {section.title}
                    </p>
                    <p className="text-xs text-[var(--ink-tertiary)] mt-0.5">{section.blurb}</p>
                  </div>
                  <div className="space-y-2">{people.map(renderPersonaButton)}</div>
                </div>
              );
            })}
          </div>

          <div className="hidden lg:block mt-6">
            <HelioButton
              className="w-full"
              size="lg"
              loading={isLoading}
              disabled={!selectedPersona}
              onClick={handleLogin}
            >
              Enter demo workspace
            </HelioButton>
          </div>
        </div>
      </div>

      <div className="lg:hidden fixed bottom-0 inset-x-0 z-30 border-t border-[var(--stroke)] bg-[var(--surface)]/95 backdrop-blur-sm px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <HelioButton
          className="w-full"
          size="lg"
          loading={isLoading}
          disabled={!selectedPersona}
          onClick={handleLogin}
        >
          Enter demo workspace
        </HelioButton>
      </div>
    </div>
  );
}
