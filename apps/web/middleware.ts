import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const GATE_COOKIE = "cloudiqs_demo_access";
const PUBLIC_PATHS = [
  "/demo-access",
  "/api/demo-access",
  "/api/health",
  // AgentCore Runtime tool-bridge (HMAC + ephemeral token; no browser session)
  "/api-backend/internal/agentcore",
  "/_next",
  "/favicon.ico",
];

export function middleware(request: NextRequest) {
  const gateEnabled = process.env.DEMO_GATE_ENABLED === "1";
  if (!gateEnabled) {
    return NextResponse.next();
  }

  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
  if (isPublic) {
    return NextResponse.next();
  }

  // Optional CloudFront origin verification (fail open if unset)
  const expectedOrigin = process.env.ORIGIN_VERIFY_TOKEN;
  if (expectedOrigin) {
    const provided = request.headers.get("x-cloudiqs-origin-verify");
    // Allow local/docker health checks without the header when Host is localhost
    const host = request.headers.get("host") || "";
    const isLocal = host.startsWith("localhost") || host.startsWith("127.0.0.1");
    const isAgentCoreBridge = pathname.startsWith("/api-backend/internal/agentcore");
    if (!isLocal && !isAgentCoreBridge && provided !== expectedOrigin) {
      return new NextResponse("Origin verification failed", { status: 403 });
    }
  }

  const cookie = request.cookies.get(GATE_COOKIE)?.value;
  const secret = process.env.DEMO_ACCESS_SECRET || "";
  if (!secret) {
    // Misconfigured gate — block public access rather than fail open
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "demo_gate_not_configured" }, { status: 503 });
    }
    return NextResponse.redirect(new URL("/demo-access?error=config", request.url));
  }

  if (cookie && timingSafeEqual(cookie, secret)) {
    return NextResponse.next();
  }

  if (
    pathname.startsWith("/api/") ||
    pathname.startsWith("/api-backend/") ||
    pathname.startsWith("/bakery-api/")
  ) {
    return NextResponse.json({ error: "demo_access_required" }, { status: 401 });
  }

  const dest = new URL("/demo-access", request.url);
  dest.searchParams.set("next", pathname);
  return NextResponse.redirect(dest);
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) {
    out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return out === 0;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
