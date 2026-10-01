import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

try:
    from .url_safety import is_public_http_url
except ImportError:  # Imported as a top-level module by report_page/server handlers
    from url_safety import is_public_http_url


class SearchEngine:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

        # List of news site domains to exclude from results
        self.news_domains = [
            'news.', 'naver.com', 'daum.net', 'joins.com', 'chosun.com',
            'donga.com', 'khan.co.kr', 'hankyung.com', 'mk.co.kr',
            'yna.co.kr', 'newsis.com', 'ytn.co.kr', 'sbs.co.kr',
            'kbs.co.kr', 'mbc.co.kr', 'jtbc.co.kr', 'mt.co.kr',
            'sedaily.com', 'seoul.co.kr', 'hani.co.kr', 'kmib.co.kr',
            'segye.com', 'fnnews.com', 'newsway.co.kr', 'journalist.or.kr',
            'youtube.com', 'youtu.be'
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
            buggy_path = ChromeDriverManager().install()
            print(f"DEBUG: Path from webdriver-manager: {buggy_path}")

            # BUG WORKAROUND: webdriver-manager might return a path to a notice file.
            # We construct the correct path to 'chromedriver.exe'.
            driver_dir = os.path.dirname(buggy_path)
            driver_path = os.path.join(driver_dir, "chromedriver.exe")

            print(f"DEBUG: Constructed driver path: {driver_path}")
            print(f"DEBUG: Constructed path exists: {os.path.exists(driver_path)}")

            if not os.path.exists(driver_path):
                 # If the path is still wrong, try one directory up, as the folder structure might be nested.
                 # e.g., .../chromedriver-win32/chromedriver.exe
                 # The buggy path might be .../chromedriver-win32/THIRD_PARTY_NOTICES.chromedriver
                 # so dirname is correct. Let's check parent dir just in case.
                 driver_dir = os.path.dirname(os.path.dirname(buggy_path))
                 driver_path = os.path.join(driver_dir, "chromedriver.exe")
                 print(f"DEBUG: Trying parent directory. New path: {driver_path}")
                 print(f"DEBUG: Parent directory path exists: {os.path.exists(driver_path)}")


            if not os.path.exists(driver_path):
                print("ERROR: Could not find chromedriver.exe even with workarounds. Using original path.")
                driver_path = buggy_path # Fallback to the original path

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

        search_url = f"https://www.google.com/search?q={keyword}"
        self.driver.get(search_url)

        # Random delay to avoid bot detection
        random_delay = random.uniform(2, 4)
        time.sleep(random_delay)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
        )

        time.sleep(random.uniform(1, 2))

        return self.driver.page_source

    def visit_search_result_links(self, max_links: int = 10) -> list:
        """
        Finds links in the search results page, visits each one, and collects HTML.

        Args:
            max_links: maximum number of links to visit

        Returns:
            list of (url, html_content) tuples
        """
        results = []

        try:
            # Find link elements within the rso (search results) area
            rso_element = self.driver.find_element(By.ID, "rso")
            link_elements = rso_element.find_elements(By.TAG_NAME, "a")

            # Filter for valid links (must have href starting with http)
            valid_links = []
            for link_element in link_elements:
                href = link_element.get_attribute("href")
                if href and (href.startswith("http://") or href.startswith("https://")):
                    # Exclude Google internal links and data: URLs
                    if "google.com" not in href and not href.startswith("data:"):
                        # Exclude news sites
                        is_news_site = any(news_domain in href for news_domain in self.news_domains)
                        print("#####", href, is_news_site)
                        if not is_news_site:
                            valid_links.append(link_element)
                        else:
                            print(f"    ⏭️ Skipping news site: {href}")

            links_to_visit = valid_links[:max_links]
            print(f"  📋 Found {len(valid_links)} valid links, visiting {len(links_to_visit)}")

            for i, link_element in enumerate(links_to_visit, 1):
                try:
                    # Save URL before clicking (becomes inaccessible after navigation)
                    target_url = link_element.get_attribute("href")
                    print(f"    [{i}/{len(links_to_visit)}] 🔗 Clicking: {target_url}")

                    link_element.click()

                    time.sleep(random.uniform(2, 3))

                    current_url = self.driver.current_url
                    html_content = self.driver.page_source

                    results.append((current_url, html_content))
                    print(f"    ✅ HTML collected: {current_url}")

                    is_last_link = (i == len(links_to_visit))
                    self.driver.back()

                    time.sleep(random.uniform(1, 2))
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "rso"))
                    )

                    if not is_last_link:
                        # Re-fetch links since the page reloaded
                        rso_element = self.driver.find_element(By.ID, "rso")
                        link_elements = rso_element.find_elements(By.TAG_NAME, "a")

                        valid_links = []
                        for link_element in link_elements:
                            href = link_element.get_attribute("href")
                            if href and (href.startswith("http://") or href.startswith("https://")):
                                if "google.com" not in href and not href.startswith("data:"):
                                    is_news_site = any(news_domain in href for news_domain in self.news_domains)
                                    if not is_news_site:
                                        valid_links.append(link_element)

                        links_to_visit = valid_links[:max_links]

                except Exception as e:
                    print(f"    ❌ Error visiting link: {e}")
                    try:
                        self.driver.back()
                        time.sleep(1)
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "rso"))
                        )
                    except:
                        print(f"    ⚠️ Failed to return to search results page")
                        pass
                    continue

        except Exception as e:
            print(f"  ❌ Error finding search result links: {e}")

        return results

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
