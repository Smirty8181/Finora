from pathlib import Path

from app.evaluate_faq import EVALUATION_CASES, evaluate
from app.services.assistant import FAQSearch


def test_faq_contains_150_to_200_records():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    assert 150 <= len(search.records) <= 200


def test_required_faq_topic_intents_are_represented():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    intents = {record["intent"] for record in search.records}
    assert {
        "account_opening",
        "cards",
        "transfers",
        "payments",
        "deposits",
        "loans",
        "limits",
        "tariffs",
        "mobile_app",
        "security",
        "profile",
        "support",
    } <= intents


def test_every_faq_has_three_to_six_distinct_variants():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    for record in search.records:
        variants = record["questions"]
        assert 3 <= len(variants) <= 6, record["question"]
        assert len(set(variants)) == len(variants), record["question"]
        assert record["question"] in variants, record["question"]
        assert any(variant != record["question"] and len(variant) != len(record["question"]) for variant in variants), record["question"]


def test_each_faq_question_is_retrievable_above_threshold():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    for record in search.records:
        matched, confidence, _ = search.search(search.canonical_question(record))
        assert matched is not None, record["question"]
        assert matched["intent"] == record["intent"], record["question"]
        assert confidence >= 0.45, record["question"]


def test_each_question_variant_retrieves_expected_intent():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    for record in search.records:
        for variant in record["questions"]:
            matched, _, _ = search.search(variant)
            assert matched is not None, variant
            assert matched["intent"] == record["intent"], variant


def test_tfidf_finds_relevant_intents():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    cases = [
        ("как заблокировать потерянную карту", "cards"),
        ("хочу перевести деньги по телефону", "transfers"),
        ("где посмотреть график платежей кредита", "loans"),
        ("мне позвонил мошенник просит код банка", "security"),
        ("как открыть депозит", "deposits"),
        ("как оплатить коммуналку", "payments"),
        ("позвать оператора поддержки", "support"),
    ]
    for query, expected in cases:
        matched, confidence, _ = search.search(query)
        assert matched is not None, query
        assert matched["intent"] == expected, (query, matched["intent"], confidence)


def test_search_recovers_from_common_typos():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    cases = [
        ("Превет", "greetings"),
        ("кэш бек", "cashback"),
        ("украли карточку", "cards"),
        ("перевод не пришол", "transfers"),
        ("комисия за перевод", "transfers"),
    ]
    for query, expected in cases:
        matched, _, _ = search.search(query)
        assert matched is not None, query
        assert matched["intent"] == expected, query


def test_single_word_topics_return_relevant_follow_up_questions():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    cases = [
        ("Кешбек", "cashback"),
        ("Перевод", "transfers"),
        ("Лимиты", "limits"),
        ("Тарифы", "tariffs"),
        ("Поддержка", "support"),
        ("Приложение", "mobile_app"),
    ]
    for query, expected in cases:
        topic = search.topic(query)
        assert topic is not None, query
        assert topic["intent"] == expected
        assert topic["suggestions"]


def test_greeting_and_login_questions_find_answers():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    cases = [
        ("Привет", "greetings"),
        ("Приветик", "greetings"),
        ("Здарова", "greetings"),
        ("Как делишки?", "how_are_you"),
        ("Что ты умеешь?", "assistant_capabilities"),
        ("Кто ты?", "identity"),
        ("Спасибо", "gratitude"),
        ("Спасибки", "gratitude"),
        ("Благодарю", "gratitude"),
        ("Пока", "goodbye"),
        ("До завтра", "goodbye"),
        ("До встречи", "goodbye"),
        ("Ты бот?", "identity"),
        ("Кто ты?", "identity"),
        ("Мне грустно", "emotions"),
        ("Повтори", "repeat_answer"),
        ("Объясни попроще", "clarification"),
        ("Помоги разобраться", "help"),
        ("Ты тупой?", "frustration"),
        ("Войти в личный кабинет не получается", "login_access"),
        ("не могу войти в личный кабинет", "login_access"),
        ("Что будет, если пропустить платёж по кредиту?", "loans"),
        ("С карты списали деньги два раза", "payments"),
        ("Потерял карту, как её заблокировать?", "cards"),
        ("Как узнать размер ежемесячного платежа?", "loans"),
        ("Как включить тёмную тему?", "mobile_app"),
        ("Подскажите, сколько бонусов я накопил?", "cashback"),
        ("Почему мне не начислили кешбэк?", "cashback"),
    ]
    for query, expected in cases:
        matched, confidence, _ = search.search(query)
        assert matched is not None, query
        assert matched["intent"] == expected, (query, matched["intent"], confidence)


def test_requested_bank_questions_match_their_topics():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    cases = [
        ("Как открыть счёт в Finora?", "account_opening"),
        ("Какие документы нужны для регистрации?", "account_opening"),
        ("Сколько времени занимает открытие счёта?", "account_opening"),
        ("Можно ли открыть счёт онлайн?", "account_opening"),
        ("Есть ли возрастные ограничения?", "account_opening"),
        ("Можно ли иметь несколько счетов?", "account_opening"),
        ("Как узнать номер своего счёта?", "account_opening"),
        ("Где посмотреть реквизиты счёта?", "account_opening"),
        ("Как изменить личные данные?", "profile"),
        ("Как изменить номер телефона?", "profile"),
        ("Как изменить адрес электронной почты?", "profile"),
        ("Как закрыть банковский счёт?", "account_opening"),
        ("Какие карты доступны в Finora?", "cards"),
        ("Как заказать банковскую карту?", "cards"),
        ("Сколько стоит обслуживание карты?", "cards"),
        ("Как активировать новую карту?", "cards"),
        ("Как узнать баланс карты?", "cards"),
        ("Где посмотреть номер своей карты?", "cards"),
        ("Как установить или изменить PIN-код?", "cards"),
        ("Как заблокировать карту?", "cards"),
        ("Как разблокировать карту?", "cards"),
        ("Что делать, если я потерял карту?", "cards"),
        ("Что делать, если банкомат не выдал карту?", "cards"),
        ("Почему карта не проходит при оплате?", "cards"),
        ("Как установить лимит на покупки?", "limits"),
        ("Можно ли пользоваться картой за границей?", "cards"),
        ("Как перевести деньги другому человеку?", "transfers"),
        ("Как перевести деньги между своими счетами?", "transfers"),
        ("Сколько времени занимает перевод?", "transfers"),
        ("Почему перевод задерживается?", "transfers"),
        ("Можно ли отменить перевод?", "transfers"),
        ("Что делать, если я отправил деньги не тому человеку?", "transfers"),
        ("Есть ли комиссия за переводы?", "transfers"),
        ("Как посмотреть историю переводов?", "payments"),
        ("Как отправить деньги за границу?", "transfers"),
        ("Почему платёж был отклонён?", "payments"),
        ("Как оплатить коммунальные услуги?", "payments"),
        ("Как настроить регулярные платежи?", "payments"),
        ("Где посмотреть текущий баланс?", "payments"),
        ("Почему баланс отличается от ожидаемого?", "payments"),
        ("Как посмотреть историю операций?", "payments"),
        ("Как скачать выписку по счёту?", "profile"),
        ("Как найти конкретную транзакцию?", "payments"),
        ("Что означает статус «В обработке»?", "payments"),
        ("Почему списались деньги?", "payments"),
        ("Как оспорить неизвестную операцию?", "security"),
        ("Можно ли посмотреть расходы за месяц?", "payments"),
        ("Как узнать общую сумму своих расходов?", "payments"),
        ("Как открыть накопительный счёт?", "deposits"),
        ("Какие вклады доступны в Finora?", "deposits"),
        ("Какая процентная ставка по вкладам?", "deposits"),
        ("Как рассчитываются проценты?", "deposits"),
        ("Когда начисляются проценты?", "deposits"),
        ("Можно ли пополнять вклад?", "deposits"),
        ("Можно ли снять деньги досрочно?", "deposits"),
        ("Как закрыть вклад?", "deposits"),
        ("Где посмотреть начисленные проценты?", "deposits"),
        ("Как создать финансовую цель накопления?", "deposits"),
        ("Какие кредитные продукты доступны?", "loans"),
        ("Как подать заявку на кредит?", "loans"),
        ("Какие документы нужны для получения кредита?", "loans"),
        ("Как рассчитывается процентная ставка?", "loans"),
        ("Как узнать размер ежемесячного платежа?", "loans"),
        ("Как досрочно погасить кредит?", "loans"),
        ("Можно ли изменить дату платежа?", "loans"),
        ("Что произойдёт при просрочке платежа?", "loans"),
        ("Где посмотреть график платежей?", "loans"),
        ("Как получить справку о погашении кредита?", "loans"),
        ("Как защитить свой банковский аккаунт?", "security"),
        ("Что делать, если я забыл пароль?", "security"),
        ("Как восстановить доступ к аккаунту?", "login_access"),
        ("Что делать, если я подозреваю взлом?", "security"),
        ("Как включить двухфакторную аутентификацию?", "security"),
        ("Как изменить пароль?", "security"),
        ("Почему Finora запросила подтверждение личности?", "security"),
        ("Что делать, если пришло подозрительное SMS?", "security"),
        ("Может ли сотрудник Finora запросить мой пароль?", "security"),
        ("Как сообщить о мошенничестве?", "security"),
        ("Как отключить доступ к аккаунту на другом устройстве?", "security"),
        ("Как проверить подозрительную транзакцию?", "security"),
        ("Где скачать приложение Finora?", "mobile_app"),
        ("Почему приложение не открывается?", "mobile_app"),
        ("Что делать, если я не могу войти в приложение?", "login_access"),
        ("Почему не приходят уведомления?", "mobile_app"),
        ("Как включить push-уведомления?", "mobile_app"),
        ("Как обновить приложение?", "mobile_app"),
        ("Что делать, если приложение зависает?", "mobile_app"),
        ("Как изменить язык приложения?", "mobile_app"),
        ("Как включить тёмную тему?", "mobile_app"),
        ("Как связаться с технической поддержкой?", "mobile_app"),
        ("Есть ли в Finora программа кешбэка?", "cashback"),
        ("Как начисляется кешбэк?", "cashback"),
        ("Где посмотреть накопленный кешбэк?", "cashback"),
        ("Когда начисляются бонусы?", "cashback"),
        ("Как использовать накопленные бонусы?", "cashback"),
        ("Как подключить дополнительные услуги?", "support"),
        ("Как отключить платные услуги?", "support"),
        ("Есть ли ограничения на количество карт?", "cards"),
        ("Как получить информацию о новых продуктах?", "support"),
        ("Как оставить отзыв о Finora?", "support"),
    ]
    assert len(cases) == 100
    failures = []
    for index, (query, expected) in enumerate(cases, 1):
        matched, confidence, _ = search.search(query)
        actual = matched["intent"] if matched is not None else None
        if actual != expected:
            failures.append((index, expected, actual, round(confidence, 3)))
    assert not failures, [failure[0] for failure in failures]


def test_low_confidence_query_is_not_matched():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    matched, _, _ = search.search("космический корабль на Марсе")
    assert matched is None


def test_short_topics_return_related_questions():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    topics = [
        ("Кешбек", "cashback"),
        ("Карта", "cards"),
        ("Перевод", "transfers"),
        ("Вклад", "deposits"),
        ("Кредит", "loans"),
        ("Пароль", "security"),
        ("Приложение", "mobile_app"),
    ]
    for query, expected in topics:
        topic = search.topic(query)
        assert topic is not None, query
        assert topic["intent"] == expected
        assert topic["suggestions"]

    greeting = search.topic("Приветик, расскажи про кешбек")
    assert greeting is not None
    assert greeting["has_greeting"] is True
    assert len(greeting["suggestions"]) == 6


def test_30_question_evaluation_matches_expected_intents():
    search = FAQSearch(Path(__file__).parents[2] / "data" / "faq.json")
    correct, failures = evaluate(search)
    assert len(EVALUATION_CASES) == 30
    assert correct == len(EVALUATION_CASES), failures
