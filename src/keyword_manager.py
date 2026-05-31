import json
from itertools import combinations
from typing import List


class KeywordManager:
    def __init__(self, keywords_file: str = "keywords.json"):
        self.keywords_file = keywords_file
        self.keywords = []

    def load_keywords(self) -> List[str]:
        try:
            with open(self.keywords_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.keywords = data.get('keywords', [])
            return self.keywords
        except FileNotFoundError:
            print(f"Keywords file {self.keywords_file} not found")
            return []
        except json.JSONDecodeError:
            print(f"Invalid JSON format in {self.keywords_file}")
            return []

    def generate_combinations(self) -> List[str]:
        if not self.keywords:
            self.load_keywords()

        all_keywords = self.keywords.copy()

        for combo in combinations(self.keywords, 2):
            all_keywords.append(" ".join(combo))

        return all_keywords