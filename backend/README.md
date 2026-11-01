# Finora backend

FastAPI service for the Finora FAQ assistant and staff ticket inbox. Python 3.12, SQLAlchemy 2, Alembic, and scikit-learn TF-IDF word/character similarity in `app/services/assistant.py`; common typos are corrected against the FAQ vocabulary, and short topic-only messages return relevant follow-up questions. No external language model is used. FAQ evaluation can run without staff credentials using `python -m app.evaluate_faq`.

## Local setup

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///./finora.db"
$env:FAQ_PATH = "..\data\faq.json"
$env:STAFF_USERNAME = "staff"
$env:STAFF_PASSWORD = Read-Host "Set a unique staff password (at least 12 characters)"
$env:JWT_SECRET = Read-Host "Set a unique JWT secret (at least 32 characters)"
alembic upgrade head
uvicorn app.main:app --reload
```

SQLite is the default. Set `DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg://user:password@localhost:5432/finora` for PostgreSQL. `STAFF_USERNAME`, `STAFF_PASSWORD`, `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, `FAQ_PATH`, and chat rate-limit settings are configurable via environment variables. `STAFF_PASSWORD` must be at least 12 characters and `JWT_SECRET` at least 32 characters; placeholder values are rejected. Set strong unique values before starting the service and do not commit them.

## API

- `POST /api/chat` — `{ "message": "...", "session_id": "optional" }`; messages are limited to 500 characters.
- `POST /api/chat/handoff` — `{ "session_id": "..." }`; creates or returns an open ticket.
- `POST /api/staff/login` — environment-configured staff credentials; returns a JWT bearer token.
- `GET /api/tickets`, `GET /api/tickets/{id}/messages`, `PATCH /api/tickets/{id}` and `POST /api/tickets/{id}/messages` — staff JWT required. Ticket statuses are `new`, `in_progress`, and `closed`; patch with `{"nova_answer_wrong": true}` to persist staff feedback on Nova's answer.
- `GET /api/unanswered-questions` — staff JWT required.
- `WS /ws/tickets/{id}?session_id=...` — client; `?token=...` — staff. Send JSON `{ "message": "..." }`.

Ticket summaries include `last_message`; history and WebSocket messages include `text`, `content`, and `message` aliases with `sender` set to `bot`, `user`, or `staff`. When a client posts to `/api/chat` after handoff, the saved message is also broadcast to ticket WebSockets. A staff WebSocket receives a `ticket_update` status/feedback snapshot on connect, and ticket status/feedback changes are broadcast as `ticket_update` events. Closing a ticket notifies the client and prevents further replies until it is reopened. Card-like 13–19 digit sequences are fully masked before transcript or unanswered-question persistence, and the response warns the user not to share card details. Chat requests are rate limited per client IP. OpenAPI documentation is available at `/docs`.

## Tests

```powershell
pytest
```

The search tests check all 181 FAQ records and all 681 distinct question phrasings against the configured 0.45 cosine threshold, plus paraphrased examples and all 100 questions in the supplied product catalog. Each record has 3–6 distinct Russian question variants; informal wording and common typos are included across the catalog. API tests cover chat validation, topic suggestions and follow-up context, handoff/transcript history, staff authentication, status changes, unanswered questions, rate limiting, card redaction, and WebSocket persistence.

### FAQ retrieval evaluation

Run the fixed 30-question Russian intent evaluation from `backend`:

```powershell
python -m app.evaluate_faq
```

The evaluator compares each retrieved intent to its expected intent; below-threshold/no-match answers count as incorrect. The fixed cases use canonical question wording from the FAQ and cover sixteen intent groups, including greetings, casual conversation, assistant capabilities, and login troubleshooting. With the bundled FAQ and cosine threshold `0.45`, the measured result is **30/30 correct (100.0% intent accuracy)**. The cases are maintained in `app/evaluate_faq.py`, and `pytest` asserts all 30 expected intents. The broader catalog test separately checks every provided question; neither score guarantees correct answers to arbitrary wording.
