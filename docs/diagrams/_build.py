"""Build standalone SVG diagrams for the application handbook."""
from pathlib import Path

OUT = Path(__file__).resolve().parent

FONT = "Segoe UI, Arial, sans-serif"


def header(w: int, h: int, title: str) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">
<title>{title}</title>
<rect width="{w}" height="{h}" fill="#f8fafc"/>
<defs>
  <marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
    <polygon points="0 0, 10 4, 0 8" fill="#0f172a"/>
  </marker>
</defs>
'''


def footer() -> str:
    return "</svg>\n"


def box(x, y, w, h, title, sub="", fill="#ffffff", stroke="#0f172a") -> str:
    cx = x + w / 2
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.75"/>'
    ]
    if sub:
        parts.append(
            f'<text x="{cx}" y="{y + h/2 - 7}" text-anchor="middle" font-family="{FONT}" font-size="15" font-weight="650" fill="#0f172a">{title}</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{y + h/2 + 14}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="#475569">{sub}</text>'
        )
    else:
        parts.append(
            f'<text x="{cx}" y="{y + h/2 + 5}" text-anchor="middle" font-family="{FONT}" font-size="15" font-weight="650" fill="#0f172a">{title}</text>'
        )
    return "\n".join(parts)


def diamond(cx, cy, w, h, text, fill="#fff7ed", stroke="#c2410c") -> str:
    pts = f"{cx},{cy - h/2} {cx + w/2},{cy} {cx},{cy + h/2} {cx - w/2},{cy}"
    return (
        f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1.75"/>'
        f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="{FONT}" font-size="13" font-weight="650" fill="#0f172a">{text}</text>'
    )


def line(x1, y1, x2, y2) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0f172a" stroke-width="1.6" marker-end="url(#ah)"/>'


def poly(points: str) -> str:
    return f'<polyline points="{points}" fill="none" stroke="#0f172a" stroke-width="1.6" marker-end="url(#ah)"/>'


def tag(x, y, text) -> str:
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="12" fill="#334155">{text}</text>'


def save(name: str, body: str) -> None:
    (OUT / name).write_text(body, encoding="utf-8")


def aws() -> None:
    w, h = 980, 520
    p = [header(w, h, "AWS request path")]
    p.append(box(36, 36, 160, 64, "Browser", "one origin"))
    p.append(box(280, 36, 180, 64, "Caddy :443", "ZeroSSL", "#eff6ff", "#1d4ed8"))
    p.append(box(540, 36, 180, 64, "Next.js", "rewrites", "#eff6ff", "#1d4ed8"))
    p.append(line(196, 68, 280, 68))
    p.append(line(460, 68, 540, 68))
    p.append(box(250, 170, 200, 64, "agent-api", "sessions and tools"))
    p.append(box(620, 170, 200, 64, "bakery-api", "guided engine"))
    p.append(poly("630,100 350,100 350,170"))
    p.append(poly("630,100 720,100 720,170"))
    p.append(tag(500, 128, "api-backend"))
    p.append(tag(740, 128, "bakery-api"))
    p.append(box(40, 310, 170, 58, "app.sqlite", "sessions, runs", "#f0fdf4", "#047857"))
    p.append(box(250, 310, 200, 58, "mock API", "enterprise SQLite", "#f0fdf4", "#047857"))
    p.append(box(640, 310, 180, 58, "Postgres", "guided tickets", "#f0fdf4", "#047857"))
    p.append(line(300, 234, 125, 310))
    p.append(line(350, 234, 350, 310))
    p.append(line(720, 234, 730, 310))
    p.append(box(250, 420, 210, 64, "AgentCore", "Hyderabad", "#fff7ed", "#c2410c"))
    p.append(box(560, 420, 200, 64, "Groq GPT-OSS", "openai/gpt-oss-20b", "#fff7ed", "#c2410c"))
    p.append(line(350, 368, 340, 420))
    p.append(line(460, 452, 560, 452))
    p.append(poly("250,452 180,452 180,200 250,200"))
    p.append(tag(78, 190, "HMAC callback"))
    p.append(footer())
    save("01-aws-request-path.svg", "\n".join(p))


def local() -> None:
    w, h = 860, 280
    p = [header(w, h, "Local Docker path")]
    p.append(box(30, 90, 160, 64, "Browser", "localhost:3000", "#eff6ff", "#1d4ed8"))
    p.append(box(250, 90, 160, 64, "Next.js", "rewrites"))
    p.append(box(470, 90, 170, 64, "agent-api", "simulator or Groq"))
    p.append(box(690, 90, 140, 64, "mock API", "SQLite", "#f0fdf4", "#047857"))
    p.append(line(190, 122, 250, 122))
    p.append(line(410, 122, 470, 122))
    p.append(line(640, 122, 690, 122))
    p.append(tag(250, 50, "AgentCore is off unless AGENTCORE_ENABLED=1"))
    p.append(footer())
    save("02-local-path.svg", "\n".join(p))


def trust() -> None:
    w, h = 920, 340
    p = [header(w, h, "Trust boundary")]
    p.append('<rect x="24" y="24" width="200" height="290" rx="12" fill="#eff6ff" stroke="#1d4ed8" stroke-width="1.5"/>')
    p.append(tag(44, 52, "Browser"))
    p.append(box(44, 80, 160, 56, "Pages"))
    p.append(box(44, 170, 160, 56, "Cookies"))
    p.append('<rect x="250" y="24" width="220" height="290" rx="12" fill="#ffffff" stroke="#0f172a" stroke-width="1.5"/>')
    p.append(tag(270, 52, "Next.js"))
    p.append(box(270, 80, 180, 56, "Demo gate"))
    p.append(box(270, 170, 180, 56, "Rewrites"))
    p.append('<rect x="496" y="24" width="400" height="290" rx="12" fill="#f0fdf4" stroke="#047857" stroke-width="1.5"/>')
    p.append(tag(516, 52, "APIs enforce policy"))
    p.append(box(516, 80, 170, 56, "Sessions"))
    p.append(box(706, 80, 170, 56, "Tool registry"))
    p.append(box(516, 180, 170, 56, "Guided engine"))
    p.append(box(706, 180, 170, 56, "Mock API ACL"))
    p.append(line(204, 108, 270, 108))
    p.append(line(450, 198, 516, 198))
    p.append(footer())
    save("03-trust-boundary.svg", "\n".join(p))


def login() -> None:
    w, h = 980, 420
    p = [header(w, h, "Sign-in flow")]
    cols = [
        (40, "Browser"),
        (250, "Next.js"),
        (460, "agent-api"),
        (700, "bakery-api"),
    ]
    for x, name in cols:
        p.append(box(x, 24, 180, 48, name, fill="#eff6ff", stroke="#1d4ed8"))
        p.append(f'<line x1="{x+90}" y1="72" x2="{x+90}" y2="400" stroke="#cbd5e1" stroke-width="1.5"/>')
    steps = [
        (100, 40, 250, "1  persona key"),
        (150, 250, 460, "2  POST /auth/demo-login"),
        (210, 460, 40, "3  Set helio_session"),
        (280, 40, 700, "4  Map to NS-00x"),
        (340, 700, 40, "5  Set bakery_session"),
    ]
    for y, x1, x2, text in steps:
        c1 = x1 + 90
        c2 = x2 + 90
        p.append(line(c1, y, c2, y))
        p.append(tag(min(c1, c2) + 12, y - 8, text))
    p.append(footer())
    save("04-sign-in.svg", "\n".join(p))


def guided() -> None:
    w, h = 980, 640
    p = [header(w, h, "Guided helpdesk")]
    p.append(box(360, 24, 260, 56, "WELCOME", "top menu", "#eff6ff", "#1d4ed8"))
    p.append(box(80, 150, 240, 56, "CHOOSING_SUBCATEGORY", "issue family"))
    p.append(box(660, 150, 240, 56, "DESCRIBING_OTHER", "off-menu text"))
    p.append(line(430, 80, 200, 150))
    p.append(line(550, 80, 780, 150))
    p.append(box(80, 270, 240, 56, "CHOOSING_SYMPTOM", "symptom list"))
    p.append(line(200, 206, 200, 270))
    p.append(box(80, 390, 240, 56, "INVESTIGATING", "read Postgres", "#fff7ed", "#c2410c"))
    p.append(line(200, 326, 200, 390))
    p.append(box(400, 390, 240, 56, "WAITING_APPROVAL", "person must decide"))
    p.append(box(660, 270, 240, 56, "Confirm ticket", "one owner", "#f0fdf4", "#047857"))
    p.append(line(780, 206, 780, 270))
    p.append(box(80, 520, 240, 56, "CASE_SUMMARY", "fix or ticket"))
    p.append(box(400, 520, 240, 56, "ASKING_ANYTHING_ELSE", "next or close"))
    p.append(box(660, 520, 240, 56, "CLOSED", "start over only"))
    p.append(line(200, 446, 200, 520))
    p.append(line(320, 546, 400, 546))
    p.append(line(640, 546, 660, 546))
    p.append(line(520, 418, 320, 418))
    p.append(tag(330, 408, "needs a person"))
    p.append(footer())
    save("05-guided-flow.svg", "\n".join(p))


def freeform() -> None:
    w, h = 980, 520
    p = [header(w, h, "Freeform agent run")]
    actors = [(30, "Browser"), (210, "agent-api"), (410, "AgentCore"), (620, "Groq"), (800, "mock API")]
    for x, name in actors:
        p.append(box(x, 20, 150, 48, name, fill="#eff6ff", stroke="#1d4ed8"))
        p.append(f'<line x1="{x+75}" y1="68" x2="{x+75}" y2="500" stroke="#cbd5e1" stroke-width="1.5"/>')
    arrows = [
        (110, 30, 210, "POST /runs"),
        (170, 210, 410, "IAM invoke"),
        (230, 410, 620, "tool loop"),
        (290, 620, 410, "tool name"),
        (350, 410, 210, "HMAC bridge"),
        (410, 210, 800, "Bearer call"),
        (470, 800, 30, "completed answer"),
    ]
    for y, a, b, text in arrows:
        p.append(line(a + 75, y, b + 75, y))
        p.append(tag(min(a, b) + 90, y - 8, text))
    p.append(footer())
    save("06-freeform-run.svg", "\n".join(p))


def brain() -> None:
    w, h = 860, 640
    p = [header(w, h, "Which brain runs")]
    p.append(box(300, 20, 260, 56, "run_agent", "new user message"))
    p.append(diamond(430, 150, 280, 90, "AgentCore on?"))
    p.append(line(430, 76, 430, 105))
    p.append(box(40, 250, 240, 64, "Invoke Runtime", "Hyderabad", "#fff7ed", "#c2410c"))
    p.append(box(560, 250, 260, 64, "Local provider", "inside agent-api"))
    p.append(line(330, 180, 160, 250))
    p.append(line(530, 180, 690, 250))
    p.append(tag(168, 210, "yes"))
    p.append(tag(560, 210, "no"))
    p.append(diamond(160, 400, 240, 80, "Transport error?"))
    p.append(line(160, 314, 160, 360))
    p.append(box(40, 520, 220, 64, "Try local provider", "Groq or simulator"))
    p.append(box(300, 520, 240, 64, "Keep the error", "do not switch path", "#fee2e2", "#b91c1c"))
    p.append(line(80, 430, 150, 520))
    p.append(line(240, 430, 420, 520))
    p.append(tag(70, 480, "yes"))
    p.append(tag(250, 480, "no"))
    p.append(box(560, 400, 260, 150, "simulator", "or Bedrock, Groq, Ollama"))
    p.append(line(690, 314, 690, 400))
    p.append(footer())
    save("07-which-brain.svg", "\n".join(p))


def bridge() -> None:
    w, h = 980, 200
    p = [header(w, h, "Tool bridge")]
    items = [
        (20, "agent-api", "stores token"),
        (210, "AgentCore", "calls back"),
        (400, "HMAC check", "timestamp + body"),
        (600, "SQLite session", "bearer stays here"),
        (790, "mock API", "same tenant"),
    ]
    fills = ["#ffffff", "#fff7ed", "#eff6ff", "#f0fdf4", "#f0fdf4"]
    strokes = ["#0f172a", "#c2410c", "#1d4ed8", "#047857", "#047857"]
    for i, (x, title, sub) in enumerate(items):
        p.append(box(x, 60, 170, 70, title, sub, fills[i], strokes[i]))
        if i:
            p.append(line(x - 20, 95, x, 95))
    p.append(footer())
    save("08-tool-bridge.svg", "\n".join(p))


def tickets() -> None:
    w, h = 860, 760
    p = [header(w, h, "Ticket owner")]
    p.append(box(300, 16, 260, 56, "New ticket", "category on the request"))
    p.append(diamond(430, 140, 240, 80, "Category?"))
    p.append(line(430, 72, 430, 100))
    p.append(box(40, 240, 280, 64, "Security analyst", "security, cloud access", "#fff7ed", "#c2410c"))
    p.append(box(540, 240, 280, 64, "IT engineer", "every other category", "#eff6ff", "#1d4ed8"))
    p.append(line(350, 170, 180, 240))
    p.append(line(510, 170, 680, 240))
    p.append(box(250, 360, 360, 64, "First active user of that role", "lowest user id", "#f0fdf4", "#047857"))
    p.append(poly("180,304 180,340 430,340 430,360"))
    p.append(poly("680,304 680,340 430,340"))
    p.append(diamond(430, 500, 220, 80, "Role filled?"))
    p.append(line(430, 424, 430, 460))
    p.append(box(40, 620, 240, 64, "status = assigned", "one person", "#f0fdf4", "#047857"))
    p.append(box(460, 600, 360, 100, "Fallback", "IT engineer, manager, admin, analyst"))
    p.append(line(350, 530, 160, 620))
    p.append(line(510, 530, 640, 600))
    p.append(tag(175, 580, "yes"))
    p.append(tag(530, 560, "no"))
    p.append(footer())
    save("09-ticket-owner.svg", "\n".join(p))


def approval() -> None:
    w, h = 980, 280
    p = [header(w, h, "Approval path")]
    p.append(box(20, 40, 170, 64, "Employee", "asks for a change", "#eff6ff", "#1d4ed8"))
    p.append(box(230, 40, 180, 64, "Proposal", "does not execute"))
    p.append(box(450, 40, 180, 64, "Self-approve", "HTTP 403", "#fee2e2", "#b91c1c"))
    p.append(box(230, 170, 180, 64, "IT engineer", "approves", "#f0fdf4", "#047857"))
    p.append(box(450, 170, 200, 64, "Execute", "or 409 if non-compliant"))
    p.append(box(700, 170, 240, 64, "Mock API writes", "the change", "#f0fdf4", "#047857"))
    p.append(line(190, 72, 230, 72))
    p.append(line(410, 72, 450, 72))
    p.append(line(320, 104, 320, 170))
    p.append(line(410, 202, 450, 202))
    p.append(line(650, 202, 700, 202))
    p.append(footer())
    save("10-approval.svg", "\n".join(p))


if __name__ == "__main__":
    aws()
    local()
    trust()
    login()
    guided()
    freeform()
    brain()
    bridge()
    tickets()
    approval()
    print("wrote", len(list(OUT.glob("*.svg"))), "svgs")
