// Settings view: per-viewer dashboard preferences kept in this browser's localStorage.
// Loaded before app.js so the other views can read the saved values on startup.

const SETTINGS_KEY = 'gamblescan-dashboard-settings';

const DEFAULT_SETTINGS = {
    defaultView: 'sites',      // sites | analytics | logs
    defaultRange: '30',        // analytics period: 7 | 30 | 90 | all
    minConfidence: '0',        // hide sites below this AI confidence
    showPromotion: true,       // include pages that promote gambling sites
    autoRefresh: '0',          // minutes between automatic reloads, 0 = off
};

let dashboardSettings = loadSettings();
let autoRefreshTimer = null;
let lastLoadedAt = null;

function loadSettings() {
    try {
        const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
        return { ...DEFAULT_SETTINGS, ...saved };
    } catch {
        return { ...DEFAULT_SETTINGS };
    }
}

function saveSettings() {
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(dashboardSettings));
    } catch {
        // Storage can be blocked (private window); settings then last for this visit only
    }
}

function getSetting(key) {
    return dashboardSettings[key];
}

// Applied to every view: the table, analytics, and logs all see the same rows
function applySiteSettings(sites) {
    const min = Number(dashboardSettings.minConfidence);
    return sites.filter(s =>
        (s.gemini_confidence || 0) >= min &&
        (dashboardSettings.showPromotion || s.category !== 'promotion')
    );
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#view-settings .segmented').forEach(group => {
        group.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', () => updateSetting(group.dataset.setting, btn.dataset.value));
        });
    });
    document.getElementById('set-show-promotion').addEventListener('change', (e) => {
        updateSetting('showPromotion', e.target.checked);
    });
    document.getElementById('settings-reset').addEventListener('click', () => {
        dashboardSettings = { ...DEFAULT_SETTINGS };
        saveSettings();
        onSettingsChanged();
    });
    syncSettingsForm();
    scheduleAutoRefresh();
});

function updateSetting(key, value) {
    dashboardSettings[key] = value;
    saveSettings();
    onSettingsChanged(key);
}

function onSettingsChanged(key) {
    syncSettingsForm();
    if (!key || key === 'autoRefresh') scheduleAutoRefresh();
    if (!key || key === 'defaultRange') analyticsRange = dashboardSettings.defaultRange;
    if (!key || key === 'minConfidence' || key === 'showPromotion') reapplySiteSettings();
    showSavedNote();
}

// Mark the saved choice in each control
function syncSettingsForm() {
    document.querySelectorAll('#view-settings .segmented').forEach(group => {
        const current = String(dashboardSettings[group.dataset.setting]);
        group.querySelectorAll('button').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.value === current);
        });
    });
    document.getElementById('set-show-promotion').checked = dashboardSettings.showPromotion;
    renderSettingsInfo();
}

function scheduleAutoRefresh() {
    clearInterval(autoRefreshTimer);
    const minutes = Number(dashboardSettings.autoRefresh);
    if (minutes > 0) {
        autoRefreshTimer = setInterval(() => loadData({ silent: true }), minutes * 60 * 1000);
    }
}

let savedNoteTimer;
function showSavedNote() {
    const note = document.getElementById('settings-saved');
    note.hidden = false;
    clearTimeout(savedNoteTimer);
    savedNoteTimer = setTimeout(() => { note.hidden = true; }, 1600);
}

// "About this data" panel
function renderSettingsInfo() {
    const el = document.getElementById('settings-info');
    if (!el) return;
    const total = typeof rawSites !== 'undefined' ? rawSites.length : 0;
    const shown = typeof allSites !== 'undefined' ? allSites.length : 0;
    const rows = [
        ['Data source', extractDomain(SUPABASE_URL)],
        ['Records loaded', `${total} illegal sites`],
        ['Shown with your filters', `${shown} sites`],
        ['Last refreshed', lastLoadedAt ? formatDateTime(lastLoadedAt) : '—'],
    ];
    el.innerHTML = rows.map(([label, value]) => `
        <div class="info-row">
            <span class="info-label">${label}</span>
            <span class="info-value">${escapeHtml(value)}</span>
        </div>`).join('');
}
