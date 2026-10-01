import time
import json
import requests
import os
from typing import Dict, Any
from urllib.parse import urlparse
from dotenv import load_dotenv

from .keyword_manager import KeywordManager
from .search_engine import SearchEngine
from .url_extractor import URLExtractor
from .json_storage import JSONStorage
from .gemini_classifier import GeminiClassifier


class GamblingDomainCrawler:
    def __init__(self, settings_file: str = "settings.json"):
        # Load environment variables from .env file
        load_dotenv()

        self.settings = self._load_settings(settings_file)
        self.keyword_manager = KeywordManager()
        self.search_engine = SearchEngine(headless=self.settings.get("headless_mode", True))
        self.url_extractor = URLExtractor(
            remove_tracking_params=self.settings.get("remove_tracking_params", True)
        )
        self.storage = JSONStorage(self.settings.get("output_file", "results.json"))

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

    def _fetch_html_from_url(self, url: str, timeout: int = 10) -> str:
        """Fetches HTML content from the given URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except Exception as e:
            print(f"  ❌ Failed to fetch URL {url}: {e}")
            return ""

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

    def _classify_and_filter_urls(self, urls: list) -> tuple:
        """
        Classifies a list of URLs and filters for illegal gambling sites.

        Returns:
            (filtered_urls, classification_results) tuple
        """
        if not self.use_classifier or not self.classifier:
            return urls, None

        filtered_urls = []
        classification_results = []

        for url in urls:
            print(f"  📥 Fetching content: {url}")
            html_content = self._fetch_html_from_url(url)

            if not html_content:
                print(f"  ⏭️ Skipping {url} - failed to fetch content")
                continue

            print(f"  🔍 Classifying: {url}")
            result = self.classifier.classify_url(url, html_content)
            classification_results.append(result)

            if result.get("error") is None and result.get("is_illegal"):
                print(f"  ✅ Illegal site detected: {url} (confidence: {result.get('confidence', 0):.2f})")
                filtered_urls.append(url)
            elif result.get("error"):
                print(f"  ⚠️ Classification error {url}: {result.get('error')}")
            else:
                print(f"  ❌ Not an illegal gambling site: {url}")

        return filtered_urls, classification_results

    def crawl(self):
        print("🚀 Starting illegal gambling site crawler...")

        keywords = self.keyword_manager.generate_combinations()
        print(f"📋 Generated {len(keywords)} keyword combinations")

        delay = self.settings.get("delay_between_searches", 2)
        max_links_per_search = self.settings.get("max_links_per_search", 10)
        existing_urls = self.storage.get_existing_urls()

        for i, keyword in enumerate(keywords, 1):
            print(f"\n🔎 [{i}/{len(keywords)}] Searching keyword: {keyword}")

            self.search_engine.search_google(keyword)

            visited_results = self.search_engine.visit_search_result_links(max_links=max_links_per_search)

            if visited_results:
                print(f"  📄 Visited {len(visited_results)} links")

                new_visited_results = [
                    (url, html) for url, html in visited_results
                    if url not in existing_urls
                ]

                if new_visited_results:
                    print(f"  🆕 Found {len(new_visited_results)} new URLs")

                    filtered_urls, classification_results = self._classify_visited_results(new_visited_results)

                    if filtered_urls:
                        self.storage.save_results(filtered_urls, keyword, classification_results)
                        existing_urls.update(filtered_urls)
                        print(f"  💾 Saved {len(filtered_urls)} illegal gambling sites (keyword: {keyword})")
                    else:
                        print(f"  ℹ️ No illegal gambling sites found (keyword: {keyword})")
                else:
                    print(f"  ℹ️ No new URLs (keyword: {keyword})")
            else:
                print(f"  ⚠️ No links visited (keyword: {keyword})")

            if i < len(keywords):
                print(f"  ⏳ Waiting {delay}s before next search...")
                time.sleep(delay)

        self.search_engine.close()
        self._print_final_stats()

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
