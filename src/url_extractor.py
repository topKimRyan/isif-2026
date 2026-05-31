import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import List, Set


class URLExtractor:
    def __init__(self, remove_tracking_params: bool = True):
        self.remove_tracking_params = remove_tracking_params
        self.tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'gclid', 'fbclid', 'ref', '_ga', '_gac', 'mc_cid', 'mc_eid'
        ]

    def extract_urls_from_html(self, html_content: str) -> List[str]:
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = set()

        # Extract from the main search results area (id="rso") only
        rso_element = soup.find(id='rso')

        # Fall back to full page if rso area is not found
        search_area = rso_element if rso_element else soup

        for link in search_area.find_all('a', href=True):
            url = link['href']

            # Unwrap Google redirect URLs to get the actual destination
            url = self._extract_real_url_from_google(url)

            if self._is_valid_url(url):
                if self.remove_tracking_params:
                    url = self._clean_tracking_params(url)
                urls.add(url)

        return list(urls)

    def _extract_real_url_from_google(self, url: str) -> str:
        """Extracts the real URL from a Google redirect (e.g. /url?q=<real_url>&...)."""
        if url.startswith('/url'):
            try:
                parsed = urlparse(url)
                query_params = parse_qs(parsed.query)
                if 'q' in query_params:
                    return query_params['q'][0]
            except:
                pass
        return url

    def _is_valid_url(self, url: str) -> bool:
        if not url or url.startswith('#') or url.startswith('javascript:'):
            return False

        if url.startswith('mailto:') or url.startswith('tel:'):
            return False

        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            return False

        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and parsed.scheme in ('http', 'https')
        except:
            return False

    def _clean_tracking_params(self, url: str) -> str:
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            cleaned_params = {k: v for k, v in query_params.items()
                            if k not in self.tracking_params}

            new_query = urlencode(cleaned_params, doseq=True)
            cleaned_url = urlunparse((
                parsed.scheme, parsed.netloc, parsed.path,
                parsed.params, new_query, parsed.fragment
            ))

            return cleaned_url
        except:
            return url

    def remove_duplicates(self, urls: List[str]) -> List[str]:
        return list(set(urls))
