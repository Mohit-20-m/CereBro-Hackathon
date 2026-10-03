"""Database schema. Messages keep their original text; analysis, topics, gaps
and evidence get their own tables because they are what the product is about."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .connection import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20), default="group")
    source: Mapped[str] = mapped_column(String(120), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    analysis_status: Mapped[str] = mapped_column(String(20), default="idle")  # idle|queued|running|error
    analysis_stage: Mapped[str | None] = mapped_column(String(80), nullable=True)
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)  # ai|heuristic
    analyzed_seq: Mapped[int] = mapped_column(Integer, default=0)
    analysis_version: Mapped[int] = mapped_column(Integer, default=0)
    agent_trace: Mapped[list] = mapped_column(JSON, default=list)
    insights: Mapped[dict] = mapped_column(JSON, default=dict)

    members: Mapped[list["Participant"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Participant.id"
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.seq"
    )
    topics: Mapped[list["Topic"]] = relationship(cascade="all, delete-orphan", order_by="Topic.first_seq")
    gaps: Mapped[list["CommunicationGap"]] = relationship(
        cascade="all, delete-orphan", order_by="CommunicationGap.question_seq"
    )


class Participant(Base):
    __tablename__ = "conversation_members"
    __table_args__ = (UniqueConstraint("conversation_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="members")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "seq"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    sender: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    time_label: Mapped[str] = mapped_column(String(16), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    analysis: Mapped["MessageAnalysis | None"] = relationship(
        back_populates="message", cascade="all, delete-orphan", uselist=False
    )


class MessageAnalysis(Base):
    __tablename__ = "message_analysis"

    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    language_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    languages: Mapped[list] = mapped_column(JSON, default=list)
    script: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_code_mixed: Mapped[bool] = mapped_column(Boolean, default=False)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    intent: Mapped[str | None] = mapped_column(String(30), nullable=True)
    requires_response: Mapped[bool] = mapped_column(Boolean, default=False)
    topic_done: Mapped[bool] = mapped_column(Boolean, default=False)
    topic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embed_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sources: Mapped[dict] = mapped_column(JSON, default=dict)  # which agents used the LLM or a fallback
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    message: Mapped[Message] = relationship(back_populates="analysis")


class AgentCache(Base):
    """Remembers agent decisions (judge verdicts, investigations, critic reviews,
    summaries) so re-analysis after a new message only does the new work."""

    __tablename__ = "agent_cache"
    __table_args__ = (UniqueConstraint("conversation_id", "kind", "cache_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    cache_key: Mapped[str] = mapped_column(String(255))
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20))  # pending|resolved|unresolved
    first_seq: Mapped[int] = mapped_column(Integer)
    last_seq: Mapped[int] = mapped_column(Integer)
    timeline: Mapped[list] = mapped_column(JSON, default=list)


class CommunicationGap(Base):
    __tablename__ = "communication_gaps"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    topic_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic_name: Mapped[str] = mapped_column(String(120))
    gap_type: Mapped[str] = mapped_column(String(40))
    raised_by: Mapped[str] = mapped_column(String(120))
    question_seq: Mapped[int] = mapped_column(Integer)
    latest_seq: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # unresolved|resolved
    resolved_seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    stages: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    critic: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[list["GapEvidence"]] = relationship(cascade="all, delete-orphan", order_by="GapEvidence.position")


class GapEvidence(Base):
    __tablename__ = "gap_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    gap_id: Mapped[int] = mapped_column(ForeignKey("communication_gaps.id", ondelete="CASCADE"), index=True)
    message_seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
