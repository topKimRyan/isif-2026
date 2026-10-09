// supabase_client.js

// IMPORTANT: Replace the values below with your actual Supabase project URL and anon key.
const SUPABASE_URL = 'https://pimnyvbggbobuvnyezga.supabase.co'; // e.g. https://your-project-id.supabase.co
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpbW55dmJnZ2JvYnV2bnllemdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAyMjc4MzMsImV4cCI6MjA5NTgwMzgzM30.UTTzmrEH6k_FVNgnbElR8ubQCJbbke2FrRIvc3a1mCw'; // e.g. eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

let supabaseClient;

if (SUPABASE_URL === 'YOUR_SUPABASE_URL' || SUPABASE_ANON_KEY === 'YOUR_SUPABASE_ANON_KEY') {
    // Use a more subtle warning in the console instead of an alert
    console.warn('Supabase URL and anon key are not configured. Please update report_page/supabase_client.js');
} else {
    // Initialize the Supabase client. The `supabase` global object is expected to be available from the CDN script.
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

// --- Report session ----------------------------------------------------------------------
// The report tables are not readable with the anon key. A report is reached through database
// functions (see supabase/security.sql) using its id plus a secret token that create_report
// returns once. Both travel in the page URL and are mirrored in sessionStorage.

function getReportAuth() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id') || sessionStorage.getItem('report_id');
    const token = params.get('t') || sessionStorage.getItem('report_token');
    return id && token ? { id, token } : null;
}

function saveReportAuth(id, token) {
    sessionStorage.setItem('report_id', id);
    sessionStorage.setItem('report_token', token);
}

function clearReportAuth() {
    sessionStorage.removeItem('report_id');
    sessionStorage.removeItem('report_token');
}

// Query string that carries the report credentials to the next page.
function reportQuery(auth) {
    return `id=${encodeURIComponent(auth.id)}&t=${encodeURIComponent(auth.token)}`;
}

async function reportRpc(name, args) {
    const { data, error } = await supabaseClient.rpc(name, args);
    if (error) throw error;
    return data;
}

// Returns {status, url, is_illegal, reason, detected_keywords}, or null if id/token don't match.
function fetchReport(auth) {
    return reportRpc('get_report', { p_id: auth.id, p_token: auth.token });
}

// Polls the report until the returned stop function is called (replaces Realtime, which
// would need table read access). onError fires for an unknown report or after 3 failed
// requests in a row.
function pollReport(auth, onReport, onError, intervalMs = 2000) {
    let stopped = false;
    let timer = null;
    let failures = 0;

    const tick = async () => {
        if (stopped) return;
        try {
            const report = await fetchReport(auth);
            if (stopped) return;
            failures = 0;
            if (!report) throw Object.assign(new Error('Report not found.'), { fatal: true });
            onReport(report);
        } catch (error) {
            if (stopped) return;
            failures += 1;
            if (error.fatal || failures >= 3) {
                onError(error);
                return;
            }
        }
        if (!stopped) timer = setTimeout(tick, intervalMs);
    };

    tick();
    return () => {
        stopped = true;
        clearTimeout(timer);
    };
}
