# report_page/server/handlers/database_logger.py
from supabase import Client
from datetime import datetime, timezone

UTC = timezone.utc

async def log_final_report(supabase: Client, report: dict):
    """
    Always inserts a new record into the 'gambling_urls' table for every final, reported data.
    The 'keyword_used' is manually set to 'manual report'.
    """
    report_id = report.get('id')
    report_url = report.get('url')
    is_illegal = report.get('is_illegal')
    confidence = report.get('confidence')
    reason = report.get('reason')
    screenshot_url = report.get('screenshot_url')
    gemini_error = report.get('gemini_error')
    detected_keywords = report.get('detected_keywords')

    if not report_url:
        print(f"[{report_id}] Cannot log to gambling_urls, report URL is missing.")
        return

    print(f"[{report_id}] Always creating a new final report log for URL: {report_url} in gambling_urls table.")

    try:
        # Always insert a new entry, regardless of whether the URL exists
        insert_data = {
            'url': report_url,
            'is_illegal': is_illegal,
            'gemini_confidence': confidence,
            'gemini_reason': reason,
            'gemini_error': gemini_error,
            'detected_keywords': detected_keywords,  # Use actual detected_keywords
            'keyword_used': 'manual report', # Add non-null value for keyword_used
            'screenshot_url': screenshot_url,
            'collected_at': datetime.now(UTC).isoformat(),
        }
        await supabase.table('gambling_urls').insert(insert_data).execute()
        print(f"[{report_id}] Created new entry in 'gambling_urls' for URL: {report_url} with manual keywords.")

    except Exception as e:
        print(f"[{report_id}] Error inserting into 'gambling_urls' table: {e}")
        # Log the error but don't re-raise.

