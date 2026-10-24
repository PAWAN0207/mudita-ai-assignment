import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)

from core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="running"
    )
    current_stage: Mapped[str] = mapped_column(
        String(40), nullable=False, default="intake"
    )
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    company_rules_json: Mapped[str] = mapped_column(Text, nullable=False)
    intake_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_history_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SalesActionLog(Base):
    __tablename__ = "sales_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="success"
    )
    details: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )


class SalesConversation(Base):
    """Persistent Assignment 1 customer conversation and extracted facts."""

    __tablename__ = "sales_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    messages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    conversation_history_json: Mapped[str] = mapped_column(
        Text, nullable=False, default="[]"
    )
    customer_name: Mapped[str] = mapped_column(String(250), nullable=False, default="")
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    service_interest: Mapped[str | None] = mapped_column(String(250), nullable=True)
    budget_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qualification_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    representative_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_takeover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    booking_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def init_database() -> None:
    """Create missing tables and safely migrate existing SQLite databases."""
    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "sqlite":
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())

        if "workflow_runs" in existing_tables:
            existing_columns = {
                column["name"]
                for column in inspector.get_columns("workflow_runs")
            }
            if "current_stage" not in existing_columns:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            """
                            ALTER TABLE workflow_runs
                            ADD COLUMN current_stage
                            VARCHAR(40) NOT NULL DEFAULT 'intake'
                            """
                        )
                    )


def save_sales_action(
    lead_id: str,
    action: str,
    details: str,
    status: str = "success",
) -> None:
    """Persist one sales-assistant action."""
    with SessionLocal() as session:
        session.add(
            SalesActionLog(
                lead_id=lead_id,
                action=action,
                details=details,
                status=status,
            )
        )
        session.commit()


def get_sales_action_logs(limit: int = 200) -> list[dict]:
    """Return latest persisted sales-assistant actions."""
    if limit < 1:
        return []

    with SessionLocal() as session:
        logs = (
            session.query(SalesActionLog)
            .order_by(SalesActionLog.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": item.id,
                "timestamp": item.created_at.isoformat()
                if item.created_at
                else None,
                "lead_id": item.lead_id,
                "action": item.action,
                "status": item.status,
                "details": item.details,
            }
            for item in logs
        ]


def save_sales_conversation(
    lead_id: str,
    messages: list[dict],
    conversation_history: list[dict],
    customer_name: str = "",
    customer_email: str = "",
    service_interest: str | None = None,
    budget_inr: int | None = None,
    timeline_days: int | None = None,
    qualification: dict | None = None,
    representative: dict | None = None,
    human_takeover: bool = False,
    booking_result: dict | None = None,
) -> None:
    """Insert or update a conversation by lead ID."""
    with SessionLocal() as session:
        record = (
            session.query(SalesConversation)
            .filter(SalesConversation.lead_id == lead_id)
            .one_or_none()
        )
        if record is None:
            record = SalesConversation(lead_id=lead_id)
            session.add(record)

        record.messages_json = json.dumps(
            messages, ensure_ascii=False, default=str
        )
        record.conversation_history_json = json.dumps(
            conversation_history, ensure_ascii=False, default=str
        )
        record.customer_name = customer_name or ""
        record.customer_email = customer_email or ""
        record.service_interest = service_interest
        record.budget_inr = budget_inr
        record.timeline_days = timeline_days
        record.qualification_json = (
            json.dumps(qualification, ensure_ascii=False, default=str)
            if qualification is not None
            else None
        )
        record.representative_json = (
            json.dumps(representative, ensure_ascii=False, default=str)
            if representative is not None
            else None
        )
        record.human_takeover = bool(human_takeover)
        record.booking_result_json = (
            json.dumps(booking_result, ensure_ascii=False, default=str)
            if booking_result is not None
            else None
        )
        record.updated_at = datetime.now(timezone.utc)
        session.commit()


def load_sales_conversation(lead_id: str) -> dict | None:
    """Load a saved conversation, returning None if no record exists."""
    with SessionLocal() as session:
        record = (
            session.query(SalesConversation)
            .filter(SalesConversation.lead_id == lead_id)
            .one_or_none()
        )
        if record is None:
            return None

        def decode(value, default=None):
            if value is None:
                return default
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return default

        return {
            "lead_id": record.lead_id,
            "messages": decode(record.messages_json, []),
            "conversation_history": decode(
                record.conversation_history_json, []
            ),
            "customer_name": record.customer_name,
            "customer_email": record.customer_email,
            "service_interest": record.service_interest,
            "budget_inr": record.budget_inr,
            "timeline_days": record.timeline_days,
            "qualification": decode(record.qualification_json),
            "representative": decode(record.representative_json),
            "human_takeover": record.human_takeover,
            "booking_result": decode(record.booking_result_json),
            "updated_at": record.updated_at.isoformat()
            if record.updated_at
            else None,
        }


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully.")
    print("WorkflowRun columns:", list(WorkflowRun.__table__.columns.keys()))
    print("SalesActionLog columns:", list(SalesActionLog.__table__.columns.keys()))
    print("SalesConversation columns:", list(SalesConversation.__table__.columns.keys()))
