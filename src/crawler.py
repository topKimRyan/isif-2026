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
        # .env 파일에서 환경 변수 로드
        load_dotenv()
        
        self.settings = self._load_settings(settings_file)
        self.keyword_manager = KeywordManager()
        self.search_engine = SearchEngine(headless=self.settings.get("headless_mode", True))
        self.url_extractor = URLExtractor(
            remove_tracking_params=self.settings.get("remove_tracking_params", True)
        )
        self.storage = JSONStorage(self.settings.get("output_file", "results.json"))
        
        # Gemini 분류기 초기화 (.env 파일에서 API 키 자동 로드)
        try:
            # GeminiClassifier는 자동으로 .env에서 GEMINI_API_KEY를 로드함
            self.classifier = GeminiClassifier()
            self.use_classifier = self.settings.get("use_gemini_classifier", True)
        except ValueError as e:
            print(f"⚠️ 경고: Gemini 분류기 초기화 실패 - {e}")
            self.classifier = None
            self.use_classifier = False

    def _load_settings(self, settings_file: str) -> Dict[str, Any]:
        # 설정 파일 로드
        with open(settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _fetch_html_from_url(self, url: str, timeout: int = 10) -> str:
        """URL에서 HTML 콘텐츠를 가져옵니다"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.encoding = response.apparent_encoding or 'utf-8'
            return response.text
        except Exception as e:
            print(f"  ❌ URL 가져오기 실패 {url}: {e}")
            return ""

    def _classify_visited_results(self, visited_results: list) -> tuple:
        """
        방문한 결과(URL과 HTML 쌍)를 분류하고 불법 도박 사이트만 필터링합니다
        
        Args:
            visited_results: [(url, html_content), ...] 형태의 리스트
        
        Returns:
            (filtered_urls, classification_results) 튜플
        """
        if not self.use_classifier or not self.classifier:
            # 분류기가 없으면 모든 URL 반환
            return [url for url, _ in visited_results], None

        filtered_urls = []
        classification_results = []

        for url, html_content in visited_results:
            if not html_content:
                print(f"  ⏭️ 건너뛰기 {url} - HTML 콘텐츠 없음")
                continue

            # Gemini로 불법 사이트 판별
            print(f"  🔍 분류 중: {url}")
            result = self.classifier.classify_url(url, html_content)
            classification_results.append(result)

            # 오류가 없고 불법 사이트면 필터링된 목록에 추가
            if result.get("error") is None and result.get("is_illegal"):
                print(f"  ✅ 불법 사이트 탐지: {url} (신뢰도: {result.get('confidence', 0):.2f})")
                filtered_urls.append(url)
            elif result.get("error"):
                print(f"  ⚠️ 분류 오류 {url}: {result.get('error')}")
            else:
                print(f"  ❌ 불법 도박 사이트 아님: {url}")

        return filtered_urls, classification_results

    def _classify_and_filter_urls(self, urls: list) -> tuple:
        """
        URL 목록을 분류하고 불법 도박 사이트만 필터링합니다
        
        Returns:
            (filtered_urls, classification_results) 튜플
        """
        if not self.use_classifier or not self.classifier:
            return urls, None

        filtered_urls = []
        classification_results = []

        for url in urls:
            # URL에서 HTML 콘텐츠 가져오기
            print(f"  📥 콘텐츠 가져오는 중: {url}")
            html_content = self._fetch_html_from_url(url)

            if not html_content:
                # HTML을 가져올 수 없으면 건너뛰기
                print(f"  ⏭️ 건너뛰기 {url} - 콘텐츠 가져오기 실패")
                continue

            # Gemini로 불법 사이트 판별
            print(f"  🔍 분류 중: {url}")
            result = self.classifier.classify_url(url, html_content)
            classification_results.append(result)

            # 오류가 없고 불법 사이트면 필터링된 목록에 추가
            if result.get("error") is None and result.get("is_illegal"):
                print(f"  ✅ 불법 사이트 탐지: {url} (신뢰도: {result.get('confidence', 0):.2f})")
                filtered_urls.append(url)
            elif result.get("error"):
                print(f"  ⚠️ 분류 오류 {url}: {result.get('error')}")
            else:
                print(f"  ❌ 불법 도박 사이트 아님: {url}")

        return filtered_urls, classification_results

    def crawl(self):
        print("🚀 불법 도박 사이트 크롤러 시작...")

        # 키워드 조합 생성
        keywords = self.keyword_manager.generate_combinations()
        print(f"📋 {len(keywords)}개의 키워드 조합 생성 완료")

        delay = self.settings.get("delay_between_searches", 2)
        max_links_per_search = self.settings.get("max_links_per_search", 10)
        existing_urls = self.storage.get_existing_urls()

        # 모든 키워드에 대해 검색 수행
        for i, keyword in enumerate(keywords, 1):
            print(f"\n🔎 [{i}/{len(keywords)}] 검색 키워드: {keyword}")

            # Google 검색 수행
            self.search_engine.search_google(keyword)

            # 검색 결과 링크를 직접 방문하며 HTML 수집
            visited_results = self.search_engine.visit_search_result_links(max_links=max_links_per_search)
            
            # 새로운 URL 필터링 및 분류
            if visited_results:
                print(f"  📄 {len(visited_results)}개의 링크 방문 완료")
                
                # 이미 존재하는 URL 제외
                new_visited_results = [
                    (url, html) for url, html in visited_results 
                    if url not in existing_urls
                ]
                
                if new_visited_results:
                    print(f"  🆕 {len(new_visited_results)}개의 새로운 URL 발견")
                    
                    # Gemini 분류기를 사용하여 불법 사이트만 필터링
                    filtered_urls, classification_results = self._classify_visited_results(new_visited_results)
                    
                    if filtered_urls:
                        # 불법 사이트로 판별된 URL만 저장
                        self.storage.save_results(filtered_urls, keyword, classification_results)
                        existing_urls.update(filtered_urls)
                        print(f"  💾 {len(filtered_urls)}개의 불법 도박 사이트 저장 완료 (키워드: {keyword})")
                    else:
                        print(f"  ℹ️ 불법 도박 사이트 미발견 (키워드: {keyword})")
                else:
                    print(f"  ℹ️ 새로운 URL 없음 (키워드: {keyword})")
            else:
                print(f"  ⚠️ 방문한 링크 없음 (키워드: {keyword})")

            # 다음 검색 전 대기
            if i < len(keywords):
                print(f"  ⏳ 다음 검색까지 {delay}초 대기 중...")
                time.sleep(delay)

        # 브라우저 종료 및 결과 출력
        self.search_engine.close()
        self._print_final_stats()

    def _print_final_stats(self):
        stats = self.storage.get_stats()
        print("\n" + "="*50)
        print("📊 크롤링 결과 요약")
        print("="*50)
        print(f"📁 총 항목 수: {stats['total_entries']}")
        print(f"🔗 고유 URL 수: {stats['unique_urls']}")
        print(f"🔤 사용된 키워드 수: {stats['keywords_used']}")
        print(f"💾 출력 파일: {self.settings.get('output_file', 'results.json')}")
        print("="*50)
