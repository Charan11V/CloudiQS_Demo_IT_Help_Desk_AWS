"""Database connection and session management."""
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import APP_DB_PATH

# Create database directory if needed
APP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# SQLite engine with WAL mode
engine = create_engine(
    f"sqlite:///{APP_DB_PATH}",
    connect_args={"check_same_thread": False, "timeout": 20},
    pool_pre_ping=True
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and foreign keys."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=20000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@contextmanager
def get_db():
    """Database session context manager."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from app import models  # Import here to avoid circular dependency
    Base.metadata.create_all(bind=engine)
