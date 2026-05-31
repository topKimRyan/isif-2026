import os
import sys
import asyncio
from supabase import Client

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))

src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from gemini_classifier import GeminiClassifier
from search_engine import SearchEngine


def _get_html_sync(url: str) -> str:
    """
    Synchronous function to fetch HTML content.
    This function is designed to be run in a separate thread.
    The SearchEngine class handles its own driver setup and teardown.
    """
    print(f"Initializing SearchEngine for HTML fetch (sync)...")
    search_engine = SearchEngine(headless=True)
    html_content = search_engine.get_html_content_from_url(url)
    return html_content


async def handle_analysis(supabase: Client, report: dict):
    """
    Fetches URL content in a non-blocking way, classifies it,
    and updates the report in Supabase.
    """
    report_id = report.get('id')
    url = report.get('url')

    if not report_id or not url:
        print("Error: Invalid report data received for analysis.")
        return

    print(f"[{report_id}] Starting analysis for URL: {url}")

    try:
        # 1. Fetch HTML content from the URL in a separate thread
        print(f"[{report_id}] Scheduling HTML fetch task in a separate thread...")
        html_content = await asyncio.to_thread(_get_html_sync, url)

        if not html_content:
            print(f"[{report_id}] Failed to fetch HTML content for {url}")
            await supabase.table('report_requests').update({
                'status': 'error', 
                'reason': f"URL에서 콘텐츠를 가져올 수 없습니다: {url}"
            }).eq('id', report_id).execute()
            return

        print(f"[{report_id}] Successfully fetched HTML content. Length: {len(html_content)}")

        # 2. Initialize and use the Gemini Classifier
        print(f"[{report_id}] Initializing GeminiClassifier...")
        classifier = GeminiClassifier()
        analysis_result = classifier.classify_url(url, html_content)
        print(f"[{report_id}] GeminiClassifier analysis result: {analysis_result}")

        if analysis_result.get("error"):
            raise Exception(analysis_result["error"])

        # 3. Update the report in Supabase with the analysis results
        update_data = {
            'is_illegal': analysis_result.get('is_illegal'),
            'confidence': analysis_result.get('confidence'),
            'reason': analysis_result.get('reason'),
            'detected_keywords': analysis_result.get('detected_keywords'),
            'status': 'analyzed'
        }
        print(f"[{report_id}] Updating Supabase with data: {update_data}")
        
        await supabase.table('report_requests').update(update_data).eq('id', report_id).execute()
        print(f"[{report_id}] Analysis complete. Status updated to 'analyzed'.")

    except Exception as e:
        print(f"[{report_id}] An error occurred during analysis: {e}")
        try:
            await supabase.table('report_requests').update({
                'status': 'error',
                'reason': f"분석 중 오류가 발생했습니다: {e}"
            }).eq('id', report_id).execute()
        except Exception as db_error:
            print(f"[{report_id}] Failed to update report with error status: {db_error}")