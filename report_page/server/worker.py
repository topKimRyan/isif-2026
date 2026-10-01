# report_page/server/worker.py

import os
import asyncio
from dotenv import load_dotenv
from supabase import create_async_client, Client
from realtime import AsyncRealtimeClient, RealtimeSubscribeStates
from typing import Optional
from handlers.analyze import handle_analysis
from handlers.screenshot import handle_screenshot
from handlers.database_logger import log_final_report

async def main():
    # Load environment variables from .env file
    # Make sure you have a .env file in the root directory with SUPABASE_URL and SUPABASE_SERVICE_KEY
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))

    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and service key must be set in .env file")

    # Initialize the standard Supabase client for other operations (e.g., database inserts/updates)
    supabase: Client = await create_async_client(SUPABASE_URL, SUPABASE_KEY)

    # Format the Supabase URL for the Realtime client
    # Assumes SUPABASE_URL is like "https://<project_ref>.supabase.co"
    REALTIME_URL = SUPABASE_URL.replace("https://", "wss://") + "/realtime/v1"

    # Initialize the AsyncRealtimeClient directly
    socket = AsyncRealtimeClient(REALTIME_URL, SUPABASE_KEY)

    # Callback for new 'submitted' reports
    async def handle_submitted_report_callback(payload):
        report = payload.get('data', {}).get('record', {})
        if report:
            print(f"SUBMITTED event received: {report['id']}.")
            # Schedule the handler to run as a background task
            asyncio.create_task(handle_analysis(supabase, report))
    
    # Callback for 'confirmed' reports
    async def handle_confirmed_report_callback(payload):
        report = payload.get('data', {}).get('record', {})
        if report:
            print(f"CONFIRMED event received: {report['id']}.")
            # Schedule the handler to run as a background task
            asyncio.create_task(handle_screenshot(supabase, report))

    # Callback for 'reported' reports - final logging to gambling_urls
    async def handle_reported_report_callback(payload):
        report = payload.get('data', {}).get('record', {})
        if report:
            print(f"REPORTED event received: {report['id']}.")
            # Schedule the handler to run as a background task
            asyncio.create_task(log_final_report(supabase, report))

    print("Worker started. Listening for database changes...")

    # Create a single channel for all reports-related postgres_changes
    channel = socket.channel("reports_channel")

    channel.on_postgres_changes(
        event="INSERT",
        schema="public",
        table="report_requests",
        filter="status=eq.submitted",
        callback=lambda payload: asyncio.create_task(handle_submitted_report_callback(payload))
    )

    channel.on_postgres_changes(
        event="UPDATE",
        schema="public",
        table="report_requests",
        filter="status=eq.confirmed",
        callback=lambda payload: asyncio.create_task(handle_confirmed_report_callback(payload))
    )

    channel.on_postgres_changes(
        event="UPDATE",
        schema="public",
        table="report_requests",
        filter="status=eq.reported",
        callback=lambda payload: asyncio.create_task(handle_reported_report_callback(payload))
    )

    # Callback to handle subscription status
    def on_subscribe_status(status: RealtimeSubscribeStates, err: Optional[Exception]):
        if status == RealtimeSubscribeStates.SUBSCRIBED:
            print("Successfully subscribed to Realtime channel!")
        elif status == RealtimeSubscribeStates.CHANNEL_ERROR:
            print(f"Error subscribing to channel: {err}")
        elif status == RealtimeSubscribeStates.TIMED_OUT:
            print("Realtime subscription timed out.")
        elif status == RealtimeSubscribeStates.CLOSED:
            print("Realtime channel closed unexpectedly.")

    await channel.subscribe(on_subscribe_status)
        
    try:
        # Keep the main thread alive to listen for events by waiting on an event that will never be set
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        print("\nWorker shutting down due to cancellation.")
    except Exception as e:
        print(f"An error occurred in the realtime listener: {e}")
    finally:
        print("Stopping worker and cleaning up resources...")
        if socket and socket.is_connected:
            await socket.close()

        print("Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())