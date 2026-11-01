import re
import secrets
import time
from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ChatMessage, ChatSession, Ticket

CARD_SEQUENCE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
WARNING = "Не отправляйте номер карты, срок действия или CVV. Номер карты скрыт и не сохраняется."


def redact_card_numbers(text: str) -> tuple[str, bool]:
    found = False

    def mask(match: re.Match) -> str:
        nonlocal found
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19:
            found = True
            return "****"
        return match.group()

    return CARD_SEQUENCE.sub(mask, text), found


def get_or_create_session(db: Session, session_id: str | None) -> ChatSession:
    candidate = session_id or secrets.token_urlsafe(18)
    session = db.get(ChatSession, candidate)
    if session is None:
        session = ChatSession(id=candidate)
        db.add(session)
        db.flush()
    return session


def save_message(db: Session, session_id: str, sender: str, message: str, ticket_id: int | None = None):
    item = ChatMessage(session_id=session_id, sender=sender, message=message, ticket_id=ticket_id)
    db.add(item)
    db.flush()
    return item


def create_or_get_ticket(db: Session, session_id: str) -> Ticket:
    ticket = db.scalar(
        select(Ticket).where(Ticket.session_id == session_id, Ticket.status != "closed")
        .order_by(Ticket.created_at.desc())
    )
    if ticket is None:
        ticket = Ticket(session_id=session_id)
        db.add(ticket)
        db.flush()
        save_message(db, session_id, "bot", "Ваш диалог передан сотруднику. Мы скоро ответим.", ticket.id)
    for message in db.scalars(
        select(ChatMessage).where(ChatMessage.session_id == session_id, ChatMessage.ticket_id.is_(None))
    ):
        message.ticket_id = ticket.id
    return ticket


class ChatRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self.requests = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        recent = self.requests[key]
        while recent and now - recent[0] >= self.window:
            recent.popleft()
        if len(recent) >= self.limit:
            return False
        recent.append(now)
        return True
