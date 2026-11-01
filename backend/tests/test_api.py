import json
from pathlib import Path

import pytest


def test_chat_preserves_session_and_returns_faq_answer(client):
    first = client.post("/api/chat", json={"message": "Как заблокировать карту?"})
    assert first.status_code == 200
    body = first.json()
    assert body["matched_intent"] == "cards"
    assert body["mode"] == "bot"
    assert body["session_id"]

    followup = client.post(
        "/api/chat",
        json={"message": "Спасибо", "session_id": body["session_id"]},
    )
    assert followup.status_code == 200
    assert followup.json()["session_id"] == body["session_id"]


def test_chat_answers_greetings_and_login_troubleshooting(client):
    from app.main import faq_search

    greeting = client.post("/api/chat", json={"message": "Привет"})
    assert greeting.status_code == 200
    assert greeting.json()["matched_intent"] == "greetings"
    assert greeting.json()["answer"] in next(
        record["answer_variants"]
        for record in faq_search.records
        if record["intent"] == "greetings"
    )

    how_are_you = client.post("/api/chat", json={"message": "Как дела?"})
    assert how_are_you.status_code == 200
    assert how_are_you.json()["matched_intent"] == "how_are_you"

    login = client.post(
        "/api/chat",
        json={"message": "Войти в личный кабинет не получается"},
    )
    assert login.status_code == 200
    assert login.json()["matched_intent"] == "login_access"
    assert "пароль" in login.json()["answer"]


def test_chat_explains_capabilities_and_varies_greetings(client, monkeypatch):
    import app.main as chat_module

    conversation = [
        "Привет",
        "Что ты умеешь?",
        "Как делишки?",
    ]
    responses = [
        client.post("/api/chat", json={"message": message}).json()
        for message in conversation
    ]
    assert [response["matched_intent"] for response in responses] == [
        "greetings",
        "assistant_capabilities",
        "how_are_you",
    ]
    assert "перевод" in responses[1]["answer"].lower()

    monkeypatch.setattr(chat_module.random, "choice", lambda answers: answers[0])
    first = client.post("/api/chat", json={"message": "Привет"}).json()["answer"]
    monkeypatch.setattr(chat_module.random, "choice", lambda answers: answers[-1])
    second = client.post("/api/chat", json={"message": "Привет"}).json()["answer"]
    assert first != second


def test_chat_suggests_topics_and_uses_the_previous_topic(client):
    from app.main import faq_search

    session_id = "topic-follow-up"
    topic = client.post(
        "/api/chat",
        json={"message": "Приветик, расскажи про кешбек", "session_id": session_id},
    ).json()
    assert topic["matched_intent"] == "cashback"
    assert "Привет!" in topic["answer"]
    assert len(topic["suggestions"]) == 6

    follow_up = client.post(
        "/api/chat",
        json={"message": "А когда начисляется?", "session_id": session_id},
    ).json()
    assert follow_up["matched_intent"] == "cashback"
    cashback_answers = {
        record["answer"]
        for record in faq_search.records
        if record["intent"] == "cashback"
    }
    assert follow_up["answer"] in cashback_answers


def test_chat_social_questions_do_not_inherit_the_previous_bank_topic(client):
    session_id = "social-after-cashback"
    client.post("/api/chat", json={"message": "Кешбэк", "session_id": session_id})

    response = client.post(
        "/api/chat", json={"message": "Как дела?", "session_id": session_id}
    ).json()

    assert response["matched_intent"] == "how_are_you"
    assert "кешбэк" not in response["answer"].lower()


def test_chat_does_not_reuse_a_topic_across_an_unrelated_turn(client):
    session_id = "topic-context-expires"
    client.post("/api/chat", json={"message": "Кешбэк", "session_id": session_id})
    client.post("/api/chat", json={"message": "Как дела?", "session_id": session_id})

    response = client.post(
        "/api/chat", json={"message": "Расскажи подробнее", "session_id": session_id}
    ).json()

    assert response["matched_intent"] is None
    assert "кешбэк" not in response["answer"].lower()


def test_chat_asks_for_clarification_with_relevant_topic_suggestions(client):
    response = client.post(
        "/api/chat", json={"message": "Расскажи подробнее"}
    ).json()

    assert response["matched_intent"] is None
    assert "Уточните вопрос" in response["answer"]
    assert response["suggestions"] == [
        "Какие карты доступны в Finora?",
        "Как перевести деньги другому клиенту?",
        "Есть ли в Finora программа кешбэка?",
        "Как связаться со службой поддержки?",
    ]


def test_chat_topic_only_prompt_offers_a_clear_follow_up(client):
    response = client.post("/api/chat", json={"message": "Переводы"}).json()
    assert response["matched_intent"] == "transfers"
    assert "о переводах" in response["answer"]
    assert response["suggestions"]


def test_chat_repeats_the_last_assistant_answer(client):
    first = client.post(
        "/api/chat",
        json={"message": "Кто ты?", "session_id": "repeat-answer"},
    ).json()
    repeated = client.post(
        "/api/chat",
        json={"message": "Повтори", "session_id": "repeat-answer"},
    ).json()
    assert repeated["matched_intent"] == "repeat_answer"
    assert first["answer"] in repeated["answer"]


def test_chat_handles_everyday_conversation_without_bank_questions(client):
    cases = [
        ("Приветик", "greetings"),
        ("Хай", "greetings"),
        ("Доброе утро", "greetings"),
        ("Кто ты?", "identity"),
        ("Ты бот?", "identity"),
        ("Благодарю", "gratitude"),
        ("До завтра", "goodbye"),
        ("Ты молодец", "compliment"),
        ("Мне грустно", "emotions"),
        ("Объясни попроще", "clarification"),
        ("Помоги разобраться", "help"),
    ]
    for message, intent in cases:
        response = client.post("/api/chat", json={"message": message})
        assert response.status_code == 200
        assert response.json()["matched_intent"] == intent, message


def test_handoff_ticket_staff_history_status_and_reply(client, staff_headers):
    chat = client.post("/api/chat", json={"message": "Нужна помощь", "session_id": "history-session"})
    assert chat.status_code == 200
    handoff = client.post("/api/chat/handoff", json={"session_id": "history-session"})
    assert handoff.status_code == 200
    ticket_id = handoff.json()["ticket_id"]

    tickets = client.get("/api/tickets", headers=staff_headers)
    assert tickets.status_code == 200
    assert tickets.json()["tickets"][0]["id"] == ticket_id
    assert tickets.json()["tickets"][0]["status"] == "new"
    assert tickets.json()["tickets"][0]["last_message"]
    assert tickets.json()["tickets"][0]["nova_answer_wrong"] is False

    reply = client.post(
        f"/api/tickets/{ticket_id}/messages",
        headers=staff_headers,
        json={"message": "Здравствуйте, мы поможем."},
    )
    assert reply.status_code == 200
    messages = client.get(f"/api/tickets/{ticket_id}/messages", headers=staff_headers)
    assert messages.status_code == 200
    assert any(item["message"] == "Здравствуйте, мы поможем." for item in messages.json()["messages"])
    assert any(item["sender"] == "user" for item in messages.json()["messages"])
    assert all(item["text"] == item["message"] for item in messages.json()["messages"])
    assert all(item["content"] == item["message"] for item in messages.json()["messages"])
    assert {item["sender"] for item in messages.json()["messages"]} <= {"bot", "user", "staff"}

    status_response = client.patch(
        f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "in_progress"}
    )
    assert status_response.json()["status"] == "in_progress"
    flag_response = client.patch(
        f"/api/tickets/{ticket_id}",
        headers=staff_headers,
        json={"nova_answer_wrong": True},
    )
    assert flag_response.status_code == 200
    assert flag_response.json()["nova_answer_wrong"] is True
    assert flag_response.json()["status"] == "in_progress"
    persisted = client.get("/api/tickets", headers=staff_headers).json()["tickets"][0]
    assert persisted["nova_answer_wrong"] is True
    assert persisted["status"] == "in_progress"


def test_ticket_status_values_match_frontend(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужна помощь", "session_id": "status-session"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "status-session"}
    ).json()["ticket_id"]

    closed = client.patch(
        f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "closed"}
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert client.patch(
        f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "resolved"}
    ).status_code == 422

    reopened_chat = client.post(
        "/api/chat", json={"message": "Еще вопрос", "session_id": "status-session"}
    )
    assert reopened_chat.status_code == 200
    assert reopened_chat.json()["mode"] == "bot"


def test_closed_ticket_can_be_reopened_and_rejects_replies_while_closed(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужна помощь", "session_id": "reopen-session"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "reopen-session"}
    ).json()["ticket_id"]

    closed = client.patch(
        f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "closed"}
    )
    assert closed.status_code == 200
    rejected = client.post(
        f"/api/tickets/{ticket_id}/messages",
        headers=staff_headers,
        json={"message": "Ответ после закрытия"},
    )
    assert rejected.status_code == 409

    reopened = client.patch(
        f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "new"}
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "new"
    accepted = client.post(
        f"/api/tickets/{ticket_id}/messages",
        headers=staff_headers,
        json={"message": "Обращение снова в очереди"},
    )
    assert accepted.status_code == 200


def test_customer_websocket_receives_ticket_closed_and_cannot_send_afterward(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужна помощь", "session_id": "closed-ws-session"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "closed-ws-session"}
    ).json()["ticket_id"]

    from fastapi import WebSocketDisconnect

    with client.websocket_connect(
        f"/ws/tickets/{ticket_id}?session_id=closed-ws-session"
    ) as websocket:
        closed = client.patch(
            f"/api/tickets/{ticket_id}", headers=staff_headers, json={"status": "closed"}
        )
        assert closed.status_code == 200
        assert websocket.receive_json()["status"] == "closed"
        websocket.send_json({"message": "Не должно попасть в закрытое обращение"})
        assert websocket.receive_json()["type"] == "ticket_closed"
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()


def test_immediate_handoff_creates_session_and_ticket(client):
    response = client.post(
        "/api/chat/handoff", json={"session_id": "immediate-handoff-session"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ticket_id"]
    assert result["session_id"] == "immediate-handoff-session"
    assert result["status"] == "new"


def test_ticket_websocket_persists_client_messages(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужен оператор", "session_id": "ws-session"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "ws-session"}
    ).json()["ticket_id"]

    with client.websocket_connect(
        f"/ws/tickets/{ticket_id}?session_id=ws-session"
    ) as websocket:
        websocket.send_json({"message": "Проверка сообщения"})
        response = websocket.receive_json()
        assert response["sender"] == "user"
        assert response["message"] == "Проверка сообщения"
        assert response["text"] == response["content"] == response["message"]

    messages = client.get(
        f"/api/tickets/{ticket_id}/messages", headers=staff_headers
    ).json()["messages"]
    assert any(item["message"] == "Проверка сообщения" for item in messages)


def test_staff_websocket_receives_ticket_snapshot_and_updates(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужен оператор", "session_id": "staff-ws"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "staff-ws"}
    ).json()["ticket_id"]
    token = staff_headers["Authorization"].split(" ", 1)[1]

    with client.websocket_connect(f"/ws/tickets/{ticket_id}?token={token}") as websocket:
        initial = websocket.receive_json()
        assert initial == {
            "type": "ticket_update",
            "ticket_id": ticket_id,
            "session_id": "staff-ws",
            "status": "new",
            "nova_answer_wrong": False,
        }
        updated = client.patch(
            f"/api/tickets/{ticket_id}",
            headers=staff_headers,
            json={"status": "in_progress"},
        )
        assert updated.status_code == 200
        event = websocket.receive_json()
        assert event["type"] == "ticket_update"
        assert event["status"] == "in_progress"


def test_staff_websocket_assignment_is_broadcast_to_client(client, staff_headers):
    client.post("/api/chat", json={"message": "Нужен оператор", "session_id": "assign-ws"})
    ticket_id = client.post(
        "/api/chat/handoff", json={"session_id": "assign-ws"}
    ).json()["ticket_id"]
    token = staff_headers["Authorization"].split(" ", 1)[1]

    with client.websocket_connect(
        f"/ws/tickets/{ticket_id}?session_id=assign-ws"
    ) as client_socket:
        with client.websocket_connect(f"/ws/tickets/{ticket_id}?token={token}") as staff_socket:
            assignment = client_socket.receive_json()
            assert assignment["type"] == "ticket_assigned"
            assert assignment["ticket_id"] == ticket_id
            assert assignment["staff_username"] == "test-staff"
            snapshot = staff_socket.receive_json()
            assert snapshot["type"] == "ticket_update"
            assert snapshot["status"] == "new"


def test_chat_post_publishes_to_open_ticket_websockets(client, monkeypatch):
    from app.main import ticket_connections

    client.post("/api/chat", json={"message": "Передать оператору", "session_id": "post-ws"})
    ticket_id = client.post("/api/chat/handoff", json={"session_id": "post-ws"}).json()["ticket_id"]
    published = []

    async def record_publish(received_ticket_id, payload):
        published.append((received_ticket_id, payload))

    monkeypatch.setattr(ticket_connections, "publish", record_publish)
    response = client.post(
        "/api/chat", json={"message": "Новое сообщение через POST", "session_id": "post-ws"}
    )
    assert response.status_code == 200
    assert len(published) == 1
    published_ticket_id, payload = published[0]
    assert published_ticket_id == ticket_id
    assert payload["sender"] == "user"
    assert payload["text"] == payload["content"] == payload["message"] == "Новое сообщение через POST"


def test_unanswered_login_and_authorization(client, staff_headers):
    response = client.post("/api/chat", json={"message": "космический корабль на Марсе"})
    assert response.status_code == 200
    assert response.json()["matched_intent"] is None
    assert response.json()["suggestions"]
    faq_questions = {
        record["question"]
        for record in json.loads(
            (Path(__file__).parents[2] / "data" / "faq.json").read_text(encoding="utf-8")
        )
    }
    assert set(response.json()["suggestions"]) <= faq_questions
    unanswered = client.get("/api/unanswered-questions", headers=staff_headers)
    assert unanswered.status_code == 200
    assert unanswered.json()["questions"][0]["question"] == "космический корабль на Марсе"
    assert client.get("/api/tickets").status_code == 401
    assert client.post("/api/staff/login", json={"username": "wrong", "password": "wrong"}).status_code == 401


def test_chat_message_limit_and_card_redaction(client, staff_headers):
    too_long = client.post("/api/chat", json={"message": "а" * 501})
    assert too_long.status_code == 422

    response = client.post("/api/chat", json={"message": "Карта 4111 1111 1111 1111"})
    assert response.status_code == 200
    assert "номер карты" in response.json()["warning"].lower()
    ticket = client.post("/api/chat/handoff", json={"session_id": response.json()["session_id"]}).json()
    history = client.get(
        f"/api/tickets/{ticket['ticket_id']}/messages", headers=staff_headers
    ).json()["messages"]
    assert all("4111 1111 1111 1111" not in item["message"] for item in history)
    assert all("1111" not in item["message"] for item in history)


def test_rate_limit(client, monkeypatch):
    from app.main import rate_limiter

    rate_limiter.limit = 1
    first = client.post("/api/chat", json={"message": "Как открыть вклад?"})
    second = client.post("/api/chat", json={"message": "Как открыть вклад?"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_staff_password_and_jwt_secret_reject_weak_values():
    import pytest
    from pydantic import ValidationError

    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, staff_password="short", jwt_secret="s" * 32)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, staff_password="long-enough-staff-password", jwt_secret="too-short")
