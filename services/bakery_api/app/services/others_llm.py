"""LLM triage for bakery guided \"Others\" free-text path.

Uses an OpenAI-compatible chat endpoint (Groq GPT-OSS-20B by default).
Falls back to None when unset/unavailable so GuidedEngine can use rules.
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

# Last call diagnostic for health / debugging (no secrets).
LAST_ERROR: str | None = None


def _settings() -> dict[str, str]:
    api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or "").strip()
    base_url = (
        os.getenv("OPENAI_BASE_URL") or "https://api.groq.com/openai/v1"
    ).rstrip("/")
    model_id = os.getenv("OPENAI_MODEL_ID") or "openai/gpt-oss-20b"
    return {"api_key": api_key, "base_url": base_url, "model_id": model_id}


def llm_configured() -> bool:
    return bool(_settings()["api_key"])


def _catalog_brief(catalog: dict | None, limit: int = 40) -> str:
    issues = (catalog or {}).get("issues") or []
    lines: list[str] = []
    for issue in issues[:limit]:
        code = issue.get("issue_code") or ""
        label = issue.get("label") or ""
        cat = issue.get("category") or ""
        if code and label:
            lines.append(f"- {code}: {label} ({cat})")
    return "\n".join(lines) if lines else "(no catalog issues loaded)"


def _system_prompt(catalog: dict | None) -> str:
    return f"""You are HELIO, an enterprise IT helpdesk assistant (Demo Mode) in the "Others" chat.

Goal: give ONE solid, practical solution for workplace IT issues using your knowledge plus the
catalog/demo facts below. Do not invent that you already changed production systems.

The UI always shows: your message, Raise a ticket, Back to main menu, and a chat box.
You only choose the branch — do not list those buttons in your message.

Decide ONE branch for the user's LATEST message (use prior turns for context):
- "guide": First reply OR a useful follow-up while still helping.
  Put ONE clear solution in "message" (short steps, what to try next). Ask at most one brief
  clarifying question only if you truly cannot give a solid first answer.
- "resolved": User indicates the issue is fixed / solved / working now.
  Congratulate briefly — UI will send them to the main menu.
- "offer_ticket": Cannot solve here, user wants a ticket/human, or they say it is still broken
  after your guidance. Restate the issue in issue_summary.
- "out_of_scope": Off-topic / not workplace IT. Politely refuse — UI returns to main catalog.

Do NOT map unrelated wording to a catalog code (e.g. "restarting didn't help" ≠ "restart pending").

Available catalog topics (guidance only):
{_catalog_brief(catalog)}

Demo facts:
- Helpdesk hours: Mon–Fri 08:00–18:00 local
- Demo helpdesk line: +1-555-0100
- Demo VPN gateway: vpn.demo.cloudiqs.local
- Guest Wi‑Fi: guest-demo / Welcome2Demo! (Demo Mode)
- Corporate Wi‑Fi uses 802.1X with work account

Respond with ONLY a JSON object (no markdown):
{{
  "branch": "guide" | "resolved" | "offer_ticket" | "out_of_scope",
  "message": "user-facing reply",
  "issue_summary": "short issue title for a ticket (empty if out_of_scope/resolved)"
}}
"""


def _extract_json(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _normalize(payload: dict[str, Any]) -> dict[str, Any] | None:
    branch = str(payload.get("branch") or "").strip().lower()
    if branch in ("answer", "guide_user", "help", "continue", "solution"):
        branch = "guide"
    if branch in ("ticket", "raise_ticket", "escalate", "unresolved"):
        branch = "offer_ticket"
    if branch in ("oos", "outside", "irrelevant", "off_topic"):
        branch = "out_of_scope"
    if branch in ("fixed", "solved", "done", "working", "resolved_ok"):
        branch = "resolved"
    if branch not in ("guide", "resolved", "offer_ticket", "out_of_scope"):
        return None
    message = str(payload.get("message") or "").strip()
    if not message:
        return None
    issue_summary = str(payload.get("issue_summary") or "").strip()
    if branch in ("out_of_scope", "resolved"):
        issue_summary = ""
    return {
        "branch": branch,
        "message": message,
        "issue_summary": issue_summary,
    }


def user_requests_ticket(text: str) -> bool:
    """True when the user explicitly asks to raise/escalate a ticket."""
    lowered = (text or "").lower()
    phrases = (
        "raise a ticket",
        "raise ticket",
        "create a ticket",
        "create ticket",
        "open a ticket",
        "open ticket",
        "file a ticket",
        "file ticket",
        "make a ticket",
        "submit a ticket",
        "escalate",
        "talk to it",
        "talk to a human",
        "speak to someone",
        "contact it",
        "need a ticket",
        "please ticket",
    )
    return any(p in lowered for p in phrases)


def user_says_resolved(text: str) -> bool:
    """True when the user indicates the issue is fixed."""
    lowered = (text or "").lower().strip()
    if not lowered:
        return False
    # Avoid "not solved" / "unresolved"
    if any(
        p in lowered
        for p in (
            "not solved",
            "not fixed",
            "isn't fixed",
            "isnt fixed",
            "still broken",
            "still failing",
            "didn't work",
            "did not work",
            "doesn't work",
            "does not work",
            "unresolved",
        )
    ):
        return False
    phrases = (
        "solved",
        "it's fixed",
        "its fixed",
        "fixed now",
        "working now",
        "works now",
        "resolved",
        "all good",
        "all set",
        "that worked",
        "this worked",
        "issue is gone",
        "problem is gone",
        "thank you that worked",
        "thanks that worked",
        "i'm good",
        "im good",
    )
    return any(p in lowered for p in phrases)


def user_says_unresolved(text: str) -> bool:
    """True when the user says the suggested fix did not work."""
    lowered = (text or "").lower().strip()
    phrases = (
        "not solved",
        "not fixed",
        "still broken",
        "still failing",
        "still not working",
        "still doesn't work",
        "still does not work",
        "didn't work",
        "did not work",
        "doesn't work",
        "does not work",
        "no luck",
        "same issue",
        "same problem",
        "didn't help",
        "did not help",
        "unresolved",
        "not working",
    )
    return any(p in lowered for p in phrases)


def triage_others_with_llm(
    user_text: str,
    *,
    catalog: dict | None = None,
    history: list[dict[str, str]] | None = None,
    timeout_sec: float = 45.0,
) -> dict[str, Any] | None:
    """Return normalized triage dict or None on failure / no key."""
    global LAST_ERROR
    LAST_ERROR = None
    cfg = _settings()
    if not cfg["api_key"]:
        LAST_ERROR = "OPENAI_API_KEY/GROQ_API_KEY not set"
        return None
    text = (user_text or "").strip()
    if not text:
        return None

    messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt(catalog)}]
    for turn in (history or [])[-10:]:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": text})

    payload: dict[str, Any] = {
        "model": cfg["model_id"],
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 900,
    }
    attempts = (
        {**payload, "response_format": {"type": "json_object"}},
        payload,
    )

    last_err = "unknown"
    for body_obj in attempts:
        body = json.dumps(body_obj).encode("utf-8")
        req = urllib.request.Request(
            f"{cfg['base_url']}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "HELIO-BakeryOthers/1.0 (+https://localhost; OpenAI-compatible client)",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:  # noqa: BLE001
                detail = str(exc)
            last_err = f"HTTP {exc.code}: {detail}"
            logger.warning("others_llm HTTP error: %s", last_err)
            if exc.code in (400, 404, 415, 422):
                continue
            LAST_ERROR = last_err
            return None
        except (urllib.error.URLError, TimeoutError) as exc:
            last_err = f"{type(exc).__name__}: {exc}"
            logger.warning("others_llm network error: %s", last_err)
            LAST_ERROR = last_err
            return None
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
            logger.warning("others_llm unexpected error: %s", last_err)
            LAST_ERROR = last_err
            return None

        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            last_err = "malformed chat.completions response"
            continue
        parsed = _extract_json(content if isinstance(content, str) else str(content))
        if not parsed:
            last_err = "model response was not valid JSON"
            continue
        normalized = _normalize(parsed)
        if not normalized:
            last_err = "model JSON missing branch/message"
            continue
        LAST_ERROR = None
        return normalized

    LAST_ERROR = last_err
    return None
