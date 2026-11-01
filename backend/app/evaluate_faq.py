"""Reproducible intent-level evaluation on canonical FAQ question wording."""

from pathlib import Path
import os

from app.services.assistant import FAQSearch

FAQ_PATH = os.environ.get(
    "FAQ_PATH",
    str(Path(__file__).resolve().parents[2] / "data" / "faq.json"),
)

EVALUATION_CASES = [
    ("Как делишки?", "how_are_you"),
    ("Что ты умеешь?", "assistant_capabilities"),
    ("Как открыть счёт в Finora?", "account_opening"),
    ("Как заказать карту?", "cards"),
    ("Как заблокировать карту?", "cards"),
    ("Как перевести деньги другому клиенту?", "transfers"),
    ("Как перевести деньги по номеру телефона?", "transfers"),
    ("Сколько идёт банковский перевод?", "transfers"),
    ("Как оплатить коммунальные услуги?", "payments"),
    ("Как оплатить мобильную связь?", "payments"),
    ("Где посмотреть историю платежей?", "payments"),
    ("Как открыть вклад?", "deposits"),
    ("Как подать заявку на кредит?", "loans"),
    ("Как досрочно погасить кредит?", "loans"),
    ("Как восстановить пароль от приложения?", "security"),
    ("Не получается войти в личный кабинет", "login_access"),
    ("Мне пришёл подозрительный звонок от банка, что делать?", "security"),
    ("Как изменить номер телефона в профиле?", "profile"),
    ("Как связаться со службой поддержки?", "support"),
    ("Как оставить жалобу или предложение?", "support"),
    ("Что делать, если карта потерялась?", "cards"),
    ("Что делать, если перевод не пришёл?", "transfers"),
    ("Что делать при двойном списании?", "payments"),
    ("Что будет, если пропустить платёж по кредиту?", "loans"),
    ("Как узнать лимит переводов?", "limits"),
    ("Какие лимиты снятия наличных по карте?", "limits"),
    ("Где посмотреть тарифы Finora?", "tariffs"),
    ("Как сменить тариф обслуживания?", "tariffs"),
    ("Как установить приложение Finora?", "mobile_app"),
    ("Что делать, если приложение Finora не открывается?", "mobile_app"),
]


def evaluate(search: FAQSearch) -> tuple[int, list[dict]]:
    correct = 0
    failures = []
    for query, expected_intent in EVALUATION_CASES:
        matched, confidence, _ = search.search(query)
        actual_intent = matched["intent"] if matched is not None else None
        if actual_intent == expected_intent:
            correct += 1
        else:
            failures.append(
                {
                    "query": query,
                    "expected": expected_intent,
                    "actual": actual_intent,
                    "confidence": round(confidence, 4),
                }
            )
    return correct, failures


def main() -> int:
    search = FAQSearch(FAQ_PATH)
    correct, failures = evaluate(search)
    total = len(EVALUATION_CASES)
    print(f"Intent accuracy: {correct}/{total} ({correct / total:.1%})")
    for failure in failures:
        print(
            f"- {failure['query']}: expected={failure['expected']}, "
            f"actual={failure['actual']}, confidence={failure['confidence']}"
        )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
