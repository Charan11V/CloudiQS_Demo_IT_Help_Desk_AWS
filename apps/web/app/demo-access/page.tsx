"use client";

import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";
import { HelioLogo, HelioButton } from "@/components/helio";

export default function DemoAccessPage() {
  const [secret, setSecret] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const params = useSearchParams();
  const next = params.get("next") || "/login";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/demo-access", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Access denied");
      }
      // Full navigation so the new HttpOnly cookie is definitely sent on the next request
      const dest = next.startsWith("/") ? next : "/login";
      window.location.assign(dest);
      return;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Access denied");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-canvas px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="flex justify-center">
          <HelioLogo />
        </div>
        <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] p-6 shadow-soft">
          <h1 className="text-xl font-semibold text-ink mb-1">Demo access</h1>
          <p className="text-sm text-ink/70 mb-4">
            This public demo is gated to protect Bedrock usage. Enter the shared demo
            access secret provided by the presenter, then choose a persona.
          </p>
          <form onSubmit={onSubmit} className="space-y-3">
            <label className="block text-sm font-medium text-ink">
              Access secret
              <input
                type="password"
                autoComplete="off"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                className="mt-1 w-full rounded-xl border border-[var(--stroke)] bg-canvas px-3 py-2"
                required
              />
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <HelioButton type="submit" disabled={loading || !secret} className="w-full">
              {loading ? "Checking…" : "Continue"}
            </HelioButton>
          </form>
        </div>
      </div>
    </main>
  );
}
