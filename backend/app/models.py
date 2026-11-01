from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True, index=True)
    sender: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    session: Mapped[ChatSession] = relationship(back_populates="messages")
    ticket: Mapped["Ticket | None"] = relationship(back_populates="messages")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    nova_answer_wrong: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    session: Mapped[ChatSession] = relationship(back_populates="tickets")
    messages: Mapped[list[ChatMessage]] = relationship(back_populates="ticket")


class UnansweredQuestion(Base):
    __tablename__ = "unanswered_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
