import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


class KeywordState:
    """
    Remembers every keyword across crawler runs and cycles.

    Each keyword has a status:
    - "active": searched again once its cooldown has passed (seed keywords always stay active)
    - "rejected": the AI keyword review turned it down; never proposed again
    - "retired": an expanded keyword that kept finding no illegal sites
    """

    def __init__(self, state_file: str = "keyword_state.json"):
        self.state_file = state_file
        self.keywords: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.state_file or not os.path.exists(self.state_file):
            return {}
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            keywords = data.get("keywords", {}) if isinstance(data, dict) else {}
            return keywords if isinstance(keywords, dict) else {}
        except (json.JSONDecodeError, OSError):
            print(f"⚠️ Could not read {self.state_file}; starting with an empty keyword history")
            return {}

    def save(self):
        if not self.state_file:
            return
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump({"keywords": self.keywords}, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def known(self) -> set:
        """Every keyword in the history, whatever its status."""
        return set(self.keywords)

    def _searched_within(self, info: Dict[str, Any], cooldown: timedelta) -> bool:
        last = info.get("last_searched_at")
        if not last:
            return False
        try:
            return self._now() - datetime.fromisoformat(last) < cooldown
        except ValueError:
            return False

    def due_keywords(self, seeds: List[str], cooldown_hours: float, limit: Optional[int] = None) -> List[str]:
        """
        Keywords to search at the start of a cycle: seeds first (in keywords.json order), then
        active expanded keywords, best performing first. Anything searched within the cooldown
        is left for a later cycle.
        """
        cooldown = timedelta(hours=cooldown_hours)
        for seed in seeds:
            info = self.keywords.setdefault(seed, {"source": "seed", "added_at": self._now().isoformat()})
            # A keyword moved into keywords.json is a seed from now on, even if it was expanded or rejected
            info["source"] = "seed"
            info["status"] = "active"

        due = [k for k in seeds if not self._searched_within(self.keywords[k], cooldown)]

        expanded = [
            (k, info) for k, info in self.keywords.items()
            if info.get("source") == "expanded" and info.get("status") == "active"
            and not self._searched_within(info, cooldown)
        ]
        expanded.sort(key=lambda item: (item[1].get("illegal_found", 0), item[1].get("site_count", 0)), reverse=True)
        due.extend(k for k, _ in expanded)

        return due[:limit] if limit else due

    def next_due_at(self, cooldown_hours: float) -> Optional[datetime]:
        """When the earliest active keyword comes out of its cooldown (None if none is active)."""
        times = []
        for info in self.keywords.values():
            if info.get("status") == "active" and info.get("last_searched_at"):
                try:
                    times.append(datetime.fromisoformat(info["last_searched_at"]) + timedelta(hours=cooldown_hours))
                except ValueError:
                    pass
        return min(times) if times else None

    def add_expanded(self, candidate: Dict[str, Any], search_round: int, reason: str = ""):
        self.keywords[candidate["keyword"]] = {
            "source": "expanded",
            "status": "active",
            "added_at": self._now().isoformat(),
            "added_in_round": search_round,
            "site_count": candidate.get("site_count", 0),
            "source_urls": candidate.get("source_urls", [])[:10],
            "review_reason": reason,
        }

    def reject(self, candidate: Dict[str, Any], reason: str):
        self.keywords[candidate["keyword"]] = {
            "source": "expanded",
            "status": "rejected",
            "added_at": self._now().isoformat(),
            "site_count": candidate.get("site_count", 0),
            "review_reason": reason,
        }

    def mark_searched(self, keyword: str, illegal_found: int, retire_after_empty_searches: int = 0):
        """Records a finished search (failed searches are not recorded, so they are retried)."""
        info = self.keywords.setdefault(keyword, {"source": "seed", "status": "active", "added_at": self._now().isoformat()})
        info["last_searched_at"] = self._now().isoformat()
        info["searches"] = info.get("searches", 0) + 1
        info["illegal_found"] = info.get("illegal_found", 0) + illegal_found

        if illegal_found:
            info["empty_searches"] = 0
        else:
            info["empty_searches"] = info.get("empty_searches", 0) + 1
            if (info.get("source") == "expanded" and retire_after_empty_searches
                    and info["empty_searches"] >= retire_after_empty_searches):
                info["status"] = "retired"
                print(f"  🗄️ Retired keyword '{keyword}' after {info['empty_searches']} searches with no illegal sites")
