const SUPABASE_URL = 'https://pimnyvbggbobuvnyezga.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpbW55dmJnZ2JvYnV2bnllemdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAyMjc4MzMsImV4cCI6MjA5NTgwMzgzM30.UTTzmrEH6k_FVNgnbElR8ubQCJbbke2FrRIvc3a1mCw';

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

let allSites = [];
let filteredSites = [];

document.addEventListener('DOMContentLoaded', () => {
    loadData();
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterSites(e.target.value);
    });
});

async function loadData() {
    const loadingEl   = document.getElementById('loading');
    const errorEl     = document.getElementById('error');
    const tableEl     = document.getElementById('sites-table');
    const emptyEl     = document.getElementById('empty-state');

    loadingEl.style.display = 'flex';
    errorEl.style.display   = 'none';
    tableEl.style.display   = 'none';
    emptyEl.style.display   = 'none';

    try {
        const { data, error } = await supabaseClient
            .from('gambling_urls')
            .select('*')
            .eq('is_illegal', true)
            .order('collected_at', { ascending: false });

        if (error) throw error;

        allSites = data || [];
        filteredSites = [...allSites];

        updateStatistics(allSites);
        renderTable(filteredSites);

        loadingEl.style.display = 'none';

    } catch (err) {
        console.error('Failed to load data:', err);
        loadingEl.style.display = 'none';
        document.getElementById('error-msg').textContent = `Failed to load data: ${err.message}`;
        errorEl.style.display = 'flex';
    }
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
            ? `<span class="keyword-chip">${site.keyword_used}</span>`
            : '<span style="color:var(--text-3)">—</span>';

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <img class="favicon"
                     src="https://www.google.com/s2/favicons?sz=32&domain=${domain}"
                     alt=""
                     onerror="this.outerHTML='<span class=\'favicon-placeholder\'>🌐</span>'">
            </td>
            <td class="url-cell">
                <a href="${site.url}" target="_blank" rel="noopener noreferrer" class="url-link"
                   title="${site.url}">
                    ${truncateUrl(site.url, 55)}
                </a>
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
            (s.keyword_used && s.keyword_used.toLowerCase().includes(q))
          )
        : [...allSites];
    renderTable(filteredSites);
}

function showDetail(index) {
    const site = filteredSites[index];
    const modal = document.getElementById('detail-modal');
    const body  = document.getElementById('modal-body');

    const confClass = getConfidenceClass(site.gemini_confidence);
    const confVal   = (site.gemini_confidence || 0).toFixed(2);

    const keywordTags = (site.detected_keywords && site.detected_keywords.length > 0)
        ? site.detected_keywords.map(k => `<span class="keyword-tag">${k}</span>`).join('')
        : '<span style="color:var(--text-3)">None detected</span>';

    const screenshotHTML = site.screenshot_url
        ? `<div class="modal-section">
               <div class="modal-label">Screenshot</div>
               <div class="modal-value"><img src="${site.screenshot_url}" alt="Screenshot" class="screenshot-img"></div>
           </div><hr class="modal-divider">`
        : '';

    body.innerHTML = `
        <div class="modal-section">
            <div class="modal-label">URL</div>
            <div class="modal-value">
                <a href="${site.url}" target="_blank" rel="noopener noreferrer" class="url-link">${site.url}</a>
            </div>
        </div>
        <hr class="modal-divider">
        ${screenshotHTML}
        <div class="modal-section">
            <div class="modal-label">Search Keyword</div>
            <div class="modal-value">${site.keyword_used || '—'}</div>
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
            <div class="modal-value">${site.gemini_reason || 'No reasoning provided.'}</div>
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

function extractDomain(url) {
    try { return new URL(url).hostname; }
    catch { return ''; }
}

function truncateUrl(url, max) {
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
