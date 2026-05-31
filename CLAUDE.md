# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an **illegal gambling domain detection crawler MVP** that searches keywords, extracts URLs from search engine results, and stores them locally. The system is designed purely for URL collection without domain analysis, risk scoring, or UI components.

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

### Running Tests
```bash
# Run Gemini classifier test (requires GEMINI_API_KEY in .env file)
python test_gemini.py

# Run database tests (requires database credentials in .env file)
python test_database.py
```

## Common Development Commands

```bash
# Verify dependencies are installed correctly
python -c "import selenium; import bs4; import google.generativeai; print('All dependencies OK')"

# Run the crawler with default settings
python main.py

# Check current crawl results and statistics
python -c "from src.json_storage import JSONStorage; s = JSONStorage(); print(s.get_stats())"

# List all keyword combinations that will be searched
python -c "from src.keyword_manager import KeywordManager; km = KeywordManager(); print(km.generate_combinations())"

# Export data from results.json to database
python -c "from src.database import DatabaseManager; db = DatabaseManager(); db.connect(); db.import_from_json('results.json')"
```

### Configuration
The crawler is controlled via `settings.json`:
- `search_engine`: Which search engine to use (e.g., "google")
- `headless_mode`: Run browser in headless mode (true/false)
- `delay_between_searches`: Seconds to wait between search requests
- `max_links_per_search`: Maximum number of URLs to extract per search
- `output_file`: Path to store collected URLs (default: "results.json")
- `remove_tracking_params`: Strip tracking parameters from URLs (true/false)
- `use_gemini_classifier`: Enable Gemini-based URL classification (true/false)

**Note:** API keys and database credentials are now managed via `.env` file (not `settings.json`).

## Key Development Notes

### Dependencies & Missing Packages
The `pyproject.toml` file is missing `google-generativeai` which is required for Gemini classification. This should be installed when running `pip install -e .`, but if you see import errors, install it directly:
```bash
pip install google-generativeai
```

### File Structure Overview
```
illicit-gambling-detector/
├── main.py                    # Entry point
├── settings.json              # Crawler configuration
├── keywords.json              # Search keywords
├── .env                       # API keys and DB credentials (not in git)
├── env_template.txt           # Template for .env
├── src/
│   ├── crawler.py             # Main orchestrator
│   ├── keyword_manager.py     # Keyword loading and combinations
│   ├── search_engine.py       # Web search (Selenium + requests fallback)
│   ├── url_extractor.py       # URL parsing and cleaning
│   ├── gemini_classifier.py   # AI-based classification
│   ├── json_storage.py        # JSON file persistence
│   └── database.py            # PostgreSQL integration
├── test_gemini.py             # Gemini API test
├── test_database.py           # Database integration test (if exists)
└── results.json               # Output file with crawled results
```

### Module Dependencies
- `crawler.py` depends on all other src modules
- `search_engine.py` has fallback: Selenium → requests library
- `gemini_classifier.py` requires `GEMINI_API_KEY` in `.env` (optional but recommended)
- `database.py` requires PostgreSQL connection credentials in `.env`

### Windows-Specific Notes
- Use `python` instead of `python3` on Windows
- Virtual environment activation: `.venv\Scripts\activate` (not `source .venv/bin/activate`)
- Chrome/Chromium: webdriver-manager handles installation automatically, but ensure Chrome is in PATH or standard install locations
- If Selenium fails, the system falls back to requests-based HTTP searches

## Architecture

The crawler follows a modular design with clear separation of concerns:

**Core Components:**
- `src/keyword_manager.py` - Loads keywords from JSON and generates 2-keyword combinations
- `src/search_engine.py` - Handles web searching with Selenium/requests fallback mechanism
- `src/url_extractor.py` - Extracts and cleans URLs from HTML using BeautifulSoup
- `src/json_storage.py` - Manages JSON file storage with deduplication and metadata
- `src/gemini_classifier.py` - Analyzes URLs using Google's Gemini API to classify illegal gambling sites
- `src/database.py` - PostgreSQL database integration for persistent storage (Supabase)
- `src/crawler.py` - Main orchestrator that coordinates all components

**Configuration Files:**
- `keywords.json` - Contains the list of gambling-related keywords to search
- `settings.json` - Controls search engine, headless mode, delays, and output settings
- `.env` - Contains API keys and database credentials (not committed to git)
- `env_template.txt` - Template for creating `.env` file
- `results.json` - Output file containing collected URLs with metadata

**Search Engine Strategy:**
The system implements a fallback mechanism: attempts Selenium with Chrome first, automatically falls back to requests-based HTTP calls if Chrome/ChromeDriver fails. This ensures functionality across different environments (including WSL/containers where GUI apps may not work).

**Data Flow:**
1. KeywordManager loads keywords and generates combinations
2. SearchEngine performs searches (Selenium → requests fallback)
3. URLExtractor parses HTML and cleans URLs (removes tracking parameters)
4. GeminiClassifier analyzes each URL (optional, if enabled in settings)
5. JSONStorage saves results with deduplication, timestamps, and classification metadata
6. Crawler orchestrates the process with configurable delays between searches

**Gemini Classification Integration:**
When enabled (`use_gemini_classifier: true`), the crawler:
- Fetches the HTML content from each discovered URL
- Sends the URL and HTML to Google's Gemini 2.5 Flash model for analysis
- Stores classification results including confidence scores and detected keywords
- Handles missing/invalid API keys gracefully (logs warning, continues without classification)
- Reads `GEMINI_API_KEY` from `.env` file (environment variable)

**Database Integration:**
The system supports persistent storage in PostgreSQL (Supabase):
- `src/database.py` provides `DatabaseManager` class for database operations
- Table schema includes URL, keywords, timestamps, Gemini classification results
- Supports bulk import from `results.json` via `import_from_json()` function
- Automatic deduplication using URL as unique constraint
- Indexes on URL, is_illegal, collected_at, and detected_keywords (JSONB) for fast queries
- Database credentials are loaded from `.env` file

**Important Implementation Notes:**
- The search engine includes bot detection avoidance (user-agent rotation, random delays, automation flags disabled)
- URL extraction filters out invalid URLs, removes tracking parameters, and deduplicates results
- All results are stored with timestamp and source keyword for traceability
- The system handles interruptions gracefully and provides progress feedback

## Current Repository Status

**Files with uncommitted changes:**
- `keywords.json` - Modified (keyword updates)
- `src/search_engine.py` - Modified (session validation and error handling improvements)

**Key considerations for future development:**
- These changes represent recent enhancements to keyword lists and search engine stability
- Review git log for context on recent commits before making additional changes
- The project is actively maintained; check recent commits for patterns in code changes