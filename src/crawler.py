import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

from .keyword_manager import KeywordManager
from .search_engine import SearchEngine
from .url_extractor import URLExtractor
from .json_storage import JSONStorage
from .gemini_classifier import GeminiClassifier
from .keyword_expander import KeywordExpander


class GamblingDomainCrawler:
    def __init__(self, settings_file: str = "settings.json"):
        # Load environment variables from .env file
        load_dotenv()

        self.settings = self._load_settings(settings_file)
        self.keyword_manager = KeywordManager()
        self.search_engine = SearchEngine(
            headless=self.settings.get("headless_mode", True),
            captcha_wait_seconds=self.settings.get("captcha_wait_seconds", 300),
            page_load_timeout=self.settings.get("page_load_timeout", 20),
        )
        self.url_extractor = URLExtractor(
            remove_tracking_params=self.settings.get("remove_tracking_params", True)
        )
        self.storage = JSONStorage(self.settings.get("output_file", "results.json"))
        self.keyword_expander = KeywordExpander(
            min_site_count=self.settings.get("min_keyword_site_count", 2),
            min_confidence=self.settings.get("min_expansion_confidence", 0.7),
            max_keywords_per_round=self.settings.get("max_new_keywords_per_round", 10),
        )

        # Initialize Gemini classifier (API key loaded automatically from .env)
        try:
            self.classifier = GeminiClassifier()
            self.use_classifier = self.settings.get("use_gemini_classifier", True)
        except ValueError as e:
            print(f"⚠️ Warning: Gemini classifier initialization failed - {e}")
            self.classifier = None
            self.use_classifier = False

    def _load_settings(self, settings_file: str) -> Dict[str, Any]:
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _classify_visited_results(self, visited_results: list) -> tuple:
        """
        Classifies visited results (URL + HTML pairs) and filters for illegal gambling sites.

        Args:
            visited_results: list of (url, html_content) tuples

        Returns:
            (filtered_urls, classification_results) tuple, where
            classification_results[i] is the result for filtered_urls[i]
        """
        if not self.use_classifier or not self.classifier:
            # Return all URLs if classifier is unavailable
            return [url for url, _ in visited_results], None

        filtered_urls = []
        classification_results = []

        for url, html_content in visited_results:
            if not html_content:
                print(f"  ⏭️ Skipping {url} - no HTML content")
                continue

            print(f"  🔍 Classifying: {url}")
            result = self.classifier.classify_url(url, html_content)

            if result.get("error") is None and result.get("is_illegal"):
                print(f"  ✅ Illegal site detected: {url} (confidence: {result.get('confidence', 0):.2f})")
                filtered_urls.append(url)
                classification_results.append(result)
            elif result.get("error"):
                print(f"  ⚠️ Classification error {url}: {result.get('error')}")
            else:
                print(f"  ❌ Not an illegal gambling site: {url}")

        return filtered_urls, classification_results

    def crawl(self):
        print("🚀 Starting illegal gambling site crawler...")

        keywords = self.keyword_manager.generate_combinations(
            include_pairs=self.settings.get("combine_keywords", True)
        )
        print(f"📋 Generated {len(keywords)} search queries")

        delay = self.settings.get("delay_between_searches", 2)
        max_links_per_search = self.settings.get("max_links_per_search", 10)
        existing_urls = self.storage.get_existing_urls()

        # Round 0 searches keywords.json; each later round searches keywords detected on the
        # illegal sites of the previous round, until no new keywords come up or the limit is hit
        expand = self.settings.get("expand_keywords", False)
        max_rounds = self.settings.get("max_expansion_rounds", 2) if expand else 0
        if expand and not self.use_classifier:
            print("⚠️ Keyword expansion needs the Gemini classifier; only the seed keywords will be searched")
            max_rounds = 0

        searched = {KeywordExpander.normalize(k) for k in keywords}
        round_keywords = [{"keyword": k} for k in keywords]
        expansion_log = {"started_at": datetime.now(timezone.utc).isoformat(), "rounds": []}
        first_search = True

        try:
            for round_no in range(max_rounds + 1):
                if round_no > 0:
                    print(f"\n🔁 Round {round_no}: searching {len(round_keywords)} keywords found in round {round_no - 1}")

                round_results = []
                for i, entry in enumerate(round_keywords, 1):
                    keyword = entry["keyword"]
                    if not first_search:
                        print(f"  ⏳ Waiting {delay}s before next search...")
                        time.sleep(delay)
                    first_search = False

                    print(f"\n🔎 [round {round_no}, {i}/{len(round_keywords)}] Searching keyword: {keyword}")
                    try:
                        found = self._process_keyword(keyword, max_links_per_search, existing_urls, round_no)
                    except Exception as e:
                        # One failed search (e.g. CAPTCHA or timeout) should not stop the whole crawl
                        print(f"  ❌ Search failed for keyword '{keyword}': {e!r}")
                        found = []
                    entry["illegal_found"] = len(found)
                    round_results.extend(found)

                expansion_log["rounds"].append({
                    "round": round_no,
                    "keywords": round_keywords,
                    "illegal_found": len(round_results),
                })
                self._save_expansion_log(expansion_log)

                if round_no == max_rounds:
                    break

                round_keywords = self.keyword_expander.select(round_results, searched)
                if not round_keywords:
                    print(f"\n🛑 No new keywords from round {round_no}; stopping expansion")
                    break
                searched.update(e["keyword"] for e in round_keywords)
                print(f"\n🌱 New keywords for round {round_no + 1}:")
                for e in round_keywords:
                    print(f"  - {e['keyword']} ({e['site_count']} sites, score {e['score']})")
        finally:
            self.search_engine.close()

        self._print_final_stats()

    def _save_expansion_log(self, expansion_log: Dict[str, Any]):
        """Appends this run's rounds to the expansion log so later runs can be compared."""
        log_file = self.settings.get("expansion_log_file")
        if not log_file:
            return
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                runs = json.load(f)
            if not isinstance(runs, list):
                runs = []
        except (FileNotFoundError, json.JSONDecodeError):
            runs = []
        # Replace this run's entry (rewritten after every round) or add it
        runs = [r for r in runs if r.get("started_at") != expansion_log["started_at"]]
        runs.append(expansion_log)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(runs, f, indent=2, ensure_ascii=False)

    def _process_keyword(self, keyword: str, max_links_per_search: int, existing_urls: set,
                         search_round: int = 0) -> List[Dict[str, Any]]:
        """Searches one keyword and saves the illegal sites; returns their classification results."""
        self.search_engine.search_google(keyword)

        visited_results = self.search_engine.visit_search_result_links(max_links=max_links_per_search)

        if not visited_results:
            print(f"  ⚠️ No links visited (keyword: {keyword})")
            return []

        print(f"  📄 Visited {len(visited_results)} links")

        # Skip known URLs, and duplicates within this batch (different links can redirect to the same page)
        new_visited_results = []
        batch_urls = set()
        for url, html in visited_results:
            url = self.url_extractor.clean_url(url)
            if url not in existing_urls and url not in batch_urls:
                batch_urls.add(url)
                new_visited_results.append((url, html))

        if not new_visited_results:
            print(f"  ℹ️ No new URLs (keyword: {keyword})")
            return []

        print(f"  🆕 Found {len(new_visited_results)} new URLs")

        filtered_urls, classification_results = self._classify_visited_results(new_visited_results)

        if filtered_urls:
            self.storage.save_results(filtered_urls, keyword, classification_results, search_round)
            existing_urls.update(filtered_urls)
            print(f"  💾 Saved {len(filtered_urls)} illegal gambling sites (keyword: {keyword})")
        else:
            print(f"  ℹ️ No illegal gambling sites found (keyword: {keyword})")
        return classification_results or []

    def _print_final_stats(self):
        stats = self.storage.get_stats()
        print("\n" + "="*50)
        print("📊 Crawl Summary")
        print("="*50)
        print(f"📁 Total entries: {stats['total_entries']}")
        print(f"🔗 Unique URLs: {stats['unique_urls']}")
        print(f"🔤 Keywords used: {stats['keywords_used']}")
        print(f"💾 Output file: {self.settings.get('output_file', 'results.json')}")
        print("="*50)
