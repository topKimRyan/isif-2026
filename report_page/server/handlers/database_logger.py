# report_page/server/handlers/database_logger.py
import asyncio
from supabase import Client
from postgrest import APIResponse
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

async def upsert_illegal_site(supabase: Client, report: dict):
    """
    Inserts or updates a record in the 'illegal_sites' table based on the report.
    - If the URL doesn't exist, it creates a new record.
    - If the URL exists, it increments the report_count and updates the timestamp.
    """
    report_id = report.get('id')
    report_url = report.get('url')
    reason = report.get('reason')
    keywords = report.get('detected_keywords')

    if not report_url:
        print(f"[{report_id}] Cannot log to illegal_sites, report URL is missing.")
        return

    try:
        # Check if the URL already exists in the illegal_sites table
        # maybe_single() returns one record or None, without raising an error.
        response: APIResponse = await supabase.table('illegal_sites').select('id, report_count').eq('url', report_url).maybe_single().execute()
        
        existing_entry = response.data

        if existing_entry:
            # Entry exists: Update it
            entry_id = existing_entry['id']
            current_count = existing_entry.get('report_count', 0)
            
            update_data = {
                'updated_at': datetime.now(KST).isoformat(),
                'report_count': current_count + 1,
                'last_report_reason': reason,
                'last_detected_keywords': keywords
            }
            
            await supabase.table('illegal_sites').update(update_data).eq('id', entry_id).execute()
            print(f"[{report_id}] Updated existing entry in 'illegal_sites' for URL: {report_url}")

        else:
            # Entry does not exist: Insert a new one
            insert_data = {
                'url': report_url,
                'report_count': 1,
                'last_report_reason': reason,
                'last_detected_keywords': keywords,
                # 'created_at' and 'updated_at' should be handled by DB defaults
            }
            await supabase.table('illegal_sites').insert(insert_data).execute()
            print(f"[{report_id}] Created new entry in 'illegal_sites' for URL: {report_url}")

    except Exception as e:
        print(f"[{report_id}] Error upserting to 'illegal_sites' table: {e}")
        # We don't re-raise the exception, as this is a secondary logging task.
        # The main report process should not fail because of this.


async def log_final_report(supabase: Client, report: dict):
    """
    Always inserts a new record into the 'gambling_urls' table for every final, reported data.
    The 'keyword_used' is manually set to '수동 신고'.
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
            'keyword_used': '수동 신고', # Add non-null value for keyword_used
            'screenshot_url': screenshot_url,
            'collected_at': datetime.now(KST).isoformat(),
        }
        await supabase.table('gambling_urls').insert(insert_data).execute()
        print(f"[{report_id}] Created new entry in 'gambling_urls' for URL: {report_url} with manual keywords.")

    except Exception as e:
        print(f"[{report_id}] Error inserting into 'gambling_urls' table: {e}")
        # Log the error but don't re-raise.

