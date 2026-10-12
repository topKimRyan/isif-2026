import re
from typing import Any, Dict, Iterable, List


class KeywordExpander:
    """
    Picks new search keywords from the detected_keywords of illegal sites found in a round.

    A keyword is chosen when enough different illegal sites mention it, it has not been
    searched yet, and it is specific enough to be worth a Google search on its own.
    """

    # Words that appear on almost every gambling page; searching them alone mostly returns
    # legal operators, news, and reference pages instead of new illegal sites
    GENERIC_KEYWORDS = {
        "casino", "casinos", "online casino", "gambling", "online gambling", "gamble",
        "bet", "bets", "betting", "online betting", "sports betting", "sportsbook",
        "slot", "slots", "poker", "baccarat", "roulette", "blackjack", "lottery", "jackpot",
        "bonus", "bonuses", "welcome bonus", "free spins", "promotion", "promo code",
        "deposit", "withdraw", "withdrawal", "payment", "crypto", "bitcoin", "cryptocurrency",
        "login", "sign up", "register", "registration", "account", "vip",
        "odds", "games", "live casino", "esports", "toto",
    }

    def __init__(
        self,
        min_site_count: int = 2,
        min_confidence: float = 0.7,
        max_keywords_per_round: int = 10,
    ):
        self.min_site_count = min_site_count
        self.min_confidence = min_confidence
        self.max_keywords_per_round = max_keywords_per_round

    @staticmethod
    def normalize(keyword: str) -> str:
        """
        Turns a detected keyword into a search query.

        Gemini writes non-English keywords as "바카라 (baccarat)"; the English translation is
        used because the crawler searches in English only.
        """
        keyword = str(keyword)
        match = re.search(r"^(.*?)\(([^()]+)\)\s*$", keyword)
        if match and match.group(1).strip():
            original, note = match.group(1), match.group(2)
            # "Bet365 (UK)" is already English; keep it and drop the note
            keyword = original if original.isascii() else note
        keyword = keyword.strip(" \t\"'`.,;:!?-·").lower()
        return re.sub(r"\s+", " ", keyword)

    def _is_searchable(self, keyword: str) -> bool:
        if len(keyword) < 2 or len(keyword) > 50 or len(keyword.split()) > 5:
            return False
        if keyword in self.GENERIC_KEYWORDS:
            return False
        if keyword.isdigit():
            return False
        # English only: drop keywords that are still non-English (no translation was given)
        if not keyword.isascii():
            return False
        # URLs and domains find the site itself, not new sites
        if "://" in keyword or "/" in keyword or re.search(r"\w\.[a-z]{2,}$", keyword):
            return False
        return True

    def select(self, classification_results: Iterable[Dict[str, Any]], searched: set) -> List[Dict[str, Any]]:
        """
        Ranks candidate keywords from one round's illegal-site results.

        Args:
            classification_results: GeminiClassifier results for the illegal sites found
            searched: normalized keywords already searched (not modified here)

        Returns:
            Up to max_keywords_per_round entries, best first:
            {"keyword": str, "site_count": int, "score": float, "source_urls": [str]}
        """
        candidates: Dict[str, Dict[str, Any]] = {}

        for result in classification_results:
            confidence = result.get("confidence", 0.0)
            if confidence < self.min_confidence:
                continue
            url = result.get("url", "")

            # Count each keyword once per site, even if Gemini listed it twice
            site_keywords = {self.normalize(k) for k in result.get("detected_keywords", [])}
            for keyword in site_keywords:
                if keyword in searched or not self._is_searchable(keyword):
                    continue
                entry = candidates.setdefault(keyword, {"keyword": keyword, "score": 0.0, "source_urls": []})
                if url not in entry["source_urls"]:
                    entry["source_urls"].append(url)
                    entry["score"] += confidence

        selected = []
        for entry in candidates.values():
            entry["site_count"] = len(entry["source_urls"])
            entry["score"] = round(entry["score"], 3)
            if entry["site_count"] >= self.min_site_count:
                selected.append(entry)

        selected.sort(key=lambda e: (e["site_count"], e["score"]), reverse=True)
        return selected[: self.max_keywords_per_round]
