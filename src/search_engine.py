import time
import random
import os
from urllib.parse import parse_qs, quote_plus, urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

try:
    from .url_safety import is_public_http_url
except ImportError:  # Imported as a top-level module by report_page/server handlers
    from url_safety import is_public_http_url


class SearchEngine:
    def __init__(self, headless: bool = True, captcha_wait_seconds: int = 300):
        self.headless = headless
        self.captcha_wait_seconds = captcha_wait_seconds
        self.driver = None

        # News/reference site domains to exclude from results (matched against the hostname,
        # including subdomains). Hosts starting with "news." are excluded as well.
        self.excluded_domains = [
            # Korean news portals and outlets
            'naver.com', 'daum.net', 'joins.com', 'chosun.com',
            'donga.com', 'khan.co.kr', 'hankyung.com', 'mk.co.kr',
            'yna.co.kr', 'newsis.com', 'ytn.co.kr', 'sbs.co.kr',
            'kbs.co.kr', 'mbc.co.kr', 'jtbc.co.kr', 'mt.co.kr',
            'sedaily.com', 'seoul.co.kr', 'hani.co.kr', 'kmib.co.kr',
            'segye.com', 'fnnews.com', 'newsway.co.kr', 'journalist.or.kr',
            # International news outlets
            'bbc.com', 'bbc.co.uk', 'cnn.com', 'reuters.com', 'apnews.com', 'nytimes.com',
            'theguardian.com', 'washingtonpost.com', 'wsj.com', 'ft.com',
            'bloomberg.com', 'forbes.com', 'cnbc.com', 'usatoday.com',
            'npr.org', 'aljazeera.com', 'independent.co.uk', 'telegraph.co.uk',
            'espn.com', 'nikkei.com', 'scmp.com',
            # Reference, video, and community sites
            'wikipedia.org', 'reddit.com', 'youtube.com', 'youtu.be'
        ]

    def setup_driver(self):
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Randomize User-Agent to reduce bot detection
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

        # Install and initialize ChromeDriver (with webdriver-manager bug workaround)
        try:
            installed_path = ChromeDriverManager().install()

            # BUG WORKAROUND: webdriver-manager may return a path to a notice file
            # (e.g. .../chromedriver-win32/THIRD_PARTY_NOTICES.chromedriver) instead of the binary,
            # so look for the driver binary next to it, then one directory up.
            driver_name = "chromedriver.exe" if os.name == "nt" else "chromedriver"
            candidates = [
                os.path.join(os.path.dirname(installed_path), driver_name),
                os.path.join(os.path.dirname(os.path.dirname(installed_path)), driver_name),
            ]
            driver_path = next((path for path in candidates if os.path.exists(path)), installed_path)

            service = Service(driver_path)
            print("ChromeDriver is set up automatically via webdriver-manager.")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

        except Exception as e:
            print(f"FATAL: Failed to initialize ChromeDriver: {e}")
            raise

        # Bypass automation detection
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def take_screenshot_from_url(self, url: str, path: str):
        """
        Takes a screenshot of a single URL using Selenium and saves it to a path.
        Ensures driver is set up and closes it afterwards if it was newly opened.
        """
        initial_driver_state = self.driver is not None
        if not initial_driver_state:
            self.setup_driver()

        try:
            if not is_public_http_url(url):
                raise ValueError(f"Blocked non-public URL: {url}")
            self.driver.get(url)
            time.sleep(5)  # Allow time for the page to load fully
            # Re-check after redirects so a public URL can't bounce to an internal address
            if not is_public_http_url(self.driver.current_url):
                raise ValueError(f"Blocked redirect to non-public URL: {self.driver.current_url}")
            self.driver.save_screenshot(path)
            print(f"  ✅ Screenshot saved: {path}")
        except Exception as e:
            print(f"  ❌ Failed to take screenshot {url}: {e}")
            raise  # Re-raise the exception to be handled by the caller
        finally:
            if not initial_driver_state and self.driver:
                self.close()

    def get_html_content_from_url(self, url: str) -> str:
        """
        Fetches HTML content for a single URL using Selenium.
        Ensures driver is set up and closes it afterwards if it was newly opened.
        """
        initial_driver_state = self.driver is not None
        if not initial_driver_state:
            self.setup_driver()

        try:
            if not is_public_http_url(url):
                print(f"  ❌ Blocked non-public URL: {url}")
                return ""
            self.driver.get(url)
            time.sleep(5) # Give page time to load and execute JS
            # Re-check after redirects so a public URL can't bounce to an internal address
            if not is_public_http_url(self.driver.current_url):
                print(f"  ❌ Blocked redirect to non-public URL: {self.driver.current_url}")
                return ""
            html_content = self.driver.page_source
            return html_content
        except Exception as e:
            print(f"  ❌ Failed to fetch HTML via Selenium {url}: {e}")
            return ""
        finally:
            # Only close driver if it was newly opened by this method
            if not initial_driver_state and self.driver:
                self.close()

    def search_google(self, keyword: str) -> str:
        # Initialize driver if not already running
        if not self.driver:
            self.setup_driver()

        # Validate session — reinitialize if connection was lost
        try:
            _ = self.driver.current_url
        except Exception as e:
            print(f"  ⚠️ Browser session lost, reinitializing driver... ({e})")
            self.driver = None
            self.setup_driver()

        search_url = f"https://www.google.com/search?q={quote_plus(keyword)}"
        self.driver.get(search_url)

        # Random delay to avoid bot detection
        random_delay = random.uniform(2, 4)
        time.sleep(random_delay)

        if self._is_captcha_page():
            self._wait_for_manual_captcha()

        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
            )
        except TimeoutException:
            if self._is_captcha_page():
                self._wait_for_manual_captcha()
            else:
                raise

        time.sleep(random.uniform(1, 2))

        return self.driver.page_source

    def _is_captcha_page(self) -> bool:
        return "/sorry/" in self.driver.current_url

    def _wait_for_manual_captcha(self):
        """Pauses until the user solves Google's CAPTCHA in the visible browser window."""
        if self.headless:
            raise RuntimeError(
                "Google blocked the search with a CAPTCHA. Set headless_mode to false to solve it manually."
            )

        print(f"\a  🧩 Google CAPTCHA detected. Solve it in the Chrome window "
              f"(waiting up to {self.captcha_wait_seconds}s)...")
        try:
            WebDriverWait(self.driver, self.captcha_wait_seconds, poll_frequency=2).until(
                lambda driver: not self._is_captcha_page()
                and driver.find_elements(By.CSS_SELECTOR, "div#search")
            )
        except TimeoutException:
            raise RuntimeError("CAPTCHA was not solved in time; skipping this keyword")
        print("  ✅ CAPTCHA solved, continuing")

    def visit_search_result_links(self, max_links: int = 10) -> list:
        """
        Collects links from the search results page, then visits each one and collects HTML.

        Args:
            max_links: maximum number of pages to collect (excluded sites don't count)

        Returns:
            list of (url, html_content) tuples
        """
        results = []

        try:
            # Read all hrefs up front: element references go stale once the browser navigates away
            rso_element = self.driver.find_element(By.ID, "rso")
            hrefs = [a.get_attribute("href") for a in rso_element.find_elements(By.TAG_NAME, "a")]
        except Exception as e:
            print(f"  ❌ Error finding search result links: {e}")
            return results

        links_to_visit = []
        seen = set()
        for href in hrefs:
            if not href or not href.startswith(("http://", "https://")):
                continue
            target, is_redirect = self._resolve_google_link(href)
            if not target:
                continue
            # Skip repeated links to the same page (e.g. title link + sitelinks)
            key = target.split("#")[0].rstrip("/")
            if key in seen:
                continue
            seen.add(key)
            # Opaque Google redirects (/goto) can only be checked after the browser follows them
            if not is_redirect and self._is_excluded_host(urlparse(target).hostname):
                print(f"    ⏭️ Skipping excluded site: {target}")
                continue
            links_to_visit.append(target)

        print(f"  📋 Found {len(links_to_visit)} candidate links, collecting up to {max_links}")

        collected_urls = set()
        for i, target_url in enumerate(links_to_visit, 1):
            if len(results) >= max_links:
                break
            try:
                print(f"    [{i}/{len(links_to_visit)}] 🔗 Visiting: {target_url[:120]}")
                self.driver.get(target_url)
                time.sleep(random.uniform(2, 3))

                current_url = self.driver.current_url
                # Check the final address: redirects reveal the real site only after loading
                if self._is_excluded_host(urlparse(current_url).hostname):
                    print(f"    ⏭️ Skipping excluded site: {current_url}")
                    continue
                if current_url in collected_urls:
                    print(f"    ⏭️ Already collected: {current_url}")
                    continue
                collected_urls.add(current_url)

                html_content = self.driver.page_source

                results.append((current_url, html_content))
                print(f"    ✅ HTML collected: {current_url}")
            except Exception as e:
                print(f"    ❌ Error visiting link {target_url[:120]}: {e}")

        return results

    def _resolve_google_link(self, href: str) -> tuple:
        """
        Unwraps Google redirect links in search results.

        Returns (url, is_redirect):
        - /url?q=<real url>  -> (real url, False)
        - /goto?url=<token>  -> (href, True): the token is opaque, so the browser must follow it
        - other Google pages -> (None, False)
        - anything else      -> (href, False)
        """
        parsed = urlparse(href)
        hostname = (parsed.hostname or "").lower()
        if not any(part == "google" for part in hostname.split(".")):
            return href, False

        if parsed.path == "/url":
            params = parse_qs(parsed.query)
            for name in ("q", "url"):
                value = params.get(name, [""])[0]
                if value.startswith(("http://", "https://")):
                    return value, False
            return None, False

        if parsed.path == "/goto":
            return href, True

        return None, False

    def _is_excluded_host(self, hostname: str) -> bool:
        """Returns True for search engine, news, and reference hosts that should not be crawled."""
        if not hostname:
            return True
        hostname = hostname.lower()
        if hostname.startswith("news."):
            return True
        # Google's own pages (google.com, google.co.kr, support.google.com, ...)
        if any(part == "google" for part in hostname.split(".")) or hostname.endswith("googleusercontent.com"):
            return True
        return any(hostname == domain or hostname.endswith("." + domain) for domain in self.excluded_domains)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
