// Logs view: a time-ordered feed of detections built from allSites (loaded in app.js).
// The public anon key can only read sites flagged illegal, so that is all the log shows.

const LOG_PAGE_SIZE = 50;

let logSource = 'all';
let logCategory = 'all';
let logLimit = LOG_PAGE_SIZE;
let logEntries = [];

document.addEventListener('DOMContentLoaded', () => {
    bindLogPicker('log-source-picker', 'source', value => { logSource = value; });
    bindLogPicker('log-category-picker', 'category', value => { logCategory = value; });
    document.getElementById('log-more').addEventListener('click', () => {
        logLimit += LOG_PAGE_SIZE;
        renderLogs();
    });
});

function bindLogPicker(id, key, set) {
    const buttons = document.querySelectorAll(`#${id} button`);
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            set(btn.dataset[key]);
            buttons.forEach(b => b.classList.toggle('active', b === btn));
            logLimit = LOG_PAGE_SIZE;
            renderLogs();
        });
    });
}

function renderLogs() {
    const view = document.getElementById('view-logs');
    if (!view || view.hidden) return;

    logEntries = allSites
        .filter(s => s.collected_at)
        .filter(s => logSource === 'all' || (logSource === 'report') === isManualReport(s))
        .filter(s => logCategory === 'all' || s.category === logCategory)
        .sort((a, b) => new Date(b.collected_at) - new Date(a.collected_at));

    const list = document.getElementById('log-list');
    const shown = logEntries.slice(0, logLimit);

    if (shown.length === 0) {
        list.innerHTML = `
            <div class="state-box">
                <span class="state-icon">📄</span>
                <span class="state-title">No log entries</span>
                <span class="state-desc">Try a different filter or refresh the data.</span>
            </div>`;
    } else {
        let html = '';
        let currentDay = '';
        shown.forEach((site, i) => {
            const day = formatDate(site.collected_at);
            if (day !== currentDay) {
                currentDay = day;
                html += `<div class="log-day">${escapeHtml(dayHeading(site.collected_at))}</div>`;
            }
            html += logRow(site, i);
        });
        list.innerHTML = html;
        list.querySelectorAll('.log-row').forEach(row => {
            row.addEventListener('click', () => showSiteDetail(logEntries[Number(row.dataset.i)]));
        });
    }

    document.getElementById('log-count').textContent =
        `Showing ${shown.length} of ${logEntries.length} entries`;
    document.getElementById('log-more').hidden = shown.length >= logEntries.length;
}

function logRow(site, i) {
    const report = isManualReport(site);
    const d = new Date(site.collected_at);
    const time = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    const conf = site.gemini_confidence || 0;
    const domain = extractDomain(site.url) || site.url;

    const action = report
        ? 'User report confirmed as illegal'
        : `Crawler found it searching <span class="keyword-chip">${escapeHtml(site.keyword_used || '—')}</span>`;
    const typeChip = site.category === 'promotion'
        ? '<span class="log-tag promo">Promotion page</span>'
        : site.category === 'operator'
            ? '<span class="log-tag operator">Gambling site</span>'
            : '';

    return `
        <button type="button" class="log-row" data-i="${i}" title="Show details">
            <span class="log-time">${time}</span>
            <span class="log-icon ${report ? 'report' : 'crawler'}">${report ? '🙋' : '🤖'}</span>
            <span class="log-main">
                <span class="log-domain">${escapeHtml(domain)} ${typeChip}</span>
                <span class="log-action">${action}</span>
            </span>
            <span class="confidence-badge ${getConfidenceClass(conf)}">${conf.toFixed(2)}</span>
        </button>`;
}

function dayHeading(dateStr) {
    const day = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
    if (day.toDateString() === today.toDateString()) return `Today · ${formatDate(dateStr)}`;
    if (day.toDateString() === yesterday.toDateString()) return `Yesterday · ${formatDate(dateStr)}`;
    return formatDate(dateStr);
}
