"""
SQLite storage layer for the Meeting Summarizer.

Keeps things intentionally simple: one table, one file, no migrations
framework. Good enough for a demo / small-team deployment. Swap out for
Postgres later by changing DATABASE_URL if this needs to scale.
"""
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./meetings.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="processing")  # processing | done | failed
    error = Column(Text, nullable=True)

    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    decisions = Column(Text, nullable=True)     # JSON-encoded list[str]
    action_items = Column(Text, nullable=True)  # JSON-encoded list[dict]

    duration_seconds = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
