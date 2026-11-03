import { NextRequest, NextResponse } from "next/server";
import { createHash, timingSafeEqual } from "crypto";

const GATE_COOKIE = "cloudiqs_demo_access";
const MAX_AGE = 60 * 60 * 12; // 12 hours

function safeEqual(a: string, b: string): boolean {
  const ah = createHash("sha256").update(a).digest();
  const bh = createHash("sha256").update(b).digest();
  return timingSafeEqual(ah, bh);
}

export async function POST(request: NextRequest) {
  const expected = process.env.DEMO_ACCESS_SECRET || "";
  if (!expected || expected === "REPLACE_AT_DEPLOY") {
    return NextResponse.json({ error: "demo_gate_not_configured" }, { status: 503 });
  }

  let body: { secret?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "invalid_body" }, { status: 400 });
  }

  const provided = body.secret || "";
  if (!provided || !safeEqual(provided, expected)) {
    return NextResponse.json({ error: "invalid_secret" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  // Secure cookies are dropped by browsers on plain HTTP. This demo may be
  // served over HTTP until CloudFront/HTTPS is available — only mark Secure on HTTPS.
  const proto = (
    request.headers.get("x-forwarded-proto") ||
    request.nextUrl.protocol.replace(":", "") ||
    "http"
  ).toLowerCase();
  const secure = proto === "https";

  // Store the secret as HttpOnly cookie. Middleware compares server-side — never expose to JS.
  res.cookies.set({
    name: GATE_COOKIE,
    value: expected,
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: MAX_AGE,
  });
  return res;
}
