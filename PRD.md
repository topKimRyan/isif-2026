# 📌 PRD (MVP Version): Keyword-Based Illegal Gambling Domain Detection Crawler with AI Classification

## 1. Overview
This project is a **minimal viable product (MVP)** for detecting potentially illegal gambling-related domains by **searching keywords, extracting URLs from search engine result pages (SERPs), analyzing them with Google's Gemini AI, and storing results locally**.

The system:
- Loads keywords from a JSON file
- Searches keywords automatically using Selenium (with requests fallback)
- Extracts URLs from search results (first page only)
- Fetches and analyzes each URL with Google's Gemini AI model
- Classifies URLs as illegal gambling sites with confidence scores
- Stores enriched results (URLs, classifications, metadata) locally in JSON

➡ **URL collection + AI-powered classification. No UI, no scheduler, no domain risk scoring — purely keyword search, URL extraction, and Gemini-based analysis.**

---

## 2. Objectives
- Load keywords from a local file
- Search keywords automatically using Selenium (with fallback to requests-based HTTP)
- Extract URLs from search engine result pages
- Fetch HTML content from each discovered URL
- Analyze URLs using Google's Gemini AI to detect illegal gambling sites
- Store results with classification metadata locally
- Handle errors gracefully and log warnings

---

## 3. Scope (MVP Features)

### ✔ 3.1 Keyword List Loading
- Load keywords from `keywords.json`
- Support single keywords and multi-word keyword phrases
- Example: `["스포츠 배팅 신규"]`

### ✔ 3.2 Search Engine Automation
- Support **Google** as primary search engine
- Fetch only **first page** of results (10 links max by default)
- Selenium-based searching with Chrome/Chromium browser
- **Automatic fallback to requests-based HTTP** if Selenium/ChromeDriver fails
- Headless mode support
- Configurable delays between searches
- Bot detection avoidance (user-agent rotation, random delays, automation flags disabled)

### ✔ 3.3 URL Extraction & Cleaning
- Extract all anchor tag URLs from search results
- Remove duplicates
- Remove tracking parameters (e.g., `?utm_source=...`) - configurable
- Filter out invalid URLs and data URLs
- Smart back navigation handling for non-final links

### ✔ 3.4 URL Analysis with Gemini AI
- Fetch HTML content from each discovered URL
- Send URL + HTML content to Google's Gemini 2.5 Flash model
- Classify URLs as:
  - `is_illegal`: boolean (whether site is illegal gambling)
  - `confidence`: float (0.0-1.0) confidence score
  - `reason`: explanation for classification
  - `detected_keywords`: list of keywords found in the content
- Handle API errors gracefully (missing keys, timeouts, etc.)
- HTML content size limiting (50,000 characters max) to respect API constraints

### ✔ 3.5 Local Storage
- Store results in JSON format (`results.json`)
- Required fields per URL:
  - `url` (string)
  - `keyword_used` (string) - which keyword found this URL
  - `collected_at` (ISO timestamp)
  - `classification` (object) - Gemini analysis results
    - `is_illegal` (boolean)
    - `confidence` (float)
    - `reason` (string)
    - `detected_keywords` (array)
  - `source_rank` (integer) - position in search results
- Automatic deduplication
- Metadata tracking (timestamps, source keywords)

### ✔ 3.6 Configuration Management
- `settings.json` controls:
  - `search_engine` - which search engine (Google, etc.)
  - `headless_mode` - run browser in headless mode (true/false)
  - `delay_between_searches` - seconds to wait between searches
  - `max_links_per_search` - maximum URLs to extract per search (default: 10)
  - `output_file` - path to results JSON file
  - `remove_tracking_params` - strip tracking parameters (true/false)
  - `use_gemini_classifier` - enable Gemini analysis (true/false)
  - `gemini_api_key` - Google Generative AI API key (or use env variable)

---

## 4. Out of Scope (Not Included in MVP)
The following features are intentionally excluded:

- Domain risk scoring (WHOIS, VirusTotal, etc.)
- ML-based domain pattern detection (beyond Gemini classification)
- Multi-search-engine support (Google only)
- Automated scheduling (manual run only)
- Proxy/VPN systems
- Admin dashboard UI
- Deep crawling inside target websites
- Messaging platform scraping (Telegram, Discord, etc.)
- Database persistence (SQLite) - JSON only
- Real-time monitoring or alerts

➡ **MVP = "Keyword → Search → URL Extract → Gemini Analysis → Save" only.**

---

## 5. Workflow

1. Load `keywords.json`
2. For each keyword:
   - Search using Selenium (fallback to requests if needed)
   - Load the SERP
   - Extract URLs (max 10 per search by default)
   - Remove duplicates & invalid URLs
   - Strip tracking parameters
3. For each extracted URL:
   - Fetch HTML content
   - Send to Gemini AI for classification
   - Store classification results
4. Save all results to `results.json` with deduplication
5. Log progress and any errors/warnings

---

## 6. Technical Requirements

### Language & Libraries
- Python 3.12+ (required)
- **Selenium** - web automation for search
- **BeautifulSoup4** - HTML parsing
- **requests** - fallback HTTP client
- **google-generativeai** - Gemini API integration
- Chrome/Chromium browser (required for Selenium)
- Google Generative AI API key (required for classification)

### Execution Environment
- CLI-based Python script (`python main.py`)
- Environment-based configuration via `settings.json`
- No external databases required (JSON storage only)

### Bot Detection Avoidance
- Random user-agent rotation
- Random delays between requests
- Disabled automation flags in Selenium
- Requests library with realistic headers

---

## 7. Directory Structure

```
illicit-gambling-detector/
├── main.py                      # Entry point - runs the crawler
├── settings.json                # Configuration (search engine, delays, API key, etc.)
├── keywords.json                # List of keywords to search
├── results.json                 # Output file with collected URLs + classifications
├── CLAUDE.md                    # Development guidance
├── README.md                    # User-facing documentation
├── PRD.md                       # This file
├── test_gemini.py               # Unit test for Gemini classifier
├── requirements.txt             # Python dependencies
├── src/
│   ├── __init__.py
│   ├── crawler.py               # Main orchestrator (GamblingDomainCrawler)
│   ├── keyword_manager.py       # Loads keywords from JSON
│   ├── search_engine.py         # Selenium-based search (with requests fallback)
│   ├── url_extractor.py         # Extracts URLs from HTML, removes tracking params
│   ├── json_storage.py          # Saves/loads results to/from JSON
│   └── gemini_classifier.py     # Gemini AI classification for URLs
└── .venv/                       # Virtual environment (not committed)
```

---

## 8. Data Model

### Result JSON Structure
```json
{
  "metadata": {
    "total_urls": 5,
    "classified_urls": 4,
    "unclassified_urls": 1,
    "last_updated": "2024-11-22T14:30:00Z"
  },
  "results": [
    {
      "url": "https://example-gambling.com",
      "keyword_used": "스포츠 배팅 신규",
      "collected_at": "2024-11-22T14:30:00Z",
      "source_rank": 1,
      "classification": {
        "is_illegal": true,
        "confidence": 0.92,
        "reason": "Site offers unregulated sports betting services with no licensing information",
        "detected_keywords": ["sports betting", "no verification", "instant payment"]
      }
    },
    {
      "url": "https://another-site.com",
      "keyword_used": "스포츠 배팅 신규",
      "collected_at": "2024-11-22T14:30:15Z",
      "source_rank": 2,
      "classification": {
        "is_illegal": false,
        "confidence": 0.88,
        "reason": "Site is a legitimate news portal about sports",
        "detected_keywords": []
      }
    }
  ]
}
```

### Settings JSON Structure
```json
{
  "search_engine": "google",
  "headless_mode": false,
  "delay_between_searches": 5,
  "max_links_per_search": 10,
  "output_file": "results.json",
  "remove_tracking_params": true,
  "use_gemini_classifier": true,
  "gemini_api_key": "AIzaSy..."
}
```

---

## 9. Error Handling & Logging

### Graceful Degradation
- If Selenium fails → automatically fallback to requests-based HTTP search
- If Gemini API key missing → continue without classification, log warning
- If URL fetch fails → skip that URL, log error, continue
- If Gemini API call fails → store URL without classification, log error

### User Feedback
- Progress logging during crawl (keywords processed, URLs found, classified, etc.)
- Warning messages for missing API keys or failed API calls
- Error summaries at the end of execution

---

## 10. Execution Examples

### Basic Usage
```bash
# Activate virtual environment
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Run the crawler
python main.py
```

### Configuration Before Running
1. Edit `keywords.json` with target keywords
2. Edit `settings.json` with your preferences:
   - `headless_mode`: true for production, false for debugging
   - `delay_between_searches`: increase if you hit rate limits
   - `use_gemini_classifier`: false to skip AI classification
   - `gemini_api_key`: set via environment variable `GEMINI_API_KEY` or directly

### Output
- All results saved to `results.json` with full classification data
- JSON file is automatically formatted for readability
- Deduplication ensures no duplicate URLs stored

---

## 11. Success Criteria for MVP

✅ **Completed:**
- [x] Keyword loading from JSON
- [x] Selenium-based Google search with requests fallback
- [x] URL extraction and cleaning (tracking param removal)
- [x] Gemini AI classification integration
- [x] JSON-based result storage with deduplication
- [x] Configuration via settings.json
- [x] Error handling and graceful degradation
- [x] Metadata tracking (timestamps, source keywords, confidence scores)

**No longer in scope:**
- ~~Keyword combination generation~~ (simplified to direct keyword support)
- ~~SQLite storage~~ (JSON only)
- ~~Multi-search-engine support~~ (Google only)
- ~~Automated scheduling~~ (manual run only)