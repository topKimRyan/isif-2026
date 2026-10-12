const SUPABASE_URL = 'https://pimnyvbggbobuvnyezga.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpbW55dmJnZ2JvYnV2bnllemdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAyMjc4MzMsImV4cCI6MjA5NTgwMzgzM30.UTTzmrEH6k_FVNgnbElR8ubQCJbbke2FrRIvc3a1mCw';

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

let rawSites = [];   // every row from Supabase
let allSites = [];   // rawSites after the viewer's Settings filters
let filteredSites = [];

const VIEW_TITLES = { sites: 'Detected Sites', analytics: 'Analytics', logs: 'Logs', settings: 'Settings' };

document.addEventListener('DOMContentLoaded', () => {
    showView(viewFromHash());
    loadData();
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterSites(e.target.value);
    });
});

window.addEventListener('hashchange', () => showView(viewFromHash()));

function viewFromHash() {
    const view = location.hash.replace('#', '');
    if (VIEW_TITLES[view]) return view;
    const saved = getSetting('defaultView');
    return VIEW_TITLES[saved] ? saved : 'sites';
}

// Switch between the "Detected Sites" table and the "Analytics" charts
function showView(view) {
    document.getElementById('view-sites').hidden     = view !== 'sites';
    document.getElementById('view-analytics').hidden = view !== 'analytics';
    document.getElementById('view-logs').hidden      = view !== 'logs';
    document.getElementById('view-settings').hidden  = view !== 'settings';
    document.getElementById('topbar-title').textContent = VIEW_TITLES[view];
    document.querySelectorAll('.nav-link[data-view]').forEach(link => {
        link.classList.toggle('active', link.dataset.view === view);
    });
    // Charts size themselves to their container, so draw them once the view is visible
    if (view === 'analytics' && typeof renderAnalytics === 'function') renderAnalytics();
    if (view === 'logs' && typeof renderLogs === 'function') renderLogs();
    if (view === 'settings') renderSettingsInfo();
}

// Open the sites table filtered by a term (used by the analytics charts)
function showSitesFor(term) {
    const input = document.getElementById('search-input');
    input.value = term;
    filterSites(term);
    location.hash = 'sites';
}

// silent: keep the current table on screen while reloading (used by auto-refresh)
async function loadData({ silent = false } = {}) {
    const loadingEl   = document.getElementById('loading');
    const errorEl     = document.getElementById('error');
    const tableEl     = document.getElementById('sites-table');
    const emptyEl     = document.getElementById('empty-state');

    if (!silent) {
        loadingEl.style.display = 'flex';
        tableEl.style.display   = 'none';
        emptyEl.style.display   = 'none';
    }
    errorEl.style.display = 'none';

    try {
        const { data, error } = await supabaseClient
            .from('gambling_urls')
            // Only the columns the public dashboard may read (see supabase/security.sql)
            .select('url, keyword_used, gemini_confidence, collected_at, detected_keywords, screenshot_url, gemini_reason, is_illegal, category')
            .eq('is_illegal', true)
            .order('collected_at', { ascending: false });

        if (error) throw error;

        rawSites = data || [];
        lastLoadedAt = new Date();
        reapplySiteSettings();

        loadingEl.style.display = 'none';

    } catch (err) {
        console.error('Failed to load data:', err);
        loadingEl.style.display = 'none';
        document.getElementById('error-msg').textContent = `Failed to load data: ${err.message}`;
        errorEl.style.display = 'flex';
    }
}

// Re-run the Settings filters over the loaded rows and redraw every view
function reapplySiteSettings() {
    allSites = applySiteSettings(rawSites);
    updateStatistics(allSites);
    filterSites(document.getElementById('search-input').value);
    if (typeof renderAnalytics === 'function') renderAnalytics();
    if (typeof renderLogs === 'function') renderLogs();
    renderSettingsInfo();
}

function updateStatistics(sites) {
    const total = sites.length;
    const avgConf = total > 0
        ? (sites.reduce((s, x) => s + (x.gemini_confidence || 0), 0) / total).toFixed(2)
        : '0.00';

    const lastUpdate = total > 0 && sites[0].collected_at
        ? formatDate(sites[0].collected_at)
        : '—';

    document.getElementById('total-count').textContent   = total;
    document.getElementById('avg-confidence').textContent = avgConf;
    document.getElementById('last-update').textContent   = lastUpdate;
}

function renderTable(sites) {
    const tbody   = document.getElementById('sites-tbody');
    const tableEl = document.getElementById('sites-table');
    const emptyEl = document.getElementById('empty-state');
    const footer  = document.getElementById('table-footer');

    tbody.innerHTML = '';

    if (sites.length === 0) {
        tableEl.style.display = 'none';
        emptyEl.style.display = 'flex';
        footer.textContent = '';
        return;
    }

    emptyEl.style.display = 'none';
    tableEl.style.display = 'table';

    sites.forEach((site, index) => {
        const domain = extractDomain(site.url);
        const confClass = getConfidenceClass(site.gemini_confidence);
        const confVal = (site.gemini_confidence || 0);
        const fillClass = confClass.replace('confidence-', 'fill-');
        const keywordLabel = site.keyword_used
            ? `<span class="keyword-chip">${escapeHtml(site.keyword_used)}</span>`
            : '<span style="color:var(--text-3)">—</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <img class="favicon"
                     src="https://www.google.com/s2/favicons?sz=32&domain=${encodeURIComponent(domain)}"
                     alt=""
                     onerror="this.replaceWith(Object.assign(document.createElement('span'), {className: 'favicon-placeholder', textContent: '🌐'}))">
            </td>
            <td class="url-cell">
                <a href="${escapeHtml(safeUrl(site.url))}" target="_blank" rel="noopener noreferrer" class="url-link"
                   title="${escapeHtml(site.url)}">
                    ${escapeHtml(truncateUrl(site.url, 55))}
                </a>
                ${site.category === 'promotion' ? '<span class="keyword-chip">Promotion</span>' : ''}
            </td>
            <td>${keywordLabel}</td>
            <td>
                <div class="confidence-bar-wrap">
                    <div class="confidence-bar">
                        <div class="confidence-bar-fill ${fillClass}" style="width:${Math.round(confVal * 100)}%"></div>
                    </div>
                    <span class="confidence-badge ${confClass}">${confVal.toFixed(2)}</span>
                </div>
            </td>
            <td><span class="date-text">${formatDateTime(site.collected_at)}</span></td>
            <td>
                <button class="detail-btn" onclick="showDetail(${index})">Details →</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    footer.textContent = `Showing ${sites.length} of ${allSites.length} records`;
}

function filterSites(term) {
    const q = term.toLowerCase().trim();
    filteredSites = q
        ? allSites.filter(s =>
            s.url.toLowerCase().includes(q) ||
            (s.keyword_used && s.keyword_used.toLowerCase().includes(q)) ||
            (Array.isArray(s.detected_keywords) &&
             s.detected_keywords.some(k => String(k).toLowerCase().includes(q)))
          )
        : [...allSites];
    renderTable(filteredSites);
}

function showDetail(index) {
    showSiteDetail(filteredSites[index]);
}

function showSiteDetail(site) {
    const modal = document.getElementById('detail-modal');
    const body  = document.getElementById('modal-body');

    const confClass = getConfidenceClass(site.gemini_confidence);
    const confVal   = (site.gemini_confidence || 0).toFixed(2);

    const keywordTags = (site.detected_keywords && site.detected_keywords.length > 0)
        ? site.detected_keywords.map(k => `<span class="keyword-tag">${escapeHtml(k)}</span>`).join('')
        : '<span style="color:var(--text-3)">None detected</span>';

    const screenshotHTML = site.screenshot_url
        ? `<div class="modal-section">
               <div class="modal-label">Screenshot</div>
               <div class="modal-value"><img src="${escapeHtml(safeUrl(site.screenshot_url))}" alt="Screenshot" class="screenshot-img"></div>
           </div><hr class="modal-divider">`
        : '';

    body.innerHTML = `
        <div class="modal-section">
            <div class="modal-label">URL</div>
            <div class="modal-value">
                <a href="${escapeHtml(safeUrl(site.url))}" target="_blank" rel="noopener noreferrer" class="url-link">${escapeHtml(site.url)}</a>
            </div>
        </div>
        <hr class="modal-divider">
        ${screenshotHTML}
        <div class="modal-section">
            <div class="modal-label">Search Keyword</div>
            <div class="modal-value">${escapeHtml(site.keyword_used || '—')}</div>
        </div>
        <div class="modal-section">
            <div class="modal-label">Category</div>
            <div class="modal-value">${escapeHtml(categoryLabel(site.category))}</div>
        </div>
        <div class="modal-section">
            <div class="modal-label">Confidence Score</div>
            <div class="modal-value">
                <span class="confidence-badge ${confClass}">${confVal}</span>
            </div>
        </div>
        <div class="modal-section">
            <div class="modal-label">Detected At</div>
            <div class="modal-value">${formatDateTime(site.collected_at)}</div>
        </div>
        <hr class="modal-divider">
        <div class="modal-section">
            <div class="modal-label">AI Reasoning</div>
            <div class="modal-value">${escapeHtml(site.gemini_reason || 'No reasoning provided.')}</div>
        </div>
        <div class="modal-section">
            <div class="modal-label">Detected Keywords</div>
            <div class="modal-value" style="margin-top:4px">${keywordTags}</div>
        </div>
    `;

    modal.style.display = 'flex';
}

function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

window.addEventListener('click', (e) => {
    if (e.target === document.getElementById('detail-modal')) closeModal();
});

// Escape text before inserting it into innerHTML (AI output and URLs are untrusted)
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Only allow http(s) links so stored URLs like "javascript:..." can't run code
function safeUrl(url) {
    try {
        const parsed = new URL(url);
        return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : '#';
    } catch {
        return '#';
    }
}

function categoryLabel(category) {
    if (category === 'operator') return 'Gambling site (operator)';
    if (category === 'promotion') return 'Promotion (steers visitors to gambling sites)';
    return '—';
}

function extractDomain(url) {
    try { return new URL(url).hostname; }
    catch { return ''; }
}

function truncateUrl(url, max) {
    url = String(url ?? '');
    return url.length <= max ? url : url.slice(0, max) + '…';
}

function getConfidenceClass(c) {
    if (c >= 0.9) return 'confidence-high';
    if (c >= 0.7) return 'confidence-medium';
    return 'confidence-low';
}

function formatDate(dateStr) {
    const d = new Date(dateStr);
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

function formatDateTime(dateStr) {
    if (!dateStr) return '—';
    const d = new Date(dateStr);
    return `${formatDate(dateStr)} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
}
