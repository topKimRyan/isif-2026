# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **illegal gambling site detection system MVP** with three parts:
- **Crawler** (`main.py`, `src/`): searches keywords on Google, visits the results, classifies each page with Gemini, and stores the illegal gambling sites
- **Report system** (`report_page/`): lets users submit a suspicious URL, which a background worker analyzes, screenshots, and logs
- **Dashboard** (`docs/`): a read-only view of detected sites from Supabase

## Development Setup

### Requirements
- Python 3.12 or higher
- Chrome/Chromium browser (for Selenium-based searching)
- Google Generative AI API key (for Gemini classification)
- PostgreSQL database (Supabase recommended)
- **Note**: On Windows, ensure Chrome/Chromium is installed in default paths or PATH

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Setup environment variables
cp env_template.txt .env
# Edit .env file with your actual API keys and database credentials

# Verify installation
python -c "import selenium; import bs4; print('Dependencies installed successfully')"
```

### Environment Variables (.env)
Create a `.env` file in the project root (use `env_template.txt` as template):
```bash
# Supabase PostgreSQL connection
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_supabase_host.supabase.co
DB_PORT=5432
DB_NAME=postgres

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
# GEMINI_MODEL=gemini-2.5-flash   # optional override

# Supabase API access for the report worker
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_KEY=your_supabase_service_role_key
```

**Important:** Never commit the `.env` file to version control!

### Running the Crawler
```bash
# Basic execution
python main.py

# With explicit venv activation (cross-platform)
source .venv/bin/activate && python main.py  # Linux/Mac
.venv\Scripts\activate && python main.py      # Windows
```

### Running the Report Worker
The report page (`report_page/`) is a static site; the worker processes reports in the background:
```bash
cd report_page/server
python worker.py
```

### Running the Dashboard
```bash
python -m http.server 3001 --directory docs
```

### Deployment (Cloudflare Workers)
The report service and dashboard are deployed together as one static site:
- Build command: `bash scripts/build_site.sh`, deploy command: `npx wrangler deploy` (uploads `dist/` per `wrangler.jsonc`; `/` = report service, `/dashboard/` = dashboard)
- Live site: https://isif-2026.2369-ryan.workers.dev
- The build copies only browser files; `report_page/server/` is not published
- The worker (`report_page/server/worker.py`) needs Python + Chrome and is **not** hosted on Cloudflare; run it on a PC or server
- Supabase access rules for the public anon key live in `supabase/security.sql` (run it in the Supabase SQL editor)
- The report pages cannot read `report_requests` directly. They call database functions (`create_report`, `get_report`, `cancel_report`, `update_report_details`, `confirm_report`) with the report id plus the secret token from `create_report`, and poll `get_report` instead of using Realtime. New table access for the browser should go through a function the same way; only the worker (service role) touches the table directly

### Tests
There is no automated test suite yet.

## Common Development Commands

```bash
# Verify dependencies are installed correctly
python -c "import selenium; import bs4; from google import genai; print('All dependencies OK')"

# Run the crawler with default settings
python main.py

# Check current crawl results and statistics
python -c "from src.json_storage import JSONStorage; s = JSONStorage(); print(s.get_stats())"

# List all keyword combinations that will be searched
python -c "from src.keyword_manager import KeywordManager; km = KeywordManager(); print(km.generate_combinations())"

# Import data from results.json into the database
python -c "from src.database import import_from_json; import_from_json('results.json')"
```

### Configuration
The crawler is controlled via `settings.json`:
- `search_engine`: Which search engine to use (currently only "google" is implemented)
- `headless_mode`: Run browser in headless mode (true/false)
- `delay_between_searches`: Seconds to wait between search requests
- `max_links_per_search`: Maximum number of result links to visit per search
- `output_file`: Path to store collected URLs (default: "results.json")
- `remove_tracking_params`: Strip tracking parameters from visited URLs (true/false)
- `use_gemini_classifier`: Enable Gemini-based URL classification (true/false)
- `combine_keywords`: Also search every 2-keyword pair (true/false). With N keywords this adds N·(N−1)/2 searches, so keep it off for long keyword lists
- `captcha_wait_seconds`: When Google shows a CAPTCHA, how long to wait for you to solve it by hand in the visible Chrome window (requires `headless_mode: false`); the keyword is skipped if it isn't solved in time
- `page_load_timeout`: Seconds to wait for a site to load before stopping it and using what has loaded (sites that never finish loading would otherwise block the crawler)
- `expand_keywords`: After searching `keywords.json` (round 0), search keywords that Gemini detected on the illegal sites found, round after round (true/false; needs the Gemini classifier)
- `max_expansion_rounds`: How many expansion rounds to run after round 0; expansion also stops early when a round yields no new keyword
- `max_new_keywords_per_round`: Most keywords searched in one expansion round (best-ranked first)
- `min_keyword_site_count`: A detected keyword must appear on at least this many different illegal sites in the round to be searched
- `min_expansion_confidence`: Only sites classified illegal with at least this Gemini confidence contribute keywords
- `expansion_log_file`: JSON log of every run's rounds (keywords, the sites they came from, illegal sites found per keyword); not in git. Empty to disable

**Note:** API keys and database credentials are managed via the `.env` file (not `settings.json`).

## Key Development Notes

### Dependencies
Gemini classification uses the `google-genai` SDK (`from google import genai`). The older `google-generativeai` package is no longer supported by Google and is not used.

### File Structure Overview
```
illicit-gambling-detector/
├── main.py                    # Crawler entry point
├── settings.json              # Crawler configuration
├── keywords.json              # Search keywords
├── .env                       # API keys and DB credentials (not in git)
├── env_template.txt           # Template for .env
├── src/
│   ├── crawler.py             # Main orchestrator
│   ├── keyword_manager.py     # Keyword loading and combinations
│   ├── keyword_expander.py    # Picks next-round keywords from detected_keywords
│   ├── search_engine.py       # Google search and page fetching via Selenium
│   ├── url_extractor.py       # Tracking-parameter removal for URLs
│   ├── url_safety.py          # Blocks non-public URLs (file://, localhost, private IPs)
│   ├── gemini_classifier.py   # AI-based classification
│   ├── json_storage.py        # JSON file persistence
│   └── database.py            # PostgreSQL integration
├── report_page/               # Public report site (static HTML/JS) + server/ worker
├── docs/                      # Read-only dashboard of detected sites
└── results.json               # Output file with crawled results (not in git)
```

### Module Dependencies
- `crawler.py` depends on all other src modules
- `search_engine.py` requires Chrome; there is no non-browser fallback
- `gemini_classifier.py` requires `GEMINI_API_KEY` in `.env` (optional but recommended)
- `database.py` requires PostgreSQL connection credentials in `.env`
- `report_page/server/` handlers import `gemini_classifier`, `search_engine`, and `url_safety` from `src/`

### Windows-Specific Notes
- Use `python` instead of `python3` on Windows
- Virtual environment activation: `.venv\Scripts\activate` (not `source .venv/bin/activate`)
- Chrome/Chromium: webdriver-manager handles driver installation automatically, but ensure Chrome is in PATH or standard install locations

## Architecture

The crawler follows a modular design with clear separation of concerns:

**Core Components:**
- `src/keyword_manager.py` - Loads keywords from JSON and generates 2-keyword combinations
- `src/keyword_expander.py` - Ranks the detected keywords of a round's illegal sites and picks the next round's search keywords
- `src/search_engine.py` - Searches Google with Selenium, collects result links, and visits each one
- `src/url_extractor.py` - Removes tracking parameters from URLs
- `src/json_storage.py` - Manages JSON file storage with timestamps and metadata
- `src/gemini_classifier.py` - Analyzes pages using Google's Gemini API to classify illegal gambling sites
- `src/database.py` - PostgreSQL database integration for persistent storage (Supabase)
- `src/crawler.py` - Main orchestrator that coordinates all components

**Configuration Files:**
- `keywords.json` - Contains the list of gambling-related keywords to search
- `settings.json` - Controls headless mode, delays, and output settings
- `.env` - Contains API keys and database credentials (not committed to git)
- `env_template.txt` - Template for creating `.env` file
- `results.json` - Output file containing collected URLs with metadata

**Data Flow:**
1. KeywordManager loads keywords and generates combinations
2. SearchEngine searches Google, collects result links (skipping Google, news, and reference hosts), and visits each link
3. URLExtractor removes tracking parameters from visited URLs; already-known URLs are skipped
4. GeminiClassifier analyzes each page (optional, if enabled in settings)
5. JSONStorage saves the sites classified as illegal, with timestamps (UTC) and classification metadata
6. Keyword expansion (if `expand_keywords`): KeywordExpander takes the `detected_keywords` of the round's illegal sites, keeps the original term of translated keywords (`바카라 (baccarat)` → `바카라`), drops already-searched, overly generic (`casino`, `토토`, …), domain/URL, and too-long keywords, keeps those seen on at least `min_keyword_site_count` sites, ranks them by site count then summed confidence, and steps 2–5 run again with them as the next round. Each saved entry records its `search_round`
7. A failed search (e.g. Google CAPTCHA) skips that keyword; the browser is always closed at the end

**Gemini Classification Integration:**
When enabled (`use_gemini_classifier: true`), the crawler:
- Sends the URL and the page's visible text to Gemini (default `gemini-2.5-flash`, override with `GEMINI_MODEL`)
- Requests JSON output; the reason is always written in English, and non-English keywords include an English translation
- Treats unparseable responses as errors (not as "not illegal")
- Handles missing/invalid API keys gracefully (logs warning, continues without classification)

**Report System (`report_page/`):**
- Users submit a URL; the worker (Supabase Realtime) fetches the page, classifies it, takes a screenshot, and logs the final report to `gambling_urls` with `keyword_used = 'manual report'`
- Report URLs are checked with `url_safety.is_public_http_url` before and after loading, so the worker never opens local files or internal addresses
- AI output is HTML-escaped before rendering on the report pages and the dashboard

**Database Integration:**
The system supports persistent storage in PostgreSQL (Supabase):
- `src/database.py` provides `DatabaseManager` class for database operations
- Table schema includes URL, keywords, timestamps, Gemini classification results, and screenshot URL
- Supports bulk import from `results.json` via the module-level `import_from_json()` function; records that fail or have no Gemini verdict are kept in the JSON file
- Crawler rows are updated in place by URL; manual reports always insert a new row
- Indexes on URL, is_illegal, collected_at, and detected_keywords (JSONB) for fast queries
- Timestamps are stored in UTC (`TIMESTAMP WITH TIME ZONE`); the dashboard shows them in the viewer's local time

**Important Implementation Notes:**
- The search engine includes bot detection avoidance (user-agent rotation, random delays, automation flags disabled)
- All results are stored with timestamp and source keyword for traceability
