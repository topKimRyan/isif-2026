// supabase_client.js

// IMPORTANT: 아래를 실제 Supabase 프로젝트 URL과 anon key로 바꾸십시오.
const SUPABASE_URL = 'https://ezpnbmglzbxujveexmvm.supabase.co'; // 예: https://your-project-id.supabase.co
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6cG5ibWdsemJ4dWp2ZWV4bXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Nzg5MjcsImV4cCI6MjA4MDA1NDkyN30.ngUP3-o0a3M2wG_8IfDZVLpQEbTCjh5P2HO2ncnymhY'; // 예: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

let supabaseClient;

if (SUPABASE_URL === 'YOUR_SUPABASE_URL' || SUPABASE_ANON_KEY === 'YOUR_SUPABASE_ANON_KEY') {
    // Use a more subtle warning in the console instead of an alert
    console.warn('Supabase URL and anon key are not configured. Please update report_page/supabase_client.js');
} else {
    // Supabase 클라이언트를 초기화합니다. `supabase` 전역 객체는 CDN 스크립트에서 사용 가능할 것으로 예상됩니다.
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}
