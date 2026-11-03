"""Deterministic guided conversation engine driven by guided_flow_catalog.json."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    ActionIntent,
    Application,
    ApprovalRequest,
    Case,
    Conversation,
    Message,
    Ticket,
)
from ..routers.catalog import load_catalog
from .diagnosis import diagnose_issue


from ..routing import route_owner, route_team
from .others_llm import LAST_ERROR as OTHERS_LLM_LAST_ERROR
from .others_llm import (
    llm_configured,
    triage_others_with_llm,
    user_requests_ticket,
    user_says_resolved,
    user_says_unresolved,
)


def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


class GuidedEngine:
    def __init__(self, db: Session, tenant_id: str, user_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.catalog = load_catalog()

    def create_conversation(self) -> str:
        conversation_id = generate_id("CONV")
        self.db.add(
            Conversation(
                conversation_id=conversation_id,
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                state="WELCOME",
            )
        )
        self.db.commit()
        return conversation_id

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.execute(
            select(Conversation).where(
                Conversation.conversation_id == conversation_id,
                Conversation.tenant_id == self.tenant_id,
                Conversation.user_id == self.user_id,
            )
        ).scalar_one_or_none()

    def get_active_conversation(self) -> Optional[Conversation]:
        """Prefer in-progress chat over a fresh WELCOME created by a bad refresh."""
        rows = self.db.execute(
            select(Conversation)
            .where(
                Conversation.tenant_id == self.tenant_id,
                Conversation.user_id == self.user_id,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(25)
        ).scalars().all()
        if not rows:
            return None

        def _is_in_progress(c: Conversation) -> bool:
            if (c.state or "") not in ("", "WELCOME"):
                return True
            snap = c.ui_snapshot or {}
            snap_state = (snap.get("state") or "") if isinstance(snap, dict) else ""
            if snap_state and snap_state not in ("WELCOME",):
                return True
            # Any user message means the chat progressed
            msg_count = self.db.execute(
                select(Message)
                .where(
                    Message.conversation_id == c.conversation_id,
                    Message.role == "user",
                )
                .limit(1)
            ).scalars().first()
            return msg_count is not None

        for c in rows:
            if _is_in_progress(c):
                return c
        return rows[0]

    def save_ui_snapshot(self, conversation_id: str, payload: dict) -> None:
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return
        # Persist a JSON-safe copy of the last turn for refresh resume
        snapshot = {k: v for k, v in (payload or {}).items() if k != "ui_snapshot"}
        conversation.ui_snapshot = snapshot
        # Touch updated_at so in-progress chats stay "active"
        conversation.updated_at = datetime.now(timezone.utc)
        self.db.commit()

    def list_messages(self, conversation_id: str, limit: int = 80) -> list[dict]:
        rows = self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc(), Message.id.asc())
            .limit(limit)
        ).scalars().all()
        return [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            }
            for m in rows
        ]

    def resume_conversation(self, conversation_id: str) -> Optional[dict]:
        """Return last UI snapshot + message history for the same chat."""
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        snapshot = dict(conversation.ui_snapshot or {})
        # Never invent a fresh welcome over an in-progress state
        if not snapshot or not snapshot.get("assistant_message"):
            snapshot = {
                "conversation_id": conversation.conversation_id,
                "state": conversation.state or "WELCOME",
                "case_id": conversation.current_case,
                "assistant_message": "",
                "options": [],
                "controls": ["start_over"],
                "allow_free_text": (conversation.state or "")
                in (
                    "DESCRIBING_OTHER",
                    "AWAITING_TICKET_DETAILS",
                    "AWAITING_UNKNOWN_TICKET_CONFIRM",
                ),
                "demo_mode": True,
            }
            if (conversation.state or "") == "WELCOME":
                snapshot = self._welcome(conversation_id)
            elif (conversation.state or "") == "DESCRIBING_OTHER":
                snapshot.update(
                    {
                        "assistant_message": (
                            "Welcome back — continue describing your issue, "
                            "or use the options below."
                        ),
                        "allow_free_text": True,
                        "free_text_hint": "Continue the conversation…",
                        "free_text_submit_label": "Send",
                        "options": [
                            {
                                "id": "others_raise_ticket",
                                "label": "Raise a ticket",
                                "type": "action",
                            },
                            {
                                "id": "others_main_menu",
                                "label": "Back to main menu",
                                "type": "action",
                            },
                        ],
                    }
                )
        snapshot["conversation_id"] = conversation.conversation_id
        snapshot["state"] = conversation.state or snapshot.get("state")
        snapshot["case_id"] = conversation.current_case or snapshot.get("case_id")
        snapshot["messages"] = self.list_messages(conversation_id)
        snapshot["resumed"] = True
        return snapshot

    def add_message(self, conversation_id: str, role: str, content: str):
        self.db.add(
            Message(
                message_id=generate_id("MSG"),
                conversation_id=conversation_id,
                role=role,
                content=content,
            )
        )
        self.db.commit()

    def find_option_in_catalog(self, option_id: str) -> Optional[dict]:
        for opt in self.catalog.get("root_options", []):
            if opt.get("id") == option_id:
                return opt
            for child in opt.get("children", []):
                if child.get("id") == option_id:
                    return child
                for grandchild in child.get("children", []):
                    if grandchild.get("id") == option_id:
                        return grandchild
        for issue in self.catalog.get("issues", []):
            if issue.get("issue_code") == option_id:
                return {**issue, "type": "issue", "id": option_id, "label": issue.get("label")}
        for g in self.catalog.get("global_options", []):
            if g.get("id") == option_id:
                return g
        return None

    def get_children_options(self, option_id: str) -> list[dict]:
        option = self.find_option_in_catalog(option_id)
        if option and "children" in option:
            return option["children"]
        return []

    def find_issue_by_code(self, issue_code: str) -> Optional[dict]:
        for issue in self.catalog.get("issues", []):
            if issue.get("issue_code") == issue_code:
                return issue
        return None

    def _anything_else_options(self) -> list[dict]:
        return [
            {
                "id": "anything_else_yes",
                "label": "Yes, I have another issue",
                "type": "answer",
            },
            {
                "id": "anything_else_no",
                "label": "No, I'm done for now",
                "type": "answer",
            },
        ]

    def _others_option(self) -> Optional[dict]:
        """Return the catalog 'Others' / cant_find global option, if present."""
        for g in self.catalog.get("global_options", []):
            if not isinstance(g, dict):
                continue
            oid = (g.get("id") or "").lower()
            label = (g.get("label") or "").strip().lower()
            if oid in ("cant_find", "others") or label == "others":
                return dict(g)
        return {
            "id": "cant_find",
            "label": "Others",
            "type": "fallback",
        }

    def _category_picker_options(self) -> list[dict]:
        """Root categories plus Others — used for welcome rematch / cancel pickers."""
        options = [dict(o) for o in self.catalog.get("root_options", []) if isinstance(o, dict)]
        existing = {(o.get("id") or "").lower() for o in options}
        others = self._others_option()
        if others and (others.get("id") or "").lower() not in existing:
            options.append(others)
        return options

    _TICKET_OPTION_IDS = frozenset(
        {"open_ticket", "confirm_raise_ticket", "still_failing"}
    )

    def _options_offer_ticket(self, options: list | None) -> bool:
        for opt in options or []:
            if not isinstance(opt, dict):
                continue
            oid = (opt.get("id") or "").lower()
            label = (opt.get("label") or "").lower()
            if oid in self._TICKET_OPTION_IDS:
                return True
            if "raise a ticket" in label or "open ticket" in label or "open support ticket" in label:
                return True
        return False

    def _attach_ticket_complaint_box(self, result: dict) -> dict:
        """Show a small complaint text box whenever raise-ticket is offered."""
        if not result or result.get("session_locked") or result.get("state") == "CLOSED":
            return result
        if result.get("allow_free_text"):
            result.setdefault("free_text_hint", "Enter your complaint…")
            if result.get("state") == "DESCRIBING_OTHER":
                result.setdefault("free_text_submit_label", "Send")
            else:
                result.setdefault("free_text_submit_label", "Raise ticket")
            return result
        if self._options_offer_ticket(result.get("options")) or result.get("state") in (
            "AWAITING_TICKET_DETAILS",
            "AWAITING_UNKNOWN_TICKET_CONFIRM",
        ):
            result["allow_free_text"] = True
            result.setdefault("free_text_hint", "Enter your complaint…")
            result.setdefault("free_text_submit_label", "Raise ticket")
        elif result.get("state") == "DESCRIBING_OTHER":
            result["allow_free_text"] = True
            result.setdefault("free_text_hint", "Describe your issue…")
            result.setdefault("free_text_submit_label", "Send")
        return result

    def _prompt_ticket_complaint(
        self,
        conversation: Conversation,
        *,
        intent: str = "support",
        message: str | None = None,
    ) -> dict:
        """Ask the user to type a short complaint before raising a ticket."""
        case = self._get_case(conversation)
        if case is not None:
            facts = dict(case.collected_facts or {})
            facts["ticket_intent"] = intent
            case.collected_facts = facts
        conversation.state = "AWAITING_TICKET_DETAILS"
        self.db.commit()
        return {
            "conversation_id": conversation.conversation_id,
            "case_id": conversation.current_case,
            "state": "AWAITING_TICKET_DETAILS",
            "assistant_message": message
            or (
                "Please enter a short description of your complaint in the box below, "
                "then raise a ticket."
            ),
            "options": [
                {"id": "open_ticket", "label": "Raise a ticket", "type": "action"},
            ],
            "controls": ["back", "start_over", "talk_to_it"],
            "allow_free_text": True,
            "free_text_hint": "Enter your complaint…",
            "free_text_submit_label": "Raise ticket",
            "demo_mode": True,
        }

    def _infer_selection_mode(self, state: str | None, options: list | None) -> str:
        opts = options or []
        if not opts:
            return "single"
        types = {o.get("type") for o in opts if isinstance(o, dict)}
        # Explicit multi-select checklists / symptoms
        if any(o.get("type") in ("checklist", "symptom", "multi") for o in opts if isinstance(o, dict)):
            return "multiple"
        if state in ("COLLECTING_CHECKLIST", "MULTI_SELECT"):
            return "multiple"
        # Mutually exclusive navigation / yes-no / actions → single
        if types & {"category", "submenu", "issue", "action", "control", "answer"}:
            return "single"
        return "single"

    def _decorate(
        self,
        result: dict,
        *,
        selection_mode: str | None = None,
        ask_anything_else: bool = False,
    ) -> dict:
        """Attach select+confirm UX metadata; optionally append Anything else?"""
        if not result or result.get("error"):
            return result

        options = list(result.get("options") or [])
        state = result.get("state")

        if ask_anything_else:
            # Replace terminal options with Anything else? (keep ticket/finding cards)
            result["assistant_message"] = (
                (result.get("assistant_message") or "").rstrip()
                + "\n\nIs there anything else I can help you with?"
            )
            options = self._anything_else_options()
            state = result.get("state") or "ASKING_ANYTHING_ELSE"
            result["state"] = "ASKING_ANYTHING_ELSE" if state == "CASE_SUMMARY" else state

        mode = selection_mode or result.get("selection_mode") or self._infer_selection_mode(
            result.get("state"), options
        )
        result["options"] = options
        result["selection_mode"] = mode  # "single" | "multiple"
        result["require_confirm"] = bool(options)
        result["confirm_label"] = "Confirm selection"
        result["selection_hint"] = (
            "Select one option, then Confirm."
            if mode == "single"
            else "Select all that apply, then Confirm."
        )
        result.setdefault("demo_mode", True)
        result.setdefault("controls", result.get("controls") or ["start_over", "talk_to_it"])
        return self._attach_ticket_complaint_box(result)

    def _opening_catalog_options(self) -> list[dict]:
        """Root + global options for the welcome picker (excludes retired 'I'm not sure')."""
        options: list[dict] = []
        for opt in self.catalog.get("root_options", []) or []:
            if isinstance(opt, dict):
                options.append(dict(opt))
        for opt in self.catalog.get("global_options", []) or []:
            if not isinstance(opt, dict):
                continue
            oid = (opt.get("id") or "").lower()
            label = (opt.get("label") or "").strip().lower()
            # Opening catalog no longer offers the unsure / triage shortcut.
            if oid == "not_sure" or label in ("i'm not sure", "i’m not sure", "im not sure"):
                continue
            options.append(dict(opt))
        return options

    def _welcome(self, conversation_id: str, *, assistant_message: str | None = None) -> dict:
        return self._decorate(
            {
                "conversation_id": conversation_id,
                "state": "WELCOME",
                "assistant_message": assistant_message
                or self.catalog.get(
                    "intro",
                    "Hi! I'm your IT support assistant. What would you like help with today?",
                ),
                "breadcrumb": [],
                "options": self._opening_catalog_options(),
                "controls": ["start_over", "talk_to_it"],
                "finding": None,
                "action_proposal": None,
                "ticket": None,
                "demo_mode": True,
            },
            selection_mode="single",
        )

    def _session_closed(self, conversation_id: str) -> dict:
        return {
            "conversation_id": conversation_id,
            "state": "CLOSED",
            "assistant_message": (
                "You're all set. I've noted that we're done for now. "
                "Come back anytime if something else comes up. (Demo Mode)"
            ),
            "options": [],
            "controls": ["start_over"],
            "allow_free_text": False,
            "session_locked": True,
            "demo_mode": True,
        }

    def process_turn(
        self,
        conversation_id: str,
        option_id: Optional[str] = None,
        option_ids: Optional[list[str]] = None,
        free_text: Optional[str] = None,
        control: Optional[str] = None,
    ) -> dict:
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return {"error": "Conversation not found"}

        # Normalize confirmed selections (single or multi)
        selected_ids = [i for i in (option_ids or []) if i]
        if option_id and option_id not in selected_ids:
            selected_ids = [option_id] + selected_ids
        primary = selected_ids[0] if selected_ids else None

        # Locked after Others ticket: only Start over may continue
        if conversation.state == "CLOSED":
            if control == "start_over" or primary == "start_over":
                return self._decorate(self._handle_control(conversation, "start_over"))
            return {
                **self._session_closed(conversation_id),
                "assistant_message": (
                    "This chat is closed. Use Start over if you have a new request."
                ),
            }

        if control:
            return self._decorate(self._handle_control(conversation, control))

        # Anything else follow-ups
        if primary == "anything_else_yes":
            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            conversation.current_case = None
            self.db.commit()
            welcome = self._welcome(conversation_id)
            welcome["assistant_message"] = (
                "Sure. Let's look at the next issue. What would you like help with?"
            )
            return welcome

        if primary == "anything_else_no":
            conversation.state = "CLOSED"
            self.db.commit()
            return self._session_closed(conversation_id)

        if primary == "start_over":
            return self._decorate(self._handle_control(conversation, "start_over"))

        # Multi-select clarification checklist → proceed if any affirmative
        if (
            len(selected_ids) > 1
            and conversation.current_case
            and all(
                i in ("yes", "no", "not_sure", "not_listed")
                or i.startswith(("symptom_", "chk_", "choice_"))
                for i in selected_ids
            )
        ):
            chosen = [
                i
                for i in selected_ids
                if i.startswith(("symptom_", "chk_", "choice_")) or i in ("yes", "not_sure")
            ]
            if chosen:
                label = ", ".join(chosen)
                return self._decorate(
                    self._handle_clarification_answer(
                        conversation, "yes", choice_label=label
                    )
                )
            return self._decorate(self._handle_clarification_answer(conversation, "no"))

        # Concrete clarifier choice (folder / app / hardware / etc.)
        if conversation.current_case and primary and (
            primary.startswith("choice_") or primary == "not_listed"
        ):
            if primary == "not_listed":
                conversation.state = "COLLECTING_FACTS"
                self.db.commit()
                return self._decorate(
                    {
                        "conversation_id": conversation_id,
                        "case_id": conversation.current_case,
                        "state": "COLLECTING_FACTS",
                        "assistant_message": (
                            "No problem. Type the exact name or describe what you need, then send."
                        ),
                        "options": [],
                        "controls": ["back", "start_over", "something_else", "talk_to_it"],
                        "demo_mode": True,
                    }
                )
            issue = self.find_issue_by_code(conversation.current_menu_node or "")
            label = primary
            if issue:
                opts, _, _ = self._build_clarifying_prompt(issue)
                match = next((o for o in opts if o.get("id") == primary), None)
                if match:
                    label = match.get("label") or primary
            return self._decorate(
                self._handle_clarification_answer(
                    conversation, primary, choice_label=label
                )
            )

        if primary in ("yes", "no", "not_sure") and conversation.current_case:
            return self._decorate(
                self._handle_clarification_answer(conversation, primary)
            )

        if primary == "consent_execute" and conversation.current_case:
            result = self._handle_consent(conversation)
            # After wait/execute, ask anything else when terminal
            ask = result.get("state") in (
                "WAITING_APPROVAL",
                "CASE_SUMMARY",
                "AWAITING_USER_CONFIRMATION",
            )
            # Keep confirmation choices on AWAITING_USER_CONFIRMATION
            if result.get("state") == "AWAITING_USER_CONFIRMATION":
                return self._decorate(result, selection_mode="single")
            if result.get("state") == "WAITING_APPROVAL":
                return self._decorate(
                    {
                        **result,
                        "assistant_message": (
                            result.get("assistant_message", "")
                            + "\n\nI've finished this step. Is there anything else I can help with while you wait?"
                        ),
                        "options": self._anything_else_options(),
                        "state": "ASKING_ANYTHING_ELSE",
                    },
                    selection_mode="single",
                )
            return self._decorate(result, ask_anything_else=ask)

        if primary == "yes_resolved":
            conversation.state = "ASKING_ANYTHING_ELSE"
            self.db.commit()
            return self._decorate(
                {
                    "conversation_id": conversation_id,
                    "case_id": conversation.current_case,
                    "state": "ASKING_ANYTHING_ELSE",
                    "assistant_message": (
                        "Great. Based on your confirmation, this issue looks resolved in Demo Mode. "
                        "No further automated changes will be made for this case.\n\n"
                        "Is there anything else I can help you with?"
                    ),
                    "options": self._anything_else_options(),
                    "controls": ["start_over", "talk_to_it"],
                    "demo_mode": True,
                },
                selection_mode="single",
            )

        if primary == "still_failing":
            detail = (free_text or "").strip()
            if not detail:
                return self._decorate(
                    self._prompt_ticket_complaint(
                        conversation,
                        intent="still_failing",
                        message=(
                            "Sorry it is still not working. Enter your complaint below, "
                            "then raise a ticket so IT can follow up."
                        ),
                    )
                )
            return self._decorate(
                self.create_unknown_ticket(
                    conversation.conversation_id,
                    (
                        f"Issue persists after demo action for case "
                        f"{conversation.current_case or 'unknown'} "
                        f"/ node {conversation.current_menu_node}.\n"
                        f"User complaint: {detail}"
                    ),
                ),
                ask_anything_else=True,
            )

        if primary == "confirm_raise_ticket":
            if (free_text or "").strip():
                case = self._get_case(conversation)
                if case is not None:
                    facts = dict(case.collected_facts or {})
                    facts["pending_ticket_detail"] = free_text.strip()
                    case.collected_facts = facts
                    self.db.commit()
            result = self._confirm_unknown_ticket(conversation)
            if result.get("state") == "AWAITING_TICKET_DETAILS":
                return self._decorate(result)
            return self._decorate(result, ask_anything_else=True)

        if primary == "decline_raise_ticket":
            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            conversation.current_case = None
            self.db.commit()
            welcome = self._welcome(conversation_id)
            welcome["assistant_message"] = (
                "No problem. We won't open a ticket. What else can I help you with?"
            )
            return welcome

        if primary == "open_ticket":
            result = self._open_support_ticket(
                conversation, detail=(free_text or "").strip() or None
            )
            if result.get("state") == "AWAITING_TICKET_DETAILS":
                return self._decorate(result)
            return self._decorate(result, ask_anything_else=True)

        if primary in ("something_else", "cant_find", "describe_in_words", "others"):
            # Others path: free text → LLM (or rules) triage:
            # guide / offer ticket / out of scope → main menu.
            detail = (free_text or "").strip()
            if detail:
                return self._decorate(self._triage_others_text(conversation, detail))
            conversation.state = "DESCRIBING_OTHER"
            conversation.current_menu_node = "GEN-UNKNOWN"
            conversation.current_case = None
            self.db.commit()
            llm_note = (
                "I'll use the IT assistant to guide you when I can. "
                if llm_configured()
                else "I'll try to answer from our IT help topics. "
            )
            return self._decorate(
                {
                    "conversation_id": conversation_id,
                    "state": "DESCRIBING_OTHER",
                    "assistant_message": (
                        "No problem. Describe your issue in a sentence or two, then send. "
                        + llm_note
                        + "If it's relevant but I can't fix it here, I'll ask before raising a ticket. "
                        "Off-topic requests go back to the main menu."
                    ),
                    "options": [],
                    "controls": ["back", "start_over"],
                    "allow_free_text": True,
                    "free_text_hint": "Describe your issue…",
                    "free_text_submit_label": "Send",
                    "demo_mode": True,
                }
            )

        if primary == "others_raise_ticket":
            case = self._get_case(conversation)
            facts = dict((case.collected_facts if case else None) or {})
            detail = (
                (free_text or "").strip()
                or facts.get("pending_ticket_detail")
                or facts.get("others_last_user_text")
                or "User requested a ticket from Others guidance"
            )
            return self._decorate(self._offer_unknown_ticket(conversation, detail))

        if primary == "others_main_menu":
            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            conversation.current_case = None
            self.db.commit()
            return self._welcome(
                conversation_id,
                assistant_message="Back to the main menu. What can I help you with?",
            )

        # Retired opening option — keep a soft redirect if an old client still sends it.
        if primary == "not_sure" and not conversation.current_case:
            conversation.state = "DESCRIBING_OTHER"
            conversation.current_menu_node = "GEN-UNKNOWN"
            conversation.current_case = None
            self.db.commit()
            return self._decorate(
                {
                    "conversation_id": conversation_id,
                    "state": "DESCRIBING_OTHER",
                    "assistant_message": (
                        "No worries — describe what you need help with in a sentence or two. "
                        "I'll try to answer, or ask before raising a ticket."
                    ),
                    "options": [],
                    "controls": ["back", "start_over"],
                    "allow_free_text": True,
                    "free_text_hint": "Describe your issue…",
                    "free_text_submit_label": "Send",
                    "demo_mode": True,
                }
            )

        if primary in ("my_tickets", "my_existing_tickets"):
            return self._decorate(
                {
                    "conversation_id": conversation_id,
                    "state": conversation.state,
                    "assistant_message": (
                        "Our support team is working on your tickets and we'll get back to you shortly. "
                        "Is there anything else I can help with here?"
                    ),
                    "options": self._anything_else_options(),
                    "controls": ["start_over", "talk_to_it"],
                    "demo_mode": True,
                },
                selection_mode="single",
            )

        if primary:
            selected = self.find_option_in_catalog(primary)
            if not selected:
                return {"error": "Invalid option", "conversation_id": conversation_id}

            if selected.get("type") == "submenu" or (
                selected.get("children") and selected.get("type") != "issue"
            ):
                conversation.current_menu_node = primary
                conversation.state = "CHOOSING_SUBCATEGORY"
                self.db.commit()
                children = self.get_children_options(primary)
                if children and children[0].get("type") == "issue":
                    conversation.state = "CHOOSING_SYMPTOM"
                    self.db.commit()
                return self._decorate(
                    {
                        "conversation_id": conversation_id,
                        "state": conversation.state,
                        "assistant_message": (
                            "Select the option that best matches your issue, then press Confirm."
                        ),
                        "breadcrumb": [selected.get("label")],
                        "options": children,
                        "controls": ["back", "start_over", "something_else", "talk_to_it"],
                        "demo_mode": True,
                    },
                    selection_mode="single",
                )

            if selected.get("type") == "issue" or primary.startswith(
                ("ID-", "NET-", "DEV-", "APP-", "PRINT-", "SEC-", "HW-", "REQ-")
            ):
                return self._decorate(self._start_issue(conversation, primary))

            if selected.get("type") in ("fallback", "triage", "free_text", "ticket_lookup"):
                return self.process_turn(
                    conversation_id, option_id=selected.get("id"), free_text=None, control=None
                )

        if free_text:
            result = self._handle_free_text(conversation, free_text)
            # Others path locks the chat — do not append "Anything else?"
            if result.get("session_locked") or result.get("state") == "CLOSED":
                return result
            # Other ticket summaries may offer Anything else?; matched issues continue flow
            ask = result.get("state") == "CASE_SUMMARY" or bool(result.get("ticket"))
            return self._decorate(result, ask_anything_else=ask)

        return self._welcome(conversation_id)

    def _handle_control(self, conversation: Conversation, control: str) -> dict:
        cid = conversation.conversation_id
        if control == "start_over":
            from sqlalchemy import delete as sa_delete

            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            conversation.current_case = None
            conversation.ui_snapshot = {}
            # Clear message history so Start over is a clean chat
            self.db.execute(sa_delete(Message).where(Message.conversation_id == cid))
            self.db.commit()
            return self._welcome(cid)
        if control == "back":
            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            self.db.commit()
            return self._welcome(cid)
        if control == "talk_to_it":
            return self._prompt_ticket_complaint(
                conversation,
                intent="escalate",
                message=(
                    "I'll connect you with IT. Enter a short description of your complaint "
                    "below, then raise a ticket."
                ),
            )
        if control == "something_else":
            return self.process_turn(cid, option_id="cant_find")
        if control == "cancel":
            conversation.state = "WELCOME"
            self.db.commit()
            return {
                "conversation_id": cid,
                "state": "WELCOME",
                "assistant_message": "Cancelled. No change was made.",
                "options": self._category_picker_options(),
                "controls": ["start_over", "talk_to_it"],
                "demo_mode": True,
            }
        return self._welcome(cid)

    def _yes_no_options(self) -> list[dict]:
        return [
            {"id": "yes", "label": "Yes", "type": "answer"},
            {"id": "no", "label": "No", "type": "answer"},
            {"id": "not_sure", "label": "Not sure", "type": "answer"},
        ]

    def _is_yes_no_question(self, question: str) -> bool:
        q = (question or "").strip().lower()
        return q.startswith(
            (
                "do ",
                "does ",
                "is ",
                "are ",
                "have ",
                "has ",
                "can ",
                "could ",
                "did ",
                "will ",
                "would ",
                "was ",
                "were ",
            )
        )

    def _tenant_apps(self, *, self_install_only: bool | None = None) -> list[Application]:
        stmt = select(Application).where(Application.tenant_id == self.tenant_id)
        apps = list(self.db.execute(stmt).scalars().all())
        if self_install_only is True:
            apps = [a for a in apps if a.allowed_to_self_install]
        elif self_install_only is False:
            apps = [a for a in apps if not a.allowed_to_self_install]
        return apps

    def _build_clarifying_prompt(self, issue: dict) -> tuple[list[dict], str, str]:
        """
        Build clarifying options that match the question.
        Returns (options, selection_mode, state).
        """
        question = issue.get("clarifying_question") or ""
        code = issue.get("issue_code") or ""
        ql = question.lower()

        # Catalogue-provided options win
        raw = issue.get("clarifying_options") or issue.get("answer_options") or issue.get("symptoms")
        if isinstance(raw, list) and raw:
            options: list[dict] = []
            for i, item in enumerate(raw):
                if isinstance(item, dict):
                    options.append(
                        {
                            "id": item.get("id") or f"choice_{i}",
                            "label": item.get("label") or str(item),
                            "type": item.get("type") or "choice",
                        }
                    )
                else:
                    options.append(
                        {"id": f"choice_{i}", "label": str(item), "type": "choice"}
                    )
            mode = "multiple" if any(o.get("type") in ("checklist", "symptom", "multi") for o in options) else "single"
            if mode == "multiple":
                options.extend(
                    [
                        {"id": "yes", "label": "These match: continue", "type": "answer"},
                        {"id": "no", "label": "None of these", "type": "answer"},
                    ]
                )
                return options, "multiple", "COLLECTING_CHECKLIST"
            options.append(
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"}
            )
            return options, "single", "COLLECTING_FACTS"

        # Shared folder / group (REQ-03)
        if code == "REQ-03" or "shared folder" in ql or "shared drive" in ql or "or group" in ql:
            folders = [
                ("finance", "Finance Shared (/Finance)"),
                ("hr", "HR Policies (/HR)"),
                ("helio", "Project Helio (/Projects/Helio)"),
                ("marketing", "Marketing Assets (/Marketing)"),
                ("engineering", "Engineering Source (/Eng)"),
                ("public", "All-Company Public"),
            ]
            options = [
                {"id": f"choice_folder_{k}", "label": label, "type": "choice"}
                for k, label in folders
            ]
            options.append(
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"}
            )
            return options, "single", "COLLECTING_FACTS"

        # Which application… (ID-06, APP-01, APP-04, etc.)
        if code in ("ID-06", "APP-01", "APP-04") or (
            "which application" in ql and "approved" not in ql and "unapproved" not in ql
        ):
            apps = self._tenant_apps()
            options = [
                {
                    "id": f"choice_app_{a.app_id.split(':')[-1]}",
                    "label": a.app_name,
                    "type": "choice",
                }
                for a in apps[:12]
            ]
            if not options:
                options = [
                    {"id": "choice_app_jira", "label": "Jira", "type": "choice"},
                    {"id": "choice_app_outlook", "label": "Outlook", "type": "choice"},
                    {"id": "choice_app_teams", "label": "Microsoft Teams", "type": "choice"},
                ]
            options.append(
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"}
            )
            return options, "single", "COLLECTING_FACTS"

        # REQ-01 approved install
        if code == "REQ-01" or "approved application" in ql:
            apps = self._tenant_apps(self_install_only=True) or self._tenant_apps()
            options = [
                {
                    "id": f"choice_app_{a.app_id.split(':')[-1]}",
                    "label": f"{a.app_name} (approved)",
                    "type": "choice",
                }
                for a in apps[:10]
            ]
            options.append(
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"}
            )
            return options, "single", "COLLECTING_FACTS"

        # REQ-02 restricted software
        if code == "REQ-02" or "unapproved application" in ql:
            apps = self._tenant_apps(self_install_only=False)
            options = [
                {
                    "id": f"choice_app_{a.app_id.split(':')[-1]}",
                    "label": f"{a.app_name} (requires approval)",
                    "type": "choice",
                }
                for a in apps[:10]
            ] or [
                {"id": "choice_app_custom", "label": "Custom / third-party tool", "type": "choice"}
            ]
            options.append(
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"}
            )
            return options, "single", "COLLECTING_FACTS"

        # REQ-04 hardware
        if code == "REQ-04" or "device or accessory" in ql or "company device" in ql:
            options = [
                {"id": "choice_hw_laptop", "label": "Replacement laptop", "type": "choice"},
                {"id": "choice_hw_monitor", "label": "External monitor", "type": "choice"},
                {"id": "choice_hw_headset", "label": "Headset / webcam", "type": "choice"},
                {"id": "choice_hw_keyboard", "label": "Keyboard / mouse", "type": "choice"},
                {"id": "choice_hw_dock", "label": "Docking station", "type": "choice"},
                {"id": "not_listed", "label": "Something else / not listed", "type": "choice"},
            ]
            return options, "single", "COLLECTING_FACTS"

        # Printer / device which-questions without catalogue lists
        if question.strip().lower().startswith("which "):
            return (
                [
                    {
                        "id": "yes",
                        "label": "Continue: I'll describe the details next",
                        "type": "answer",
                    },
                    {"id": "not_listed", "label": "Type the exact name myself", "type": "choice"},
                    {"id": "no", "label": "Wrong issue: go back", "type": "answer"},
                ],
                "single",
                "COLLECTING_FACTS",
            )

        # Default: yes/no clarifying questions
        if self._is_yes_no_question(question):
            return self._yes_no_options(), "single", "COLLECTING_FACTS"

        return self._yes_no_options(), "single", "COLLECTING_FACTS"

    def _persist_clarifying_choice(self, conversation: Conversation, choice_id: str, label: str):
        if not conversation.current_case:
            return
        case = self.db.execute(
            select(Case).where(Case.case_id == conversation.current_case)
        ).scalar_one_or_none()
        if not case:
            return
        facts = dict(case.collected_facts or {})
        facts["clarifying_choice_id"] = choice_id
        facts["clarifying_choice_label"] = label
        case.collected_facts = facts
        self.db.commit()

    def _start_issue(self, conversation: Conversation, issue_code: str) -> dict:
        issue = self.find_issue_by_code(issue_code)
        if not issue:
            return {"error": f"Unknown issue {issue_code}"}
        case_id = generate_id("CASE")
        self.db.add(
            Case(
                case_id=case_id,
                conversation_id=conversation.conversation_id,
                tenant_id=self.tenant_id,
                issue_code=issue_code,
                state="triaging",
            )
        )
        conversation.current_menu_node = issue_code
        conversation.current_case = case_id
        options, selection_mode, state = self._build_clarifying_prompt(issue)
        conversation.state = state
        self.db.commit()

        prompt = issue.get("clarifying_question") or "Select the option that best matches, then Confirm."
        if any(o.get("type") == "choice" for o in options):
            prompt = f"{prompt}\n\nSelect one option below, then press Confirm."

        return {
            "conversation_id": conversation.conversation_id,
            "case_id": case_id,
            "state": state,
            "assistant_message": prompt,
            "breadcrumb": [
                issue.get("category"),
                issue.get("subcategory"),
                issue.get("label"),
            ],
            "options": options,
            "selection_mode": selection_mode,
            "controls": ["back", "start_over", "something_else", "talk_to_it"],
            "demo_mode": True,
        }

    def _handle_clarification_answer(
        self,
        conversation: Conversation,
        answer: str,
        *,
        choice_label: str | None = None,
    ) -> dict:
        issue_code = conversation.current_menu_node
        issue = self.find_issue_by_code(issue_code or "")
        if not issue:
            return self.create_unknown_ticket(conversation.conversation_id, f"Answer={answer}")

        if answer == "no":
            return {
                "conversation_id": conversation.conversation_id,
                "case_id": conversation.current_case,
                "state": "CHOOSING_SYMPTOM",
                "assistant_message": (
                    "Thanks. That may not be the right match. Pick another category or describe the problem."
                ),
                "options": self._category_picker_options(),
                "controls": ["back", "start_over", "something_else", "talk_to_it"],
                "demo_mode": True,
            }

        if choice_label:
            self._persist_clarifying_choice(conversation, answer, choice_label)

        conversation.state = "INVESTIGATING"
        self.db.commit()
        result = diagnose_issue(
            self.db, self.tenant_id, self.user_id, issue_code, issue
        )
        result["conversation_id"] = conversation.conversation_id
        result["case_id"] = conversation.current_case
        result["breadcrumb"] = [
            issue.get("category"),
            issue.get("subcategory"),
            issue.get("label"),
        ]
        result["demo_mode"] = True
        if choice_label:
            finding = dict(result.get("finding") or {})
            obs = list(finding.get("observations") or [])
            obs.insert(
                0,
                {
                    "field": "user_selection",
                    "value": choice_label,
                    "source": "guided_clarifier",
                },
            )
            finding["observations"] = obs
            result["finding"] = finding
            if result.get("assistant_message"):
                result["assistant_message"] = (
                    f"Got it. You selected **{choice_label}**.\n\n"
                    + result["assistant_message"]
                )
        conversation.state = result.get("state", "SHOWING_FINDING")
        conversation.current_menu_node = issue_code
        case = self.db.execute(
            select(Case).where(Case.case_id == conversation.current_case)
        ).scalar_one_or_none()
        if case:
            case.diagnosis = {
                "finding": result.get("finding"),
                "action_proposal": result.get("action_proposal"),
                "selected_clarifier": choice_label,
            }
            if result.get("action_proposal"):
                case.state = "action_proposed"
            elif (result.get("finding") or {}).get("requires_ticket"):
                case.state = "awaiting_ticket"
        self.db.commit()
        return result

    def _latest_proposal(self, conversation: Conversation) -> Optional[dict]:
        if not conversation.current_case:
            return None
        case = self.db.execute(
            select(Case).where(Case.case_id == conversation.current_case)
        ).scalar_one_or_none()
        if case and isinstance(case.diagnosis, dict):
            return case.diagnosis.get("action_proposal")
        return None

    def _handle_consent(self, conversation: Conversation) -> dict:
        proposal = self._latest_proposal(conversation)
        if not proposal:
            return {
                "conversation_id": conversation.conversation_id,
                "assistant_message": "No pending action proposal found.",
                "state": conversation.state,
                "options": [],
                "controls": ["start_over", "talk_to_it"],
                "demo_mode": True,
            }

        action_code = proposal["action_code"]
        target = proposal["target"]
        expected_version = proposal.get("expected_version")
        payload = proposal.get("payload") or {}
        action_id = generate_id("ACTION")
        idempotency_key = f"{self.user_id}:{action_code}:{target}:{conversation.current_case}"
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()

        # Idempotent reuse
        existing = self.db.execute(
            select(ActionIntent).where(
                ActionIntent.tenant_id == self.tenant_id,
                ActionIntent.idempotency_key == idempotency_key,
            )
        ).scalar_one_or_none()
        if existing:
            action_id = existing.action_id
            intent = existing
        else:
            intent = ActionIntent(
                action_id=action_id,
                tenant_id=self.tenant_id,
                actor=self.user_id,
                target=target,
                action_code=action_code,
                payload=payload,
                payload_sha256=payload_hash,
                expected_version=expected_version,
                idempotency_key=idempotency_key,
                expires_at=datetime.utcnow() + timedelta(hours=24),
                state="pending",
            )
            self.db.add(intent)
            self.db.commit()

        requires_approval = action_code in {
            "renew_mock_vpn_certificate",
            "request_entitlement_grant",
            "request_licence_assignment",
        }

        if requires_approval:
            approval_id = generate_id("APPR")
            self.db.add(
                ApprovalRequest(
                    approval_id=approval_id,
                    action_id=action_id,
                    required_role="it_engineer",
                    status="pending",
                    expiry=datetime.utcnow() + timedelta(hours=48),
                )
            )
            intent.state = "awaiting_approval"
            self.db.commit()
            conversation.state = "WAITING_APPROVAL"
            self.db.commit()
            return {
                "conversation_id": conversation.conversation_id,
                "case_id": conversation.current_case,
                "state": "WAITING_APPROVAL",
                "assistant_message": (
                    f"I've requested IT approval ({approval_id}). Your account/device has "
                    "**not** been changed yet. An IT engineer must approve before execution."
                ),
                "action_proposal": {**proposal, "action_id": action_id, "approval_id": approval_id},
                "options": [{"id": "start_over", "label": "Start over", "type": "control"}],
                "controls": ["start_over", "talk_to_it"],
                "demo_mode": True,
            }

        # Execute immediately after consent for non-approval actions
        from ..routers.actions import _execute_tool

        intent.state = "consented"
        self.db.commit()
        result = _execute_tool(
            db=self.db,
            action_code=action_code,
            tenant_id=self.tenant_id,
            actor=self.user_id,
            target=target,
            payload=payload,
            expected_version=expected_version,
            idempotency_key=idempotency_key,
        )
        ok = bool(result.get("success"))
        intent.state = "executed" if ok else "failed"
        self.db.commit()
        conversation.state = "AWAITING_USER_CONFIRMATION" if ok else "CASE_SUMMARY"
        self.db.commit()
        if ok:
            msg = (
                "DEMO MODE: the simulated change was applied and verified. "
                f"Details: {result.get('message') or result}. Did this solve your problem?"
            )
            options = [
                {"id": "yes_resolved", "label": "Yes, resolved", "type": "answer"},
                {"id": "still_failing", "label": "Still not working", "type": "answer"},
                {"id": "open_ticket", "label": "Open ticket", "type": "action"},
            ]
        else:
            msg = (
                f"The demo action did not complete successfully: {result.get('error') or result}. "
                "I have not claimed resolution. You can open a ticket."
            )
            options = [{"id": "open_ticket", "label": "Open support ticket", "type": "action"}]
        return {
            "conversation_id": conversation.conversation_id,
            "case_id": conversation.current_case,
            "state": conversation.state,
            "assistant_message": msg,
            "finding": {"execution_result": result, "verified": ok},
            "action_proposal": {**proposal, "action_id": action_id, "executed": ok},
            "options": options,
            "controls": ["start_over", "talk_to_it"],
            "demo_mode": True,
        }

    def _handle_free_text(self, conversation: Conversation, free_text: str) -> dict:
        detail = (free_text or "").strip()

        # Others / describe path: triage instead of auto-raising a ticket
        if conversation.state == "DESCRIBING_OTHER":
            return self._triage_others_text(conversation, detail)

        # Already mid-case (e.g. "not listed" clarifier) — use typed answer as selection
        if conversation.current_case and conversation.state in (
            "COLLECTING_FACTS",
            "COLLECTING_CHECKLIST",
        ):
            return self._handle_clarification_answer(
                conversation, "free_text", choice_label=detail
            )

        # Ticket complaint box — typed detail becomes the ticket body
        if conversation.state in ("AWAITING_TICKET_DETAILS", "SHOWING_FINDING"):
            case = self._get_case(conversation)
            intent = ((case.collected_facts or {}) if case else {}).get("ticket_intent") or "support"
            if intent == "escalate":
                return self.create_escalation_ticket(
                    conversation.conversation_id, detail=detail
                )
            if intent == "still_failing":
                return self.create_unknown_ticket(
                    conversation.conversation_id,
                    (
                        f"Issue persists after demo action for case "
                        f"{conversation.current_case or 'unknown'} "
                        f"/ node {conversation.current_menu_node}.\n"
                        f"User complaint: {detail}"
                    ),
                )
            return self._open_support_ticket(conversation, detail=detail)

        # Legacy confirm path — keep description, then raise
        if conversation.state == "AWAITING_UNKNOWN_TICKET_CONFIRM":
            case = self._get_case(conversation)
            if case is not None and detail:
                facts = dict(case.collected_facts or {})
                facts["pending_ticket_detail"] = detail
                case.collected_facts = facts
                self.db.commit()
            return self._confirm_unknown_ticket(conversation)

        # Free text from other states (e.g. welcome describe): same triage as Others
        return self._triage_others_text(conversation, detail)

    def _others_history(self, conversation: Conversation) -> list[dict[str, str]]:
        """Prior Others turns for multi-turn LLM guidance."""
        case = self._get_case(conversation)
        facts = dict((case.collected_facts if case else None) or {})
        history = facts.get("others_llm_history") or []
        if isinstance(history, list):
            return [h for h in history if isinstance(h, dict)][-8:]
        return []

    def _append_others_history(
        self, conversation: Conversation, user_text: str, assistant_text: str
    ) -> None:
        case = self._get_case(conversation)
        if case is None:
            case_id = generate_id("CASE")
            case = Case(
                case_id=case_id,
                conversation_id=conversation.conversation_id,
                tenant_id=self.tenant_id,
                issue_code="GEN-UNKNOWN",
                state="others_guiding",
                collected_facts={},
            )
            self.db.add(case)
            conversation.current_case = case_id
        facts = dict(case.collected_facts or {})
        history = list(facts.get("others_llm_history") or [])
        if user_text:
            history.append({"role": "user", "content": user_text})
        if assistant_text:
            history.append({"role": "assistant", "content": assistant_text})
        facts["others_llm_history"] = history[-12:]
        facts["others_last_user_text"] = user_text
        case.collected_facts = facts
        case.state = "others_guiding"
        self.db.commit()

    def _others_issue_detail(self, conversation: Conversation, fallback: str = "") -> str:
        facts_hist = self._others_history(conversation)
        for turn in facts_hist:
            if turn.get("role") == "user":
                content = (turn.get("content") or "").strip()
                if (
                    content
                    and not user_requests_ticket(content)
                    and not user_says_resolved(content)
                    and not user_says_unresolved(content)
                ):
                    # Prefer the original problem statement (first real issue text)
                    return content
        case = self._get_case(conversation)
        facts = dict((case.collected_facts if case else None) or {})
        return (
            facts.get("others_original_issue")
            or facts.get("others_last_user_text")
            or facts.get("pending_ticket_detail")
            or fallback
        )

    def _respond_others_resolved(
        self, conversation: Conversation, detail: str, message: str | None = None
    ) -> dict:
        self._append_others_history(
            conversation,
            detail,
            message or "Glad that resolved it.",
        )
        conversation.state = "WELCOME"
        conversation.current_menu_node = None
        conversation.current_case = None
        self.db.commit()
        return self._welcome(
            conversation.conversation_id,
            assistant_message=(
                (message or "Great — glad that resolved it.")
                + "\n\nBack to the main catalog. What else can I help with?"
            ),
        )

    def _triage_others_text(self, conversation: Conversation, detail: str) -> dict:
        """
        Others free-text:
        - First/guide: one solid solution + Raise ticket / Main menu / chat
        - Resolved → main menu
        - Unresolved / can't solve / user asks ticket → ticket confirm (+ main menu via decline)
        - Out of scope → main catalog
        """
        if not detail:
            conversation.state = "DESCRIBING_OTHER"
            self.db.commit()
            return {
                "conversation_id": conversation.conversation_id,
                "state": "DESCRIBING_OTHER",
                "assistant_message": (
                    "Please type a short description of the issue, then send."
                ),
                "options": [],
                "controls": ["back", "start_over"],
                "allow_free_text": True,
                "free_text_hint": "Describe your issue…",
                "free_text_submit_label": "Send",
                "demo_mode": True,
            }

        # Remember the original issue on first Others free-text
        if (
            not user_says_resolved(detail)
            and not user_requests_ticket(detail)
            and not user_says_unresolved(detail)
        ):
            case = self._get_case(conversation)
            if case is None:
                case_id = generate_id("CASE")
                case = Case(
                    case_id=case_id,
                    conversation_id=conversation.conversation_id,
                    tenant_id=self.tenant_id,
                    issue_code="GEN-UNKNOWN",
                    state="others_guiding",
                    collected_facts={"others_original_issue": detail},
                )
                self.db.add(case)
                conversation.current_case = case_id
                self.db.commit()
            else:
                facts = dict(case.collected_facts or {})
                if not facts.get("others_original_issue"):
                    facts["others_original_issue"] = detail
                    case.collected_facts = facts
                    self.db.commit()

        if user_says_resolved(detail):
            return self._respond_others_resolved(conversation, detail)

        if user_requests_ticket(detail) or user_says_unresolved(detail):
            ticket_detail = self._others_issue_detail(conversation, detail)
            return self._offer_unknown_ticket(
                conversation,
                ticket_detail,
                assistant_message=(
                    (
                        "Sorry that didn't fully resolve it. "
                        if user_says_unresolved(detail)
                        else "Understood — I can raise a support ticket for this.\n\n"
                    )
                    + f"Issue: {ticket_detail}\n\n"
                    "Would you like me to raise a ticket, or go back to the main menu?"
                ),
            )

        llm = triage_others_with_llm(
            detail,
            catalog=self.catalog,
            history=self._others_history(conversation),
        )
        if llm:
            branch = llm["branch"]
            message = llm["message"]
            issue_summary = llm.get("issue_summary") or self._others_issue_detail(
                conversation, detail
            )
            if branch == "resolved":
                return self._respond_others_resolved(conversation, detail, message)
            if branch == "guide":
                return self._respond_others_guide(conversation, detail, message)
            if branch == "out_of_scope":
                conversation.state = "WELCOME"
                conversation.current_menu_node = None
                conversation.current_case = None
                self.db.commit()
                return self._welcome(
                    conversation.conversation_id,
                    assistant_message=(
                        message
                        + "\n\nThat is out of scope for IT support, so I'm taking you back to the main catalog. "
                        "Pick an IT topic below, or open Others again for a workplace issue."
                    ),
                )
            ticket_detail = issue_summary if issue_summary else detail
            return self._offer_unknown_ticket(
                conversation,
                ticket_detail,
                assistant_message=(
                    message
                    + "\n\nI can raise a support ticket that mentions this issue, "
                    "or you can return to the main menu."
                ),
            )

        # LLM configured but failed → avoid brittle keyword→catalog mis-routes
        # (e.g. "restarting hasn't fixed it" ≠ DEV-04 Restart pending).
        if llm_configured():
            lowered = detail.lower()
            if self._looks_out_of_scope(lowered) and not self._looks_it_support(lowered):
                conversation.state = "WELCOME"
                conversation.current_menu_node = None
                conversation.current_case = None
                self.db.commit()
                return self._welcome(
                    conversation.conversation_id,
                    assistant_message=(
                        "That looks outside IT support (out of scope). "
                        "Would you like to choose from the issues listed here instead?"
                    ),
                )
            faq = self._match_demo_faq_answer(lowered)
            if faq:
                return self._respond_others_guide(conversation, detail, faq)
            err = (OTHERS_LLM_LAST_ERROR or "provider unavailable").strip()
            return self._offer_unknown_ticket(
                conversation,
                detail,
                assistant_message=(
                    "I couldn't reach the IT assistant just now "
                    f"({err[:160]}). "
                    "This still looks like a workplace IT issue I can't fully resolve here.\n\n"
                    f"Issue: {detail}\n\n"
                    "Are you OK if I raise a support ticket that mentions this issue?"
                ),
            )

        branch, payload = self._classify_others_query(detail)
        if branch == "answer":
            return self._respond_others_answer(conversation, detail, payload or {})
        if branch == "out_of_scope":
            conversation.state = "WELCOME"
            conversation.current_menu_node = None
            conversation.current_case = None
            self.db.commit()
            return self._welcome(
                conversation.conversation_id,
                assistant_message=(
                    "That looks outside IT support (out of scope). "
                    "Would you like to choose from the issues listed here instead?"
                ),
            )
        # Default: uncertain / cannot answer confidently → ask before ticketing
        return self._offer_unknown_ticket(conversation, detail)

    def _classify_others_query(self, free_text: str) -> tuple[str, dict | None]:
        """Rule fallback: (branch, payload) where branch is answer | offer_ticket | out_of_scope."""
        text = (free_text or "").strip()
        lowered = text.lower()
        if not lowered:
            return "offer_ticket", None

        if self._looks_out_of_scope(lowered):
            return "out_of_scope", None

        faq = self._match_demo_faq_answer(lowered)
        if faq:
            return "answer", {"kind": "faq", "message": faq}

        matched = self._match_free_text_to_issue(text)
        if matched:
            issue = self.find_issue_by_code(matched) or {}
            return "answer", {"kind": "catalog", "issue_code": matched, "issue": issue}

        if self._looks_it_support(lowered):
            return "offer_ticket", None

        # No IT signal and no catalog match → treat as out of scope
        return "out_of_scope", None

    def _looks_out_of_scope(self, lowered: str) -> bool:
        """Clear non-IT / off-topic steering away from helpdesk."""
        off_topic = (
            "weather",
            "forecast",
            "recipe",
            "cook ",
            "cooking",
            "sports",
            "football",
            "cricket",
            "movie",
            "netflix",
            "joke",
            "riddle",
            "horoscope",
            "dating",
            "girlfriend",
            "boyfriend",
            "stock price",
            "bitcoin",
            "crypto",
            "politics",
            "election",
            "poem",
            "lyrics",
            "homework math",
            "capital of",
            "who won the",
            "tell me a story",
            "play a game",
        )
        if any(p in lowered for p in off_topic):
            # Allow IT-flavoured exceptions (e.g. "crypto" in "encrypt")
            if self._looks_it_support(lowered) and not any(
                p in lowered
                for p in (
                    "weather",
                    "recipe",
                    "joke",
                    "sports",
                    "football",
                    "cricket",
                    "movie",
                    "dating",
                    "horoscope",
                    "politics",
                )
            ):
                return False
            return True
        return False

    def _looks_it_support(self, lowered: str) -> bool:
        it_terms = (
            "password",
            "login",
            "log in",
            "sign in",
            "signin",
            "account",
            "locked",
            "mfa",
            "2fa",
            "otp",
            "authenticator",
            "vpn",
            "wifi",
            "wi-fi",
            "network",
            "internet",
            "email",
            "outlook",
            "teams",
            "printer",
            "print",
            "laptop",
            "computer",
            "desktop",
            "disk",
            "storage",
            "slow",
            "crash",
            "software",
            "hardware",
            "keyboard",
            "mouse",
            "monitor",
            "headset",
            "phish",
            "malware",
            "virus",
            "security",
            "access",
            "entitlement",
            "certificate",
            "active directory",
            "ad sync",
            "sso",
            "okta",
            "azure",
            "office 365",
            "microsoft 365",
            "sharepoint",
            "onedrive",
            "ticket",
            "helpdesk",
            "it support",
            "install",
            "application",
            "app ",
            "browser",
            "chrome",
            "edge",
            "firewall",
            "proxy",
            "dns",
            "ip address",
            "remote desktop",
            "rdp",
            "citrix",
            "docking",
            "usb",
            "webcam",
            "microphone",
            "bluetooth",
        )
        if any(t in lowered for t in it_terms):
            return True
        # Category / submenu labels from catalog
        for opt in self.catalog.get("root_options", []) or []:
            if not isinstance(opt, dict):
                continue
            label = (opt.get("label") or "").strip().lower()
            if label and len(label) >= 4 and label in lowered:
                return True
        return False

    def _match_demo_faq_answer(self, lowered: str) -> str | None:
        """Lightweight canned answers for common IT helpdesk FAQs (demo)."""
        faqs = [
            (
                ("helpdesk hour", "support hour", "when is it open", "opening hours"),
                "IT helpdesk hours are Monday–Friday, 08:00–18:00 local time (Demo Mode). "
                "For after-hours emergencies, use Talk to IT to raise a priority ticket.",
            ),
            (
                ("how do i contact it", "contact it", "it phone", "support phone", "helpdesk number"),
                "You can reach IT via this Get Help chat, or raise a ticket from Talk to IT. "
                "The demo helpdesk line is +1-555-0100 (Demo Mode).",
            ),
            (
                ("reset my password", "how do i reset", "password reset"),
                "For a self-service password reset: go to the company sign-in page → "
                "Forgot password → complete the verification challenge. "
                "If that fails, pick Account → Forgot password in the catalog, or ask me to raise a ticket.",
            ),
            (
                ("vpn server", "vpn address", "vpn gateway", "connect to vpn"),
                "Demo VPN gateway: vpn.demo.cloudiqs.local. Use your corporate credentials and "
                "ensure MFA is enrolled. If the certificate is expired, choose VPN → Certificate issues "
                "from the catalog for a guided fix.",
            ),
            (
                ("wifi password", "wi-fi password", "wireless password", "guest wifi"),
                "Corporate Wi‑Fi uses 802.1X with your work account (no shared password). "
                "Guest Wi‑Fi: guest-demo / Welcome2Demo! (Demo Mode). "
                "If you cannot join, pick Network → Wi‑Fi from the catalog.",
            ),
            (
                ("mfa setup", "set up mfa", "enroll mfa", "register authenticator"),
                "To enroll MFA: open My Account → Security → Add authenticator, scan the QR code, "
                "then confirm with a test code. Lost device? Choose Account → Lost MFA device.",
            ),
        ]
        for keys, answer in faqs:
            if any(k in lowered for k in keys):
                return answer
        return None

    def _respond_others_guide(
        self, conversation: Conversation, detail: str, message: str
    ) -> dict:
        """Solid solution + Raise ticket / Main menu / free-text chat."""
        self._append_others_history(conversation, detail, message)
        conversation.state = "DESCRIBING_OTHER"
        conversation.current_menu_node = "GEN-UNKNOWN"
        self.db.commit()
        return {
            "conversation_id": conversation.conversation_id,
            "case_id": conversation.current_case,
            "state": "DESCRIBING_OTHER",
            "assistant_message": (
                message
                + "\n\nTry the steps above. You can reply here if you need a follow-up, "
                "raise a ticket if it isn’t resolved, or return to the main menu."
            ),
            "options": [
                {
                    "id": "others_raise_ticket",
                    "label": "Raise a ticket",
                    "type": "action",
                },
                {
                    "id": "others_main_menu",
                    "label": "Back to main menu",
                    "type": "action",
                },
            ],
            "controls": ["start_over"],
            "allow_free_text": True,
            "free_text_hint": "Reply if it helped, still broken, or ask a follow-up…",
            "free_text_submit_label": "Send",
            "demo_mode": True,
            "selection_mode": "single",
            "breadcrumb": ["Others", "IT assistant"],
        }

    def _respond_others_answer(
        self, conversation: Conversation, detail: str, payload: dict
    ) -> dict:
        """Rule-based answer when LLM is unavailable — no auto ticket."""
        kind = payload.get("kind")
        if kind == "faq":
            message = payload.get("message") or "Here is what I can share from our demo help topics."
        else:
            issue = payload.get("issue") or {}
            code = payload.get("issue_code") or issue.get("issue_code") or ""
            label = issue.get("label") or code or "this topic"
            category = issue.get("category") or "IT"
            sub = issue.get("subcategory") or ""
            action = issue.get("action_code") or "guided remediation"
            verify = issue.get("verify") or "confirm the issue is cleared"
            scope = f"{category}" + (f" / {sub}" if sub else "")
            message = (
                f"I can help with that — it looks like \"{label}\" ({code}) under {scope}.\n\n"
                f"Demo guidance: we usually check related signals, then run {action} "
                f"and verify that {verify}.\n\n"
                "No ticket was created. For a guided walkthrough, pick the matching "
                "category below. If that does not help, use Others again or Talk to IT."
            )

        # Prefer staying in Others chat so the user can follow up (same UX as LLM guide).
        return self._respond_others_guide(conversation, detail, message)

    def _close_with_other_ticket(self, conversation: Conversation, detail: str) -> dict:
        """Legacy helper: raise a ticket from free text and lock the session."""
        if not detail:
            conversation.state = "DESCRIBING_OTHER"
            self.db.commit()
            return {
                "conversation_id": conversation.conversation_id,
                "state": "DESCRIBING_OTHER",
                "assistant_message": (
                    "Please type a short description of the issue, then send."
                ),
                "options": [],
                "controls": ["back", "start_over"],
                "allow_free_text": True,
                "free_text_hint": "Describe your issue…",
                "free_text_submit_label": "Send",
                "demo_mode": True,
            }

        result = self.create_unknown_ticket(
            conversation.conversation_id,
            detail,
            summary_override="User-described issue (Others)",
            issue_code_override="GEN-UNKNOWN",
            close_session=True,
        )
        conversation.state = "CLOSED"
        self.db.commit()
        result["state"] = "CLOSED"
        result["options"] = []
        result["controls"] = ["start_over"]
        result["allow_free_text"] = False
        result["session_locked"] = True
        return result

    def _match_free_text_to_issue(self, free_text: str) -> Optional[str]:
        """Map free text to a catalogue issue code when we have a designed flow."""
        text = (free_text or "").lower()
        if not text.strip():
            return None
        keywords = [
            ("locked out", "ID-01"),
            ("account locked", "ID-01"),
            ("locked", "ID-01"),
            ("reset password", "ID-02"),
            ("forgot password", "ID-02"),
            ("password", "ID-02"),
            ("mfa", "ID-03"),
            ("multi-factor", "ID-03"),
            ("vpn certificate", "NET-01"),
            ("vpn cert", "NET-01"),
            ("vpn client", "NET-02"),
            ("cannot connect vpn", "NET-01"),
            ("can't connect vpn", "NET-01"),
            ("vpn", "NET-01"),
            ("wifi", "NET-03"),
            ("wi-fi", "NET-03"),
            ("internet", "NET-03"),
            ("disk full", "DEV-01"),
            ("disk space", "DEV-01"),
            ("storage", "DEV-01"),
            ("disk", "DEV-01"),
            ("laptop slow", "DEV-01"),
            ("computer slow", "DEV-01"),
            ("slow", "DEV-01"),
            # Avoid bare "restart" — matches "restarting hasn't fixed it" falsely as DEV-04
            ("restart loop", "DEV-04"),
            ("keeps restarting", "DEV-04"),
            ("pending restart", "DEV-04"),
            ("restart pending", "DEV-04"),
            ("forced reboot", "DEV-04"),
            ("teams", "APP-01"),
            ("outlook", "APP-02"),
            ("email", "APP-02"),
            ("crash", "APP-01"),
            ("printer", "PRINT-02"),
            ("print", "PRINT-02"),
            ("phish", "SEC-01"),
            ("suspicious email", "SEC-01"),
            ("malware", "SEC-02"),
            ("keyboard", "HW-01"),
            ("mouse", "HW-01"),
            ("monitor", "HW-02"),
            ("headset", "HW-03"),
            ("software request", "REQ-01"),
            ("access request", "REQ-02"),
        ]
        for kw, code in keywords:
            if kw in text and self.find_issue_by_code(code):
                return code
        # Soft match against catalogue labels / categories
        issues = self.catalog.get("issues") or []
        best_code = None
        best_score = 0
        for issue in issues:
            code = issue.get("issue_code")
            if not code:
                continue
            label = (issue.get("label") or "").lower()
            category = (issue.get("category") or "").lower()
            sub = (issue.get("subcategory") or "").lower()
            score = 0
            for token in (label, category, sub):
                if token and len(token) >= 4 and token in text:
                    score += len(token)
            if score > best_score:
                best_score = score
                best_code = code
        if best_score >= 6:
            return best_code
        return None

    def _offer_unknown_ticket(
        self,
        conversation: Conversation,
        detail: str,
        *,
        assistant_message: str | None = None,
    ) -> dict:
        """Ask consent before raising a ticket for unanticipated free text."""
        case_id = conversation.current_case or generate_id("CASE")
        case = self._get_case(conversation)
        if case is None:
            self.db.add(
                Case(
                    case_id=case_id,
                    conversation_id=conversation.conversation_id,
                    tenant_id=self.tenant_id,
                    issue_code="GEN-UNKNOWN",
                    state="awaiting_ticket_confirm",
                    collected_facts={"pending_ticket_detail": detail},
                )
            )
            conversation.current_case = case_id
        else:
            facts = dict(case.collected_facts or {})
            facts["pending_ticket_detail"] = detail
            case.collected_facts = facts
            case.issue_code = case.issue_code or "GEN-UNKNOWN"
            case.state = "awaiting_ticket_confirm"
        conversation.current_menu_node = "GEN-UNKNOWN"
        conversation.state = "AWAITING_UNKNOWN_TICKET_CONFIRM"
        self.db.commit()
        default_msg = (
            f"I can't effectively solve this here yet.\n\n"
            f"Issue: {detail}\n\n"
            "Raise a ticket with this issue, or go back to the main menu."
        )
        return {
            "conversation_id": conversation.conversation_id,
            "case_id": case_id,
            "state": "AWAITING_UNKNOWN_TICKET_CONFIRM",
            "assistant_message": assistant_message or default_msg,
            "options": [
                {
                    "id": "confirm_raise_ticket",
                    "label": "Raise a ticket",
                    "type": "action",
                },
                {
                    "id": "others_main_menu",
                    "label": "Back to main menu",
                    "type": "action",
                },
            ],
            "controls": ["start_over"],
            "demo_mode": True,
            "selection_mode": "single",
            "require_confirm": True,
            "confirm_label": "Confirm",
            "breadcrumb": ["Others", "Raise a ticket?"],
        }

    def _confirm_unknown_ticket(self, conversation: Conversation) -> dict:
        case = self._get_case(conversation)
        detail = ""
        if case is not None:
            facts = dict(case.collected_facts or {})
            detail = (facts.get("pending_ticket_detail") or facts.get("ticket_detail") or "").strip()
        if not detail:
            return self._prompt_ticket_complaint(
                conversation,
                intent="support",
                message=(
                    "Please enter a short description of your complaint in the box below, "
                    "then raise a ticket."
                ),
            )
        result = self.create_unknown_ticket(
            conversation.conversation_id,
            detail,
            summary_override="Issue not in catalog",
            issue_code_override="GEN-UNKNOWN",
        )
        if case is not None:
            case.state = "ticket_opened"
            self.db.commit()
        conversation.state = "CASE_SUMMARY"
        self.db.commit()
        return result

    def _get_case(self, conversation: Conversation) -> Case | None:
        if not conversation.current_case:
            return None
        return self.db.execute(
            select(Case).where(Case.case_id == conversation.current_case)
        ).scalar_one_or_none()

    def _build_ticket_description(
        self, conversation: Conversation, detail: str | None = None
    ) -> str:
        issue_code = conversation.current_menu_node or "GEN-UNKNOWN"
        issue = self.find_issue_by_code(issue_code) or {}
        case = self._get_case(conversation)
        facts = dict((case.collected_facts if case else None) or {})
        selection = facts.get("clarifying_choice_label") or facts.get("clarifying_choice_id")
        detail_text = (detail or "").strip() or (facts.get("ticket_detail") or "").strip()

        lines = [
            f"Catalogue issue: {issue_code} ({issue.get('label') or issue_code})",
            f"Category: {issue.get('category') or 'n/a'} / {issue.get('subcategory') or 'n/a'}",
        ]
        if selection:
            lines.append(f"User selection: {selection}")
        if detail_text and detail_text != selection:
            lines.append(f"Issue detail: {detail_text}")
        if not selection and not detail_text:
            lines.append(
                f"Issue detail: User requested ticket for {issue.get('label') or issue_code}"
            )
        diag = (case.diagnosis if case else None) or {}
        hyp = (diag.get("finding") or {}).get("hypothesis")
        if hyp:
            lines.append(f"Diagnosis: {hyp}")
        lines.append("Reason: specialised automated tool unavailable (last-resort ticket)")
        return "\n".join(lines)

    def _open_support_ticket(
        self, conversation: Conversation, detail: str | None = None
    ) -> dict:
        """Open a ticket using clarifier text + optional typed detail (no-tool fallback)."""
        issue_code = conversation.current_menu_node or ""
        case = self._get_case(conversation)
        if case is not None and detail:
            facts = dict(case.collected_facts or {})
            facts["ticket_detail"] = detail
            case.collected_facts = facts
            self.db.commit()

        # Always collect a user-typed complaint before raising
        facts = dict((case.collected_facts if case else None) or {})
        complaint = (detail or "").strip() or (facts.get("ticket_detail") or "").strip()
        if not complaint:
            return self._prompt_ticket_complaint(
                conversation,
                intent="support",
                message=(
                    "Please enter a short description of your complaint in the box below, "
                    "then raise a ticket."
                ),
            )

        description = self._build_ticket_description(conversation, detail=complaint)
        issue = self.find_issue_by_code(issue_code) or {}
        if issue_code == "NET-04":
            summary = "VPN/service outage-linked ticket"
        elif issue.get("label"):
            summary = f"{issue.get('label')}: ticket request"
        else:
            summary = f"Support ticket for {issue_code or 'unknown issue'}"

        result = self.create_unknown_ticket(
            conversation.conversation_id,
            description,
            summary_override=summary,
            issue_code_override=issue_code or None,
        )
        if case is not None:
            case.state = "ticket_opened"
            self.db.commit()
        conversation.state = "CASE_SUMMARY"
        self.db.commit()
        return result

    def create_escalation_ticket(
        self, conversation_id: str, detail: str | None = None
    ) -> dict:
        complaint = (detail or "").strip()
        if not complaint:
            conversation = self.get_conversation(conversation_id)
            if conversation:
                return self._prompt_ticket_complaint(
                    conversation,
                    intent="escalate",
                    message=(
                        "I'll connect you with IT. Enter a short description of your "
                        "complaint below, then raise a ticket."
                    ),
                )
        description = (
            f"User chose Talk to IT / human escalation.\nUser complaint: {complaint}"
            if complaint
            else "User chose Talk to IT / human escalation"
        )
        ticket_id = generate_id("INC")
        now = datetime.now(timezone.utc)
        talk_team = route_team(category="requests", summary="talk to IT")
        owner_id, owner_name = route_owner(self.db, self.tenant_id, talk_team)
        self.db.add(
            Ticket(
                ticket_id=ticket_id,
                tenant_id=self.tenant_id,
                requester=self.user_id,
                summary="User requested to talk to IT",
                description=description,
                status="in_progress",
                priority="medium",
                assigned_team=talk_team,
                assigned_to=owner_id,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        self.db.commit()
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.state = "CASE_SUMMARY"
            self.db.commit()
        return {
            "conversation_id": conversation_id,
            "state": "CASE_SUMMARY",
            "assistant_message": (
                f"I've created ticket {ticket_id} for {talk_team} and assigned it to "
                f"{owner_name}. I haven't changed your settings. That task is done on my side."
            ),
            "ticket": {
                "ticket_id": ticket_id,
                "status": "in_progress",
                "assigned_team": talk_team,
                "assigned_to": owner_id,
                "assignee_name": owner_name,
                "created_at": now.isoformat(),
            },
            "options": self._anything_else_options(),
            "controls": ["start_over"],
            "allow_free_text": False,
            "demo_mode": True,
        }

    def create_unknown_ticket(
        self,
        conversation_id: str,
        description: str,
        *,
        summary_override: str | None = None,
        issue_code_override: str | None = None,
        close_session: bool = False,
    ) -> dict:
        conversation = self.get_conversation(conversation_id)
        node = (conversation.current_menu_node if conversation else None) or ""
        issue_code = (
            issue_code_override
            or (node if node and "-" in node and len(node) <= 12 else "GEN-UNKNOWN")
        )
        if "Outage-linked" in description or node == "NET-04" or issue_code == "NET-04":
            issue_code = "NET-04"
            summary = summary_override or "VPN/service outage-linked ticket"
            team = route_team(issue_code="NET-04", category="network")
            priority = "high"
        elif issue_code.startswith("SEC"):
            summary = summary_override or "Security escalation"
            team = route_team(issue_code=issue_code, category="security")
            priority = "high"
        elif issue_code == "GEN-UNKNOWN":
            summary = summary_override or "Issue not in catalog"
            team = route_team(issue_code=issue_code, category="requests")
            priority = "medium"
        else:
            summary = summary_override or f"Escalation for {issue_code}"
            team = route_team(issue_code=issue_code, summary=summary)
            priority = "medium"

        owner_id, owner_name = route_owner(self.db, self.tenant_id, team)
        ticket_id = generate_id("INC")
        existing = self.db.execute(
            select(Ticket).where(
                Ticket.tenant_id == self.tenant_id,
                Ticket.requester == self.user_id,
                Ticket.summary == summary,
                Ticket.description == description,
            )
        ).scalar_one_or_none()
        ticket_row: Ticket | None = existing
        if existing:
            ticket_id = existing.ticket_id
        else:
            now = datetime.now(timezone.utc)
            ticket_row = Ticket(
                ticket_id=ticket_id,
                tenant_id=self.tenant_id,
                requester=self.user_id,
                issue_code=issue_code,
                summary=summary,
                description=description,
                status="in_progress",
                priority=priority,
                assigned_team=team,
                assigned_to=owner_id,
                version=1,
                created_at=now,
                updated_at=now,
            )
            self.db.add(ticket_row)
            self.db.commit()
            self.db.refresh(ticket_row)

        created_at = (
            ticket_row.created_at.isoformat()
            if ticket_row is not None and ticket_row.created_at is not None
            else None
        )

        if close_session:
            assistant_message = (
                f"Thanks. I've raised ticket **{ticket_id}** with your description "
                f"and assigned it to {owner_name} ({team}). We're looking into it and will get back to you. "
                "You don't need to do anything else in this chat for now. "
                "Use **Start over** if you have a new request."
            )
            options: list = []
            state = "CLOSED"
            controls = ["start_over"]
        else:
            assistant_message = (
                f"Ticket **{ticket_id}** is open for IT ({issue_code}). "
                "Your details are on the ticket."
            )
            options = self._anything_else_options()
            state = "CASE_SUMMARY"
            controls = ["start_over"]

        return {
            "conversation_id": conversation_id,
            "state": state,
            "assistant_message": assistant_message,
            "ticket": {
                "ticket_id": ticket_id,
                "status": "in_progress",
                "issue_code": issue_code,
                "summary": summary,
                "description": description,
                "assigned_team": team,
                "assigned_to": owner_id,
                "assignee_name": owner_name,
                "created_at": created_at,
                "source": "bakery",
            },
            "options": options,
            "controls": controls,
            "allow_free_text": False,
            "session_locked": close_session,
            "demo_mode": True,
        }
