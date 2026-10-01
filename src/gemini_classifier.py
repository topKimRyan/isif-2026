import json
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from bs4 import BeautifulSoup
import re


class GeminiClassifier:
    """Classifies websites as illegal gambling sites using the Gemini API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GeminiClassifier.

        Args:
            api_key: Google Generative AI API key. If not provided, loaded from .env file.
        """
        # Load environment variables from .env
        load_dotenv()

        # Priority: 1. parameter value, 2. environment variable
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY in your .env file or pass it via the api_key parameter."
            )

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    def classify_url(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Analyzes the HTML content of a URL to determine whether it is an illegal gambling site.

        Args:
            url: The URL to analyze.
            html_content: The HTML content of the website.

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
            cleaned_html = self._extract_text_from_html(html_content)

            # Truncate to fit Gemini API input limits
            if len(cleaned_html) > 50000:
                cleaned_html = cleaned_html[:50000]

            prompt = self._build_prompt(url, cleaned_html)
            response = self.model.generate_content(prompt)

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
        Extracts plain text from HTML, removing script, style, meta, and other non-content tags.

        Args:
            html_content: Raw HTML content.

        Returns:
            Cleaned text content.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            for tag in soup.find_all(['script', 'style', 'meta', 'noscript', 'link', 'head']):
                tag.decompose()

            text = soup.get_text(separator=' ', strip=True)

            # Collapse consecutive whitespace
            text = re.sub(r'\s+', ' ', text)

            return text
        except Exception as e:
            # Return raw HTML as fallback if parsing fails
            return html_content

    def _build_prompt(self, url: str, text_content: str) -> str:
        """Builds the classification prompt for illegal gambling site detection."""

        prompt = f"""You are an expert at detecting illegal online gambling websites.

Analyze the following website information and determine whether it is an illegal gambling site.

URL: {url}

Website content:
{text_content}

Detection criteria:
1. Betting/gambling-related keywords (betting, casino, poker, slots, sports betting, baccarat, etc.)
2. Payment methods offered (credit card, cryptocurrency, wire transfer, deposit, withdraw, etc.)
3. Login/registration system (login, signup, register, etc.)
4. Language suggesting illegality (anonymous, untraceable, VPN, hidden, etc.)
5. Regional regulation evasion (bypass, offshore, etc.)
6. Gambling terms in any language

Response format (return JSON only):
{{
  "is_illegal": true/false,
  "confidence": 0.0-1.0,
  "reason": "Reason for the decision (one or two sentences)",
  "detected_keywords": ["keyword1", "keyword2"]
}}

Language requirements:
- Write the "reason" field in English only, even if the website content is in another language.
- In "detected_keywords", write English keywords as-is. For non-English keywords, keep the original term and add an English translation in parentheses, e.g. "바카라 (baccarat)".

Be accurate and objective. Return only the JSON with no additional text."""

        return prompt

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parses the Gemini API response into structured data."""

        try:
            # Handle potential markdown code block wrapping
            cleaned_response = response_text.strip()
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response.split("```")[1]
                if cleaned_response.startswith("json"):
                    cleaned_response = cleaned_response[4:]
                cleaned_response = cleaned_response.strip()

            result = json.loads(cleaned_response)

        except json.JSONDecodeError as e:
            # Raise so classify_url reports an error instead of a silent "not illegal" verdict
            raise ValueError(f"Failed to parse Gemini response as JSON: {response_text[:200]!r}") from e

        if not isinstance(result, dict) or "is_illegal" not in result:
            raise ValueError(f"Gemini response is missing 'is_illegal': {response_text[:200]!r}")

        is_illegal = result["is_illegal"]
        if isinstance(is_illegal, str):
            is_illegal = is_illegal.strip().lower() == "true"
        result["is_illegal"] = bool(is_illegal)

        try:
            confidence = float(result.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        result["confidence"] = max(0.0, min(1.0, confidence))

        keywords = result.get("detected_keywords")
        result["detected_keywords"] = [str(k) for k in keywords] if isinstance(keywords, list) else []

        return result
