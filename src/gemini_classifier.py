import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from bs4 import BeautifulSoup
import re


class GeminiClassifier:
    """Classifies websites as illegal gambling sites using the Gemini API."""

    # operator = runs illegal gambling, promotion = advertises/steers to it (both count as illegal)
    CATEGORIES = ("operator", "promotion", "informational", "none")
    ILLEGAL_CATEGORIES = ("operator", "promotion")

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GeminiClassifier.

        Args:
            api_key: Google Generative AI API key. If not provided, loaded from .env file
                (GEMINI_API_KEYS, a comma-separated list tried in order, plus GEMINI_API_KEY).
        """
        # Load environment variables from .env
        load_dotenv()

        # Priority: 1. parameter value, 2. environment variables
        if api_key:
            keys = [api_key]
        else:
            keys = [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",")]
            keys.append((os.getenv("GEMINI_API_KEY") or "").strip())
        self.api_keys = list(dict.fromkeys(k for k in keys if k))

        if not self.api_keys:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY (or GEMINI_API_KEYS) in your .env file or pass it via the api_key parameter."
            )

        self.clients = [genai.Client(api_key=k) for k in self.api_keys]
        self.key_index = 0
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    @staticmethod
    def _is_key_error(error: errors.APIError) -> bool:
        """True when the failure belongs to the API key (quota, invalid, or no permission)."""
        if error.code in (401, 403, 429):
            return True
        return error.code == 400 and "api key" in str(error).lower()

    def _generate_json(self, prompt: str) -> str:
        """
        Sends a prompt that asks for JSON and returns the response text.

        When a key runs out of quota or is rejected, the next key is tried; the key that
        worked is kept for later calls, so a recovered key is reached again in turn.
        """
        last_error = None
        for _ in range(len(self.clients)):
            try:
                response = self.clients[self.key_index].models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    # Ask for raw JSON so the response can be parsed reliably
                    config=types.GenerateContentConfig(response_mime_type="application/json"),
                )
            except errors.APIError as e:
                if not self._is_key_error(e) or len(self.clients) == 1:
                    raise
                last_error = e
                print(f"  🔑 Gemini key #{self.key_index + 1} failed ({e.code} {e.status}); switching to the next key")
                self.key_index = (self.key_index + 1) % len(self.clients)
                continue

            if not response.text:
                raise ValueError("Gemini returned an empty response (it may have been blocked)")
            return response.text

        raise RuntimeError(f"All {len(self.clients)} Gemini API keys failed; last error: {last_error}")

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
                "category": "operator" | "promotion" | "informational" | "none" | None,
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
            result = self._parse_response(self._generate_json(prompt))

            return {
                "url": url,
                "is_illegal": result.get("is_illegal", False),
                "category": result.get("category"),
                "confidence": result.get("confidence", 0.0),
                "reason": result.get("reason", ""),
                "detected_keywords": result.get("detected_keywords", []),
                "error": None,
            }

        except Exception as e:
            return {
                "url": url,
                "is_illegal": False,
                "category": None,
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

        prompt = f"""You are an expert at detecting illegal online gambling websites and the pages that promote them.

Analyze the following website information and classify it into exactly one category.

URL: {url}

Website content:
{text_content}

Categories:
- "operator": the site itself runs illegal gambling (betting, casino, poker, slots, sports betting, baccarat, etc.) with deposits/withdrawals, login/registration, or play.
- "promotion": the page does not run gambling itself but advertises or steers visitors to illegal gambling sites. Examples: scam-verification / "eat-and-run" verification (먹튀검증) pages, "safe playground" (안전놀이터) or recommended-site lists, affiliate/referral pages, bonus/promo-code pages, and mirror/link-collection pages. This also applies to user-uploaded spam documents on hosting platforms (e.g. Scribd, blogs, forums) that exist to promote such sites.
- "informational": neutral or protective content about gambling that does not promote any gambling site. Examples: news, addiction prevention or counseling, legal or regulatory explanations, academic or encyclopedic articles.
- "none": unrelated to gambling.

Signals for operator/promotion: gambling keywords in any language, payment methods (deposit, withdraw, crypto), login/registration, language suggesting illegality (anonymous, untraceable, VPN, hidden), regional regulation evasion (bypass, offshore), and recommendation or verification claims about gambling sites. Mentioning gambling alone is not enough: judge whether the page runs or promotes gambling sites.

Response format (return JSON only):
{{
  "category": "operator" | "promotion" | "informational" | "none",
  "is_illegal": true if category is "operator" or "promotion", otherwise false,
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
        is_illegal = bool(is_illegal)

        # The category decides the verdict when it is valid; otherwise keep the model's boolean
        category = str(result.get("category") or "").strip().lower()
        if category in self.CATEGORIES:
            is_illegal = category in self.ILLEGAL_CATEGORIES
        else:
            category = None if is_illegal else "none"
        result["is_illegal"] = is_illegal
        result["category"] = category

        try:
            confidence = float(result.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        result["confidence"] = max(0.0, min(1.0, confidence))

        keywords = result.get("detected_keywords")
        result["detected_keywords"] = [str(k) for k in keywords] if isinstance(keywords, list) else []

        return result

    def review_keywords(self, candidates: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Asks Gemini whether each candidate is a good search query for finding more illegal
        gambling sites, so keyword expansion does not drift away from gambling.

        Args:
            candidates: [{"keyword": str, "site_count": int}, ...]

        Returns:
            {keyword: {"approved": bool, "reason": str}} for every candidate. Keywords the
            response leaves out are rejected. Raises on API or parsing errors.
        """
        if not candidates:
            return {}

        listing = "\n".join(
            f"- {c['keyword']} (seen on {c.get('site_count', 1)} illegal gambling sites)" for c in candidates
        )
        prompt = f"""You help a research crawler that finds illegal online gambling sites by searching Google.

The keywords below were detected on pages already classified as illegal gambling sites or pages that promote them. Decide for each one whether searching it on Google (in English) is likely to surface MORE illegal gambling sites or their promotion pages.

Approve a keyword when it is specific to illegal or unlicensed gambling, for example: terms about bypassing regulation or self-exclusion, no-KYC or anonymous play, offshore operators, scam-verification ("eat-and-run") or "safe playground" promotion, gambling slang, or names of illegal gambling site types.

Reject a keyword when it is:
- too generic to find illegal sites (e.g. "casino", "slots", "bonus", "sports")
- the name of a licensed operator, regulator, payment provider, or other legitimate brand
- unrelated to gambling, a person's name, or something that is not a search phrase
- not in English

Keywords:
{listing}

Return JSON only:
{{"keywords": [{{"keyword": "<exactly as given>", "approved": true or false, "reason": "<short English reason>"}}]}}"""

        response_text = self._generate_json(prompt).strip()
        if response_text.startswith("```"):
            response_text = response_text.strip("`").removeprefix("json").strip()
        try:
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse keyword review as JSON: {response_text[:200]!r}") from e

        items = data.get("keywords", []) if isinstance(data, dict) else []
        verdicts = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            keyword = str(item.get("keyword", "")).strip().lower()
            approved = item.get("approved")
            if isinstance(approved, str):
                approved = approved.strip().lower() == "true"
            verdicts[keyword] = {"approved": bool(approved), "reason": str(item.get("reason", ""))}

        return {
            c["keyword"]: verdicts.get(c["keyword"], {"approved": False, "reason": "Not returned by the keyword review"})
            for c in candidates
        }
