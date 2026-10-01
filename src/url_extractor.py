from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


class URLExtractor:
    def __init__(self, remove_tracking_params: bool = True):
        self.remove_tracking_params = remove_tracking_params
        self.tracking_params = [
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'gclid', 'fbclid', 'ref', '_ga', '_gac', 'mc_cid', 'mc_eid'
        ]

    def clean_url(self, url: str) -> str:
        """Removes tracking parameters from a URL when enabled in settings."""
        if self.remove_tracking_params:
            return self._clean_tracking_params(url)
        return url

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
        except ValueError:
            return url
