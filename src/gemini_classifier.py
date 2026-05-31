import json
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from bs4 import BeautifulSoup
import re


class GeminiClassifier:
    """Gemini API를 사용하여 불법 도박 사이트를 판별하는 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        """
        GeminiClassifier 초기화

        Args:
            api_key: Google Generative AI API 키 (제공되지 않으면 .env 파일에서 로드)
        """
        # .env 파일에서 환경 변수 로드
        load_dotenv()
        
        # API 키 우선순위: 1. 매개변수로 전달된 값, 2. 환경 변수
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError(
                "Gemini API 키를 찾을 수 없습니다. .env 파일에 GEMINI_API_KEY를 설정하거나 api_key 매개변수를 제공하세요."
            )

        # API 키로 Gemini 설정
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def classify_url(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        URL의 HTML 콘텐츠를 분석하여 불법 도박 사이트 여부를 판별

        Args:
            url: 분석할 URL
            html_content: 웹사이트의 HTML 콘텐츠

        Returns:
            {
                "url": str,
                "is_illegal": bool,
                "confidence": float (0.0-1.0),
                "reason": str,
                "detected_keywords": list,
                "error": str or None
            }
        """
        try:
            # HTML에서 텍스트만 추출
            cleaned_html = self._extract_text_from_html(html_content)

            # 추출된 텍스트 길이 제한 (Gemini API 입력 크기 제한)
            if len(cleaned_html) > 50000:
                cleaned_html = cleaned_html[:50000]

            prompt = self._build_prompt(url, cleaned_html)
            response = self.model.generate_content(prompt)

            # 응답 파싱
            response_text = response.text
            result = self._parse_response(response_text)

            return {
                "url": url,
                "is_illegal": result.get("is_illegal", False),
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", ""),
                "detected_keywords": result.get("detected_keywords", []),
                "error": None,
            }

        except Exception as e:
            return {
                "url": url,
                "is_illegal": False,
                "confidence": 0.0,
                "reason": "",
                "detected_keywords": [],
                "error": str(e),
            }

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        HTML에서 텍스트 콘텐츠만 추출
        script, style, meta 등 불필요한 태그 제거

        Args:
            html_content: 원본 HTML 콘텐츠

        Returns:
            정제된 텍스트 콘텐츠
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # script, style, meta, noscript 태그 제거
            for tag in soup.find_all(['script', 'style', 'meta', 'noscript', 'link', 'head']):
                tag.decompose()

            # 텍스트 추출
            text = soup.get_text(separator=' ', strip=True)

            # 연속된 공백을 단일 공백으로 정리
            text = re.sub(r'\s+', ' ', text)

            return text
        except Exception as e:
            # 파싱 실패 시 원본 반환 (안전성)
            return html_content

    def _build_prompt(self, url: str, text_content: str) -> str:
        """불법 도박 사이트 판별을 위한 프롬프트 작성"""

        prompt = f"""당신은 불법 온라인 도박 사이트를 탐지하는 전문가입니다.

다음 웹사이트의 정보를 분석하고, 이것이 불법 도박 사이트인지 판단하세요.

URL: {url}

웹사이트 콘텐츠:
{text_content}

판단 기준:
1. 베팅/도박 관련 키워드 (betting, casino, poker, slots, sports betting, 도박, 베팅, 카지노, 슬롯머신, 스포츠베팅 등)
2. 결제 수단 제공 (신용카드, 가상화폐, 송금, deposit, withdraw 등)
3. 로그인/회원가입 시스템 (login, signup, register, 회원가입, 로그인 등)
4. 불법성을 암시하는 언어 (은폐, 익명, 추적 불가, VPN, anonymous, hidden 등)
5. 지역 규제 회피 표현 (우회, bypass, offshore, 규제 회피 등)
6. 다양한 언어로 된 도박 관련 용어 (바카라, 더블업, 롤링, 마진, 핸디캡 등)

응답 형식 (JSON만 반환):
{{
  "is_illegal": true/false,
  "confidence": 0.0-1.0 (신뢰도),
  "reason": "판단 이유 (한두 문장)",
  "detected_keywords": ["탐지된 키워드1", "탐지된 키워드2"]
}}

정확하고 객관적으로 판단하세요. JSON만 반환하고 다른 텍스트는 포함하지 마세요."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Gemini API 응답을 파싱하여 구조화된 데이터로 변환"""

        try:
            # JSON 형식으로 응답 파싱
            # 응답에 마크다운 코드 블록이 있을 수 있으므로 처리
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                # 마크다운 코드 블록 제거
                cleaned_response = cleaned_response.split("```")[1]
                if cleaned_response.startswith("json"):
                    cleaned_response = cleaned_response[4:]
                cleaned_response = cleaned_response.strip()

            result = json.loads(cleaned_response)

            # 신뢰도 범위 확인
            confidence = result.get("confidence", 0.0)
            if not isinstance(confidence, (int, float)):
                confidence = 0.0
            result["confidence"] = max(0.0, min(1.0, confidence))

            return result

        except json.JSONDecodeError:
            # JSON 파싱 실패 시 기본값 반환
            return {
                "is_illegal": False,
                "confidence": 0.0,
                "reason": "응답 파싱 실패",
                "detected_keywords": [],
            }
