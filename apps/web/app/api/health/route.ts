import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const agentUrl = process.env.AGENT_API_URL || "http://127.0.0.1:8001";
  let agentOk = false;
  try {
    const r = await fetch(`${agentUrl}/health`, { cache: "no-store" });
    agentOk = r.ok;
  } catch {
    agentOk = false;
  }

  return NextResponse.json({
    ok: true,
    service: "web",
    agent_api: agentOk,
    demo_gate: process.env.DEMO_GATE_ENABLED === "1",
    runtime: process.env.NEXT_PUBLIC_RUNTIME_BADGE || "local",
  });
}
