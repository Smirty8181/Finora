import json
import re
from difflib import get_close_matches
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class FAQSearch:
    TOPICS = (
        ("cashback", "кешбэке", ("кешбек", "кешбэк", "кэшбек", "кэшбэк", "cashback", "бонус")),
        ("cards", "карте", ("карт", "карточ", "пластик")),
        ("transfers", "переводах", ("перевод", "перевести")),
        ("payments", "платежах", ("платеж", "оплат", "коммун")),
        ("limits", "лимитах", ("лимит", "огранич")),
        ("tariffs", "тарифах и комиссиях", ("тариф", "комисс")),
        ("deposits", "вкладах", ("вклад", "депозит", "накоплен")),
        ("loans", "кредитах", ("кредит", "займ")),
        ("security", "безопасности и пароле", ("парол", "безопас", "взлом", "защит")),
        ("mobile_app", "приложении", ("приложен", "апп", "мобилк")),
        ("support", "поддержке", ("поддерж", "оператор", "сотрудник", "специалист")),
        ("profile", "личных данных", ("профил", "данн", "телефон", "почт")),
        ("account_opening", "счёте", ("счет", "счёт", "реквизит")),
    )
    TOPIC_FILLER = {
        "а", "бы", "быть", "вопрос", "есть", "мне", "можно", "немного", "нибудь", "ново",
        "о", "об", "пожалуйста", "помоги", "помощь", "по", "поговорим", "подскажи",
        "подскажите", "привет", "приветик", "расскажи", "рассказать", "с", "хай", "хочу",
        "что", "чуть", "узнать", "про", "как", "здравствуй", "здравствуйте", "здарова", "доброе",
        "утро", "вечер", "день", "дела", "делишки",
    }

    def __init__(self, path: str | Path, threshold: float = 0.45):
        with Path(path).open(encoding="utf-8") as file:
            self.records = json.load(file)
        if not self.records:
            raise ValueError("FAQ must contain at least one record")
        for record in self.records:
            questions = record.get("questions")
            if not isinstance(questions, list) or not 3 <= len(questions) <= 6:
                raise ValueError("Every FAQ record must have 3 to 6 question variants")
            if record.get("question") not in questions:
                raise ValueError("The canonical question must be one of its variants")
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(
            preprocessor=self._normalize,
            token_pattern=r"(?u)\b\w+\b",
            ngram_range=(1, 2),
        )
        self.char_vectorizer = TfidfVectorizer(
            preprocessor=self._normalize,
            analyzer="char_wb",
            ngram_range=(2, 5),
        )
        self.documents = []
        self.record_indexes = []
        for index, item in enumerate(self.records):
            for question in item["questions"]:
                self.documents.append(question)
                self.record_indexes.append(index)
            for keyword in item.get("keywords", []):
                if len(keyword.split()) > 1:
                    self.documents.append(keyword)
                    self.record_indexes.append(index)
        self.matrix = self.vectorizer.fit_transform(self.documents)
        self.char_matrix = self.char_vectorizer.fit_transform(self.documents)
        self.vocabulary = tuple(self.vectorizer.vocabulary_)

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = text.lower().replace("ё", "е")
        normalized = re.sub(r"\b(?:кеш|кэш)\s*б[еэ]к\b", "кэшбэк", normalized)
        normalized = re.sub(r"\b(?:(?:кеш|кэш)б[еэ]к\w*|cashback)\b", "кэшбэк", normalized)
        normalized = re.sub(r"\bкарточк\w*", "карта", normalized)
        normalized = re.sub(r"\bсмс\b", "сообщение", normalized)
        return re.sub(r"[^\w\s]", " ", normalized)

    def topic(self, query: str) -> dict | None:
        normalized = self.correct_typos(query)
        tokens = normalized.split()
        for intent, name, stems in self.TOPICS:
            topic_tokens = {
                token
                for token in tokens
                if any(token.startswith(stem) for stem in stems)
            }
            if not topic_tokens:
                continue
            other_tokens = set(tokens) - topic_tokens - self.TOPIC_FILLER
            if other_tokens:
                continue
            suggestions = [
                self.canonical_question(record)
                for record in self.records
                if record["intent"] == intent
            ][:6 if intent == "cashback" else 4]
            if not suggestions:
                continue
            has_greeting = any(
                token.startswith(("привет", "здравств", "здарова", "хай"))
                for token in tokens
            )
            return {
                "intent": intent,
                "name": name,
                "suggestions": suggestions,
                "has_greeting": has_greeting,
            }
        return None

    @staticmethod
    def canonical_question(record: dict) -> str:
        return record["question"]

    def correct_typos(self, query: str) -> str:
        corrected = []
        for token in self._normalize(query).split():
            if len(token) < 5 or token in self.vectorizer.vocabulary_:
                corrected.append(token)
                continue
            closest = get_close_matches(token, self.vocabulary, n=1, cutoff=0.82)
            corrected.append(closest[0] if closest else token)
        return " ".join(corrected)

    def search(self, query: str, limit: int = 3, context_intent: str | None = None):
        detected_topic = self.topic(query)
        if detected_topic is not None:
            topic_records = [
                record for record in self.records if record["intent"] == detected_topic["intent"]
            ]
            return topic_records[0], 1.0, topic_records[:limit]
        query = self.correct_typos(query)
        query_vector = self.vectorizer.transform([query])
        char_query_vector = self.char_vectorizer.transform([query])
        word_scores = cosine_similarity(query_vector, self.matrix).flatten()
        char_scores = cosine_similarity(char_query_vector, self.char_matrix).flatten()
        variant_scores = [
            max(word, 0.75 * word + 0.25 * char)
            for word, char in zip(word_scores, char_scores)
        ]
        scores_by_record = [0.0] * len(self.records)
        for index, score in zip(self.record_indexes, variant_scores):
            scores_by_record[index] = max(scores_by_record[index], float(score))
        query_tokens = self._normalize(query).split()
        has_account = any(token.startswith("счет") for token in query_tokens)
        has_card = any(token.startswith(("карт", "пластик")) for token in query_tokens)
        if has_account != has_card:
            opposing_intent = "cards" if has_account else "account_opening"
            for index, record in enumerate(self.records):
                if record["intent"] == opposing_intent:
                    scores_by_record[index] *= 0.7
        indexes = sorted(range(len(scores_by_record)), key=scores_by_record.__getitem__, reverse=True)[:limit]
        results = [
            (self.records[index], scores_by_record[index])
            for index in indexes
            if scores_by_record[index] > 0
        ]
        best = results[0] if results else (None, 0.0)
        matched = best[0] if best[1] >= self.threshold else None
        confidence = best[1]
        if matched is None and context_intent:
            contextual = next(
                (
                    (self.records[index], scores_by_record[index])
                    for index in sorted(
                        range(len(scores_by_record)),
                        key=scores_by_record.__getitem__,
                        reverse=True,
                    )
                    if self.records[index]["intent"] == context_intent
                    and scores_by_record[index] >= 0.25
                ),
                None,
            )
            if contextual:
                matched = contextual[0]
                confidence = contextual[1]
                if matched not in [record for record, _ in results]:
                    results.append(contextual)
        return matched, confidence, [record for record, _ in results]
