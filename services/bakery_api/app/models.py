from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, Float, ForeignKey, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base


class Tenant(Base):
    __tablename__ = "tenants"
    
    tenant_id = Column(String(50), primary_key=True)
    display_name = Column(String(200), nullable=False)
    domain = Column(String(200), nullable=False)
    config = Column(JSON, default=dict)
    demo_mode = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    email = Column(String(200), nullable=False)
    display_name = Column(String(200), nullable=False)
    role = Column(String(50), nullable=False)  # employee, it_engineer, it_manager, tenant_admin
    department = Column(String(200))
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    tenant = relationship("Tenant", back_populates="users")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user'),
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_email'),
        Index('idx_user_tenant_id', 'tenant_id'),
    )


class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String(50), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    status = Column(String(50), default="active")  # active, locked, disabled
    lock_reason = Column(String(200))
    failed_logins = Column(Integer, default=0)
    mfa_enabled = Column(Boolean, default=True)
    password_expired = Column(Boolean, default=False)
    credentials_version = Column(Integer, default=1)
    risk_flag = Column(Boolean, default=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_account_tenant_user', 'tenant_id', 'user_id'),
    )


class Session(Base):
    __tablename__ = "sessions"
    
    session_id = Column(String(100), primary_key=True)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    status = Column(String(50), default="active")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    assigned_to = Column(String(50), nullable=False)  # user_id
    device_name = Column(String(200), nullable=False)
    platform = Column(String(50))
    asset_tag = Column(String(100))
    
    # Disk metrics
    disk_total_gb = Column(Integer, default=256)
    disk_free_gb = Column(Integer, default=50)
    disk_free_pct = Column(Float, default=20.0)
    
    # Performance metrics
    cpu_percent = Column(Float, default=30.0)
    memory_percent = Column(Float, default=50.0)
    temperature_celsius = Column(Float)
    battery_health = Column(String(50), default="good")
    
    # State flags
    restart_pending = Column(Boolean, default=False)
    wifi_enabled = Column(Boolean, default=True)
    dns_status = Column(String(50), default="healthy")
    
    # Health
    health = Column(String(50), default="healthy")
    reboot_count = Column(Integer, default=0)
    last_heartbeat = Column(DateTime(timezone=True))
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_device_tenant_assigned', 'tenant_id', 'assigned_to'),
    )


class TemporaryFile(Base):
    __tablename__ = "temporary_files"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    object_id = Column(String(50), unique=True, nullable=True)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    path_label = Column(String(500))
    size_bytes = Column(BigInteger, nullable=False)
    size_gb = Column(Float)
    category = Column(String(100))  # temp_cache, build_artifacts, etc.
    removed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VpnProfile(Base):
    __tablename__ = "vpn_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vpn_id = Column(String(50), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    client_version = Column(String(20))
    min_client_version = Column(String(20))
    cert_expires_at = Column(DateTime(timezone=True))
    last_failure = Column(String(100))
    connection_status = Column(String(50), default="disconnected")
    status = Column(String(50), default="active")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    service_name = Column(String(200), nullable=False)
    status = Column(String(50), default="healthy")  # healthy, degraded, outage
    active_incident_id = Column(String(100))
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Application(Base):
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    app_name = Column(String(200), nullable=False)
    approved_version = Column(String(50))
    allowed_to_self_install = Column(Boolean, default=False)
    requires_licence = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AppInstallation(Base):
    __tablename__ = "app_installations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    installation_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    device_id = Column(String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    app_id = Column(String(100), ForeignKey("applications.app_id", ondelete="CASCADE"), nullable=False)
    installed_version = Column(String(50))
    health = Column(String(50), default="healthy")  # healthy, crashing, stopped
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'device_id', 'app_id', name='uq_tenant_device_app'),
    )


class Entitlement(Base):
    __tablename__ = "entitlements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entitlement_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    resource = Column(String(200), nullable=False)  # e.g., "jira", "confluence"
    scope = Column(String(200), nullable=False)  # e.g., "read", "admin"
    status = Column(String(50), default="active")
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_id', 'resource', 'scope', name='uq_tenant_user_resource_scope'),
    )


class Mailbox(Base):
    __tablename__ = "mailboxes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mailbox_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    used_gb = Column(Float, default=0.0)
    quota_gb = Column(Float, default=50.0)
    archived_items = Column(Integer, default=0)
    sync_status = Column(String(50), default="healthy")
    last_sync_at = Column(DateTime(timezone=True))
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Printer(Base):
    __tablename__ = "printers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    printer_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    printer_name = Column(String(200), nullable=False)
    status = Column(String(50), default="online")  # online, offline
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PrintJob(Base):
    __tablename__ = "print_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    printer_id = Column(String(100), ForeignKey("printers.printer_id", ondelete="CASCADE"), nullable=False)
    document_name = Column(String(500))
    status = Column(String(50), default="pending")  # pending, printing, completed, failed, stuck, cancelled
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50))
    severity = Column(String(50))  # low, medium, high, critical
    event_type = Column(String(100))
    description = Column(Text)
    review_status = Column(String(50), default="pending")
    observed_at = Column(DateTime(timezone=True), server_default=func.now())


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    requester = Column(String(50), nullable=False)  # user_id
    issue_code = Column(String(50))
    summary = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed
    priority = Column(String(50), default="medium")  # low, medium, high, critical
    assigned_team = Column(String(100))
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TicketEvent(Base):
    __tablename__ = "ticket_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False)
    ticket_id = Column(String(100), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False)
    actor = Column(String(50), nullable=False)
    prior_status = Column(String(50))
    next_status = Column(String(50))
    reason = Column(Text)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now())


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(50), nullable=False)
    current_menu_node = Column(String(200))
    current_case = Column(String(100))
    state = Column(String(50), default="WELCOME")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(100), unique=True, nullable=False)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class Case(Base):
    __tablename__ = "cases"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(String(100), unique=True, nullable=False)
    conversation_id = Column(String(100), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    issue_code = Column(String(50))
    selected_device = Column(String(50))
    state = Column(String(50), default="new")
    expected_resource_versions = Column(JSON)
    collected_facts = Column(JSON)
    diagnosis = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ActionIntent(Base):
    __tablename__ = "action_intents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    actor = Column(String(50), nullable=False)
    target = Column(String(100), nullable=False)
    action_code = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    expected_version = Column(Integer)
    idempotency_key = Column(String(200), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    state = Column(String(50), default="pending")  # pending, approved, rejected, expired, executed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'idempotency_key', name='uq_tenant_idempotency_key'),
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    approval_id = Column(String(100), unique=True, nullable=False)
    action_id = Column(String(100), ForeignKey("action_intents.action_id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String(50))
    required_role = Column(String(50), nullable=False)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    decision_at = Column(DateTime(timezone=True))
    expiry = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ActionExecution(Base):
    __tablename__ = "action_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(100), unique=True, nullable=False)
    action_id = Column(String(100), ForeignKey("action_intents.action_id", ondelete="CASCADE"), nullable=False)
    attempts = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    state = Column(String(50), default="pending")  # pending, running, success, failed
    result_data = Column(JSON)
    external_operation_id = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(100), unique=True, nullable=False)
    tenant_id = Column(String(50), ForeignKey("tenants.tenant_id", ondelete="CASCADE"), nullable=False)
    actor = Column(String(50), nullable=False)
    resource = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    before_json = Column(JSON)
    after_json = Column(JSON)
    reason = Column(Text)
    operation_id = Column(String(100))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_tenant_resource', 'tenant_id', 'resource'),
        Index('idx_audit_timestamp', 'timestamp'),
    )
