import os
import tempfile
import asyncio
from supabase import Client
import sys

# Add src directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))

src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from search_engine import SearchEngine
from url_safety import is_public_http_url


def _take_screenshot_sync(url: str, path: str):
    """
    Synchronous function to take a screenshot.
    This function is designed to be run in a separate thread.
    The SearchEngine class handles its own driver setup and teardown.
    """
    print(f"Initializing SearchEngine for screenshot (sync)...")
    search_engine = SearchEngine(headless=True)
    search_engine.take_screenshot_from_url(url, path)


async def handle_screenshot(supabase: Client, report: dict):
    """
    Takes a screenshot of a URL by running the synchronous screenshot logic
    in a separate thread, uploads it to Supabase Storage, and updates the report.
    """
    report_id = report.get('id')
    url = report.get('url')

    if not report_id or not url:
        print("Error: Invalid report data received for screenshot.")
        return

    print(f"[{report_id}] Starting screenshot for URL: {url}")

    if not await asyncio.to_thread(is_public_http_url, url):
        print(f"[{report_id}] Rejected non-public URL: {url}")
        await supabase.table('report_requests').update({
            'status': 'error',
            'reason': "Only public http(s) URLs can be reported."
        }).eq('id', report_id).execute()
        return
    
    # Create a temporary file path, ensuring it's closed so other processes can write to it.
    tmp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    screenshot_path = tmp_file.name
    tmp_file.close()

    try:
        # 1. Take screenshot with Selenium in a separate thread to avoid blocking
        print(f"[{report_id}] Scheduling screenshot task in a separate thread...")
        await asyncio.to_thread(_take_screenshot_sync, url, screenshot_path)
        
        print(f"[{report_id}] Screenshot saved to {screenshot_path}")

        # 2. Upload screenshot to Supabase Storage
        storage_path = f"screenshots/{report_id}.png"
        
        with open(screenshot_path, 'rb') as f:
            await supabase.storage.from_("report_screenshots").upload(
                file=f,
                path=storage_path,
                file_options={"content-type": "image/png", "upsert": "true"}
            )
        
        # 3. Get the public URL of the uploaded file
        res = await supabase.storage.from_("report_screenshots").get_public_url(storage_path)
        public_url = res

        print(f"[{report_id}] Screenshot uploaded to {public_url}")

        # 4. Update the report with the screenshot URL and set status to 'reported'
        update_data = {
            'screenshot_url': public_url,
            'status': 'reported'
        }
        await supabase.table('report_requests').update(update_data).eq('id', report_id).execute()
        
        print(f"[{report_id}] Report completed. Status updated to 'reported'.")

    except Exception as e:
        print(f"[{report_id}] An error occurred during screenshot handling: {e}")
        try:
            await supabase.table('report_requests').update({
                'status': 'error',
                'reason': f"Error occurred during screenshot capture/upload: {e}"
            }).eq('id', report_id).execute()
        except Exception as db_error:
            print(f"[{report_id}] Failed to update report with error status: {db_error}")
    finally:
        # Clean up the temporary file
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)