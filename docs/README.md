# Illegal Gambling Site Reporting Dashboard

A web dashboard for viewing and reporting illegal gambling sites detected by AI.

## File Structure

```
dashboard/
├── index.html    # Main HTML file
├── style.css     # Stylesheet
└── app.js        # JavaScript (Supabase connection and data loading)
```

## Usage

### 1. Run Locally

Open `index.html` directly in your browser:

```bash
# Windows
start dashboard/index.html

# Mac
open dashboard/index.html

# Linux
xdg-open dashboard/index.html
```

Or run a simple HTTP server:

```bash
# Python 3
cd dashboard
python -m http.server 8000

# Open http://localhost:8000 in your browser
```

### 2. Features

**Statistics section:**
- Total number of illegal sites
- Average confidence score
- Last updated timestamp

**Table section:**
- Favicon preview
- URL (opens in a new tab when clicked)
- Search keyword used
- AI confidence score (color-coded)
- Collection timestamp
- Details button

**Search:**
- Real-time filtering by URL or keyword

**Details modal:**
- AI reasoning
- Detected keywords list

### 3. Database Connection

Fetches illegal site data from the `gambling_urls` table in Supabase in real time.

Current connection settings:
- URL: `https://brdwgsnffgsmubnfjmyi.supabase.co`
- Table: `gambling_urls`
- Filter: `is_illegal = true`

### 4. How to Report

1. Find an illegal site on the dashboard
2. Click the Details button to review the AI reasoning
3. Copy the URL and report it to the relevant authority:
   - Cybercrime reporting: https://ecrm.police.go.kr/
   - Korea Communications Standards Commission: https://www.kocsc.or.kr/

## Notes

- This dashboard is read-only
- Uses the Supabase ANON_KEY — no write permissions
- Exercise caution when clicking URLs of illegal sites

## Tech Stack

- HTML5
- CSS3 (responsive design)
- JavaScript (ES6+)
- Supabase JavaScript Client (CDN)
