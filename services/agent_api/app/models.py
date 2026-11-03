"""SQLAlchemy models for agent application state."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False)
    persona_key = Column(String(50), nullable=False)
    bearer_token = Column(String(100), nullable=False)  # Server-side only
    created_at = Column(DateTime, nullable=False, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False, default=utcnow)


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    conversation_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    runs = relationship("AgentRun", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    message_id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("chat_conversations.conversation_id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    conversation = relationship("ChatConversation", back_populates="messages")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    run_id = Column(String(64), primary_key=True)
    conversation_id = Column(String(64), ForeignKey("chat_conversations.conversation_id"), nullable=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    mode = Column(String(20), nullable=False)  # simulator|bedrock|ollama
    status = Column(String(30), nullable=False, default="queued")  # queued|running|completed|failed|cancelled
    prompt_version = Column(String(50), nullable=False)
    model_id = Column(String(100), nullable=True)
    input_message = Column(Text, nullable=False)
    output_json = Column(Text, nullable=True)  # AgentOutcome JSON
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    token_usage = Column(Integer, nullable=True)
    conversation = relationship("ChatConversation", back_populates="runs")
    tool_events = relationship("ToolEvent", back_populates="run", cascade="all, delete-orphan")
    evidence_refs = relationship("EvidenceRef", back_populates="run", cascade="all, delete-orphan")
    run_events = relationship("RunEvent", back_populates="run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_runs_tenant_created", "tenant_id", "started_at"),
    )


class ToolEvent(Base):
    __tablename__ = "tool_events"
    event_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("agent_runs.run_id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # started|completed|denied|failed
    input_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    run = relationship("AgentRun", back_populates="tool_events")


class EvidenceRef(Base):
    __tablename__ = "evidence_refs"
    evidence_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("agent_runs.run_id"), nullable=False, index=True)
    source = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    tenant_id = Column(String(50), nullable=False)
    observed_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    retrieved_at = Column(DateTime, nullable=False, default=utcnow)
    classification = Column(String(50), nullable=False)
    trust_level = Column(String(50), nullable=False)
    version = Column(String(20), nullable=True)
    run = relationship("AgentRun", back_populates="evidence_refs")


class ActionIntent(Base):
    __tablename__ = "action_intents"
    intent_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("agent_runs.run_id"), nullable=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    target_user_id = Column(String(50), nullable=False)
    device_id = Column(String(50), nullable=True)
    rationale = Column(Text, nullable=False)
    payload_json = Column(Text, nullable=False)
    payload_hash = Column(String(64), nullable=False)
    status = Column(String(30), nullable=False, default="proposed")  # proposed|awaiting_approval|authorised|executed|rejected|failed
    approval_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    notification_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    link = Column(String(500), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read", "created_at"),
    )


class TicketComment(Base):
    __tablename__ = "ticket_comments"
    comment_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    ticket_id = Column(String(64), nullable=False, index=True)
    author_id = Column(String(50), nullable=False)
    body = Column(Text, nullable=False)
    visibility = Column(String(20), nullable=False, default="public")  # public|internal
    created_at = Column(DateTime, nullable=False, default=utcnow)


class TicketStateEvent(Base):
    __tablename__ = "ticket_state_events"
    event_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False)
    ticket_id = Column(String(64), nullable=False, index=True)
    actor_id = Column(String(50), nullable=False)
    event_type = Column(String(50), nullable=False)  # status_changed|assigned|priority_changed|comment_added
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Escalation(Base):
    __tablename__ = "escalations"
    escalation_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    ticket_id = Column(String(64), nullable=False, index=True)
    escalated_by = Column(String(50), nullable=False)
    target_team = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    evidence_ids = Column(Text, nullable=False)  # JSON array
    status = Column(String(30), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)


class ConnectorChange(Base):
    __tablename__ = "connector_changes"
    change_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    connector_key = Column(String(100), nullable=False)
    actor_id = Column(String(50), nullable=False)
    change_type = Column(String(30), nullable=False)  # enabled|disabled|configured|tested
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    version_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    policy_json = Column(Text, nullable=False)
    policy_hash = Column(String(64), nullable=False)
    created_by = Column(String(50), nullable=False)
    effective_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class KnowledgeRevision(Base):
    __tablename__ = "knowledge_revisions"
    revision_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    document_id = Column(String(64), nullable=False)
    version = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    classification = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)  # current|superseded|archived
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    run_id = Column(String(64), primary_key=True)
    dataset_hash = Column(String(64), nullable=False)
    prompt_hash = Column(String(64), nullable=False)
    provider = Column(String(20), nullable=False)
    model_id = Column(String(100), nullable=True)
    git_commit = Column(String(40), nullable=True)
    started_at = Column(DateTime, nullable=False, default=utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_tests = Column(Integer, nullable=False, default=0)
    passed_tests = Column(Integer, nullable=False, default=0)
    failed_tests = Column(Integer, nullable=False, default=0)
    safety_failures = Column(Integer, nullable=False, default=0)
    results = relationship("EvaluationTestResult", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationTestResult(Base):
    __tablename__ = "evaluation_test_results"
    result_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), ForeignKey("evaluation_runs.run_id"), nullable=False, index=True)
    scenario_id = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    outcome = Column(String(20), nullable=False)  # pass|fail|error
    is_safety_gate = Column(Boolean, nullable=False, default=False)
    expected_invariant = Column(Text, nullable=True)
    observed_result = Column(Text, nullable=True)
    trace_id = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    evaluation = relationship("EvaluationRun", back_populates="results")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    event_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    actor_id = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(200), nullable=False)
    result = Column(String(20), nullable=False)
    detail_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_audit_events_tenant_created", "tenant_id", "created_at"),
    )


class UsageEvent(Base):
    __tablename__ = "usage_events"
    event_id = Column(String(64), primary_key=True)
    run_id = Column(String(64), nullable=True, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    provider = Column(String(20), nullable=False)
    model_id = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(String(20), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class RunEvent(Base):
    __tablename__ = "run_events"
    event_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), ForeignKey("agent_runs.run_id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # run.created|run.stage_started|tool.started|etc
    data_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    run = relationship("AgentRun", back_populates="run_events")

    __table_args__ = (
        Index("ix_run_events_run_seq", "run_id", "event_id"),
    )


class AgentCoreBridgeSession(Base):
    """Ephemeral HMAC tool-bridge sessions (shared across uvicorn workers / docker exec)."""

    __tablename__ = "agentcore_bridge_sessions"
    token = Column(String(128), primary_key=True)
    bearer_token = Column(String(100), nullable=False)
    tenant_id = Column(String(50), nullable=False)
    user_id = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)
    session_id = Column(String(64), nullable=False)
    run_id = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
