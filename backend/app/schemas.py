from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str | None = Field(default=None, max_length=64)


class HandoffRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChatResponse(BaseModel):
    answer: str
    confidence: float
    matched_intent: str | None
    suggestions: list[str] | None = None
    ticket_id: int | None = None
    mode: Literal["bot", "human"]
    warning: str | None = None
    session_id: str


class TicketStatusUpdate(BaseModel):
    status: Literal["new", "in_progress", "closed"] | None = None
    nova_answer_wrong: bool | None = None

    @model_validator(mode="after")
    def require_update(self):
        if self.status is None and self.nova_answer_wrong is None:
            raise ValueError("At least one ticket field must be provided")
        return self


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class MessageResponse(BaseModel):
    id: int
    sender: str
    message: str
    created_at: datetime


class TicketResponse(BaseModel):
    id: int
    session_id: str
    status: str
    created_at: datetime
    updated_at: datetime


class TicketsResponse(BaseModel):
    tickets: list[TicketResponse]


class MessagesResponse(BaseModel):
    messages: list[MessageResponse]
