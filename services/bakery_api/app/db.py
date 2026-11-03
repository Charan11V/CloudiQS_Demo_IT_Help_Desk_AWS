from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from .config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    _ensure_conversation_ui_snapshot_column()
    _ensure_ticket_assigned_to_column()


def _ensure_conversation_ui_snapshot_column() -> None:
    """Add conversations.ui_snapshot on existing DBs without a full reset."""
    from sqlalchemy import text

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'conversations' AND column_name = 'ui_snapshot'
                """
            )
        ).first()
        if row:
            return
        conn.execute(
            text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ui_snapshot JSON")
        )


def _ensure_ticket_assigned_to_column() -> None:
    """Add tickets.assigned_to on databases created before owner routing."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "tickets" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("tickets")}
    if "assigned_to" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE tickets ADD COLUMN assigned_to VARCHAR(50)"))


def drop_tables():
    """Drop all tables in the database"""
    Base.metadata.drop_all(bind=engine)
