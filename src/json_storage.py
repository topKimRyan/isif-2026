import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any


class JSONStorage:
    def __init__(self, output_file: str = "results.json"):
        self.output_file = output_file

    def save_results(self, urls: List[str], keyword: str, classification_results: List[Dict[str, Any]] = None) -> None:
        kst = timezone(timedelta(hours=9))
        timestamp = datetime.now(kst).isoformat()

        new_entries = []
        for i, url in enumerate(urls):
            entry = {
                "url": url,
                "keyword_used": keyword,
                "collected_at": timestamp
            }

            # Attach classification result if available
            if classification_results and i < len(classification_results):
                result = classification_results[i]
                entry["is_illegal"] = result.get("is_illegal", False)
                entry["gemini_confidence"] = result.get("confidence", 0.0)
                entry["gemini_reason"] = result.get("reason", "")
                entry["gemini_error"] = result.get("error", None)
                if result.get("detected_keywords"):
                    entry["detected_keywords"] = result.get("detected_keywords")

            new_entries.append(entry)

        existing_data = self.load_existing_data()
        existing_data.extend(new_entries)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)

        print(f"  💾 Saved {len(new_entries)} URLs (keyword: '{keyword}')")

    def load_existing_data(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.output_file):
            return []

        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def get_existing_urls(self) -> set:
        existing_data = self.load_existing_data()
        return {entry.get("url", "") for entry in existing_data}

    def get_stats(self) -> Dict[str, Any]:
        existing_data = self.load_existing_data()
        total_urls = len(existing_data)
        unique_urls = len(set(entry.get("url", "") for entry in existing_data))
        keywords_used = set(entry.get("keyword_used", "") for entry in existing_data)

        return {
            "total_entries": total_urls,
            "unique_urls": unique_urls,
            "keywords_used": len(keywords_used),
            "keywords": list(keywords_used)
        }
