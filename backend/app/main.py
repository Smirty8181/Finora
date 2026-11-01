import json
import random
from contextlib import asynccontextmanager
from collections import defaultdict

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import ChatMessage, ChatSession, Ticket, UnansweredQuestion
from app.schemas import (
    ChatRequest,
    ChatResponse,
    HandoffRequest,
    LoginRequest,
    LoginResponse,
    MessageRequest,
    TicketStatusUpdate,
)
from app.security import authenticate_token, create_access_token
from app.services.assistant import FAQSearch
from app.services.runtime import (
    ChatRateLimiter,
    WARNING,
    create_or_get_ticket,
    get_or_create_session,
    redact_card_numbers,
    save_message,
)

faq_search = FAQSearch(settings.faq_path)
rate_limiter = ChatRateLimiter(settings.chat_rate_limit, settings.chat_rate_window_seconds)

class TicketConnections:
    def __init__(self):
        self.connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, ticket_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[ticket_id].add(websocket)

    def disconnect(self, ticket_id: int, websocket: WebSocket):
        self.connections[ticket_id].discard(websocket)
        if not self.connections[ticket_id]:
            self.connections.pop(ticket_id, None)

    async def publish(self, ticket_id: int, payload: dict, exclude: WebSocket | None = None):
        stale = []
        for connection in tuple(self.connections.get(ticket_id, ())):
            if connection is exclude:
                continue
            try:
                await connection.send_json(payload)
            except (OSError, RuntimeError, WebSocketDisconnect):
                stale.append(connection)
        for connection in stale:
            self.disconnect(ticket_id, connection)


ticket_connections = TicketConnections()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Finora API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    rate_key = request.client.host if request.client else "unknown"
    if not rate_limiter.allow(rate_key):
        raise HTTPException(status_code=429, detail="Too many chat requests")

    session = get_or_create_session(db, payload.session_id)
    safe_message, had_card = redact_card_numbers(payload.message)
    ticket = db.scalar(
        select(Ticket).where(Ticket.session_id == session.id, Ticket.status != "closed")
        .order_by(Ticket.created_at.desc())
    )
    user_message = save_message(
        db, session.id, "user", safe_message, ticket.id if ticket is not None else None
    )

    if ticket is not None:
        db.commit()
        message_payload = _message_dict(user_message)
        if had_card:
            message_payload["warning"] = "Номер карты скрыт и не сохраняется."
        await ticket_connections.publish(ticket.id, message_payload)
        return ChatResponse(
            answer="Ваше сообщение передано сотруднику. Мы ответим в этом диалоге.",
            confidence=1.0,
            matched_intent="human_support",
            ticket_id=ticket.id,
            mode="human",
            warning=" ".join([WARNING] if had_card else []) or None,
            session_id=session.id,
        )

    topic = faq_search.topic(safe_message)
    if topic is not None:
        answer = (
            f"Привет! Ты хочешь узнать что-нибудь о {topic['name']}? Вот чем могу помочь:"
            if topic["has_greeting"]
            else f"Вот что могу подсказать о {topic['name']}. Выберите, что вас интересует:"
        )
        confidence = 1.0
        intent = topic["intent"]
        suggestions = topic["suggestions"]
    else:
        history = db.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session.id,
                ChatMessage.id < user_message.id,
            )
            .order_by(ChatMessage.id.desc())
            .limit(4)
        ).all()
        matched, confidence, candidates = faq_search.search(safe_message)
        if matched is None and len(safe_message.split()) <= 4:
            search_message = safe_message
            context_intent = None
            for previous in history:
                if previous.sender != "user":
                    continue
                previous_topic = faq_search.topic(previous.message)
                if previous_topic:
                    search_message = f"{previous_topic['name']} {safe_message}"
                    context_intent = previous_topic["intent"]
                break
            if context_intent:
                matched, confidence, candidates = faq_search.search(
                    search_message,
                    context_intent=context_intent,
                )
        if matched is not None:
            answer = random.choice(matched.get("answer_variants", [matched["answer"]]))
            intent = matched["intent"]
            same_topic = [
                faq_search.canonical_question(record)
                for record in faq_search.records
                if record["intent"] == intent and record is not matched
            ][:3]
            if intent in {
                "greetings",
                "how_are_you",
                "identity",
                "gratitude",
                "goodbye",
                "compliment",
                "frustration",
                "apology",
                "repeat_answer",
                "clarification",
                "help",
                "emotions",
            }:
                suggestions = None
            elif intent == "assistant_capabilities":
                suggestions = [
                    "Кешбэк",
                    "Как заказать карту?",
                    "Как открыть вклад?",
                    "Как перевести деньги другому человеку?",
                ]
            else:
                suggestions = same_topic or [
                    faq_search.canonical_question(record)
                    for record in candidates
                    if record["intent"] != intent
                ][:3] or None
            if intent == "repeat_answer":
                previous_answer = next(
                    (message.message for message in history if message.sender == "bot"),
                    None,
                )
                if previous_answer:
                    answer = f"Конечно, повторяю:\n{previous_answer}"
        else:
            answer = (
                "Пока не поняла, что именно вы хотите узнать. Уточните вопрос или выберите тему ниже. "
                "Если удобнее, подключу сотрудника."
            )
            intent = None
            suggestions = [
                "Какие карты доступны в Finora?",
                "Как перевести деньги другому клиенту?",
                "Есть ли в Finora программа кешбэка?",
                "Как связаться со службой поддержки?",
            ]
            db.add(UnansweredQuestion(session_id=session.id, question=safe_message))

    save_message(db, session.id, "bot", answer)
    db.commit()
    return ChatResponse(
        answer=answer,
        confidence=round(confidence, 4),
        matched_intent=intent,
        suggestions=suggestions,
        mode="bot",
        warning=WARNING if had_card else None,
        session_id=session.id,
    )


@app.post("/api/chat/handoff")
def handoff(payload: HandoffRequest, db: Session = Depends(get_db)):
    session = get_or_create_session(db, payload.session_id)
    ticket = create_or_get_ticket(db, session.id)
    db.commit()
    return {"ticket_id": ticket.id, "session_id": session.id, "status": ticket.status}


@app.post("/api/staff/login", response_model=LoginResponse)
def staff_login(payload: LoginRequest):
    if not (
        secrets_compare(payload.username, settings.staff_username)
        and secrets_compare(payload.password, settings.staff_password)
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(access_token=create_access_token(payload.username))


def secrets_compare(provided: str, configured: str) -> bool:
    import hmac

    return hmac.compare_digest(provided.encode(), configured.encode())


@app.get("/api/tickets")
def list_tickets(_: str = Depends(authenticate_token), db: Session = Depends(get_db)):
    tickets = db.scalars(select(Ticket).order_by(Ticket.updated_at.desc())).all()
    return {
        "tickets": [
            {
                "id": ticket.id,
                "session_id": ticket.session_id,
                "status": ticket.status,
                "nova_answer_wrong": ticket.nova_answer_wrong,
                "last_message": (
                    db.scalar(
                        select(ChatMessage.message)
                        .where(ChatMessage.ticket_id == ticket.id)
                        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                        .limit(1)
                    )
                ),
                "created_at": ticket.created_at,
                "updated_at": ticket.updated_at,
            }
            for ticket in tickets
        ]
    }


@app.get("/api/tickets/{ticket_id}/messages")
def list_ticket_messages(ticket_id: int, _: str = Depends(authenticate_token), db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    messages = db.scalars(
        select(ChatMessage).where(ChatMessage.ticket_id == ticket_id).order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()
    return {"messages": [_message_dict(message) for message in messages]}


@app.patch("/api/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    payload: TicketStatusUpdate,
    _: str = Depends(authenticate_token),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if payload.status is not None:
        ticket.status = payload.status
    if payload.nova_answer_wrong is not None:
        ticket.nova_answer_wrong = payload.nova_answer_wrong
    db.commit()
    response = {
        "id": ticket.id,
        "session_id": ticket.session_id,
        "status": ticket.status,
        "nova_answer_wrong": ticket.nova_answer_wrong,
    }
    await ticket_connections.publish(
        ticket.id,
        {
            "type": "ticket_update",
            "ticket_id": ticket.id,
            "session_id": ticket.session_id,
            "status": ticket.status,
            "nova_answer_wrong": ticket.nova_answer_wrong,
        },
    )
    return response


@app.post("/api/tickets/{ticket_id}/messages")
async def staff_message(
    ticket_id: int,
    payload: MessageRequest,
    _: str = Depends(authenticate_token),
    db: Session = Depends(get_db),
):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.status == "closed":
        raise HTTPException(status_code=409, detail="Ticket is closed")
    safe_message, had_card = redact_card_numbers(payload.message)
    message = save_message(db, ticket.session_id, "staff", safe_message, ticket.id)
    db.commit()
    response = _message_dict(message)
    if had_card:
        response["warning"] = "Номер карты скрыт и не сохраняется."
    await ticket_connections.publish(ticket.id, response)
    return response


@app.get("/api/unanswered-questions")
def unanswered_questions(_: str = Depends(authenticate_token), db: Session = Depends(get_db)):
    rows = db.scalars(select(UnansweredQuestion).order_by(UnansweredQuestion.created_at.desc())).all()
    return {
        "questions": [
            {"id": row.id, "session_id": row.session_id, "question": row.question, "created_at": row.created_at}
            for row in rows
        ]
    }


def _message_dict(message: ChatMessage):
    return {
        "id": message.id,
        "sender": message.sender,
        "text": message.message,
        "content": message.message,
        "message": message.message,
        "created_at": message.created_at.isoformat(),
    }


@app.websocket("/ws/tickets/{ticket_id}")
async def ticket_websocket(websocket: WebSocket, ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        await websocket.close(code=4404)
        return
    session_id = websocket.query_params.get("session_id")
    token = websocket.query_params.get("token")
    is_staff = False
    if token:
        try:
            data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            is_staff = isinstance(data, dict) and data.get("sub") == settings.staff_username
        except jwt.PyJWTError:
            is_staff = False
    if not is_staff and session_id != ticket.session_id:
        await websocket.close(code=4401)
        return

    if not is_staff and ticket.status == "closed":
        await websocket.accept()
        await websocket.send_json({"type": "ticket_closed", "ticket_id": ticket.id})
        await websocket.close(code=4409)
        return

    await ticket_connections.connect(ticket.id, websocket)
    try:
        if is_staff:
            await ticket_connections.publish(
                ticket.id,
                {
                    "type": "ticket_assigned",
                    "ticket_id": ticket.id,
                    "session_id": ticket.session_id,
                    "staff_username": settings.staff_username,
                },
                exclude=websocket,
            )
            await websocket.send_json(
                {
                    "type": "ticket_update",
                    "ticket_id": ticket.id,
                    "session_id": ticket.session_id,
                    "status": ticket.status,
                    "nova_answer_wrong": ticket.nova_answer_wrong,
                }
            )
        while True:
            incoming = await websocket.receive_text()
            db.refresh(ticket)
            if ticket.status == "closed":
                await websocket.send_json({"type": "ticket_closed", "ticket_id": ticket.id})
                await websocket.close(code=4409)
                break
            try:
                data = json.loads(incoming)
                text = data["message"] if isinstance(data, dict) else incoming
            except (json.JSONDecodeError, KeyError, TypeError):
                text = incoming
            if not isinstance(text, str) or not text.strip() or len(text) > 500:
                await websocket.send_json({"error": "Message must contain 1 to 500 characters"})
                continue
            safe_message, had_card = redact_card_numbers(text)
            message = save_message(db, ticket.session_id, "staff" if is_staff else "user", safe_message, ticket.id)
            db.commit()
            response = _message_dict(message)
            if had_card:
                response["warning"] = "Номер карты скрыт и не сохраняется."
            await ticket_connections.publish(ticket.id, response, exclude=websocket)
            await websocket.send_json(response)
    except WebSocketDisconnect:
        ticket_connections.disconnect(ticket.id, websocket)
