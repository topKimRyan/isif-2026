// supabase_client.js

// IMPORTANT: Replace the values below with your actual Supabase project URL and anon key.
const SUPABASE_URL = 'https://ezpnbmglzbxujveexmvm.supabase.co'; // e.g. https://your-project-id.supabase.co
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6cG5ibWdsemJ4dWp2ZWV4bXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Nzg5MjcsImV4cCI6MjA4MDA1NDkyN30.ngUP3-o0a3M2wG_8IfDZVLpQEbTCjh5P2HO2ncnymhY'; // e.g. eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

let supabaseClient;

if (SUPABASE_URL === 'YOUR_SUPABASE_URL' || SUPABASE_ANON_KEY === 'YOUR_SUPABASE_ANON_KEY') {
    // Use a more subtle warning in the console instead of an alert
    console.warn('Supabase URL and anon key are not configured. Please update report_page/supabase_client.js');
} else {
    // Initialize the Supabase client. The `supabase` global object is expected to be available from the CDN script.
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}
