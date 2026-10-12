// Analytics view: charts built from the rows app.js already loaded (allSites).
// Charts are plain SVG/HTML so the dashboard stays dependency-free.

const MANUAL_REPORT_KEYWORD = 'manual report';
const DAY_MS = 24 * 60 * 60 * 1000;

let analyticsRange = getSetting('defaultRange');

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('#range-picker button').forEach(btn => {
        btn.addEventListener('click', () => {
            analyticsRange = btn.dataset.range;
            document.querySelectorAll('#range-picker button')
                .forEach(b => b.classList.toggle('active', b === btn));
            renderAnalytics();
        });
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(renderAnalytics, 150);
    });
});

function renderAnalytics() {
    const view = document.getElementById('view-analytics');
    if (!view || view.hidden) return;

    document.querySelectorAll('#range-picker button')
        .forEach(b => b.classList.toggle('active', b.dataset.range === analyticsRange));

    const { sites, start, end, prevSites } = sitesInRange(allSites, analyticsRange);

    renderAnalyticsStats(sites, prevSites, start, end);
    renderTimeline(sites, start, end);
    renderBarList('an-category', countBy(sites, s => categoryName(s.category)), {
        total: sites.length,
        order: ['Gambling site', 'Promotion page', 'Unclassified'],
    });
    renderBarList('an-source', countBy(sites, s => isManualReport(s) ? 'User report' : 'Crawler'), {
        total: sites.length,
        order: ['Crawler', 'User report'],
    });
    renderBarList('an-keywords',
        countBy(sites.filter(s => s.keyword_used && !isManualReport(s)), s => s.keyword_used), {
            limit: 8,
            onClick: label => showSitesFor(label),
        });
    renderBarList('an-detected', countDetectedKeywords(sites), {
        limit: 8,
        onClick: label => showSitesFor(label),
    });
    renderConfidence(sites);
    renderBarList('an-tld', countBy(sites, s => topLevelDomain(s.url)), {
        limit: 8,
        total: sites.length,
    });
}

// ── Data helpers ─────────────────────────────────────────────

function sitesInRange(all, range) {
    const end = startOfDay(new Date());
    const dated = all.filter(s => s.collected_at);

    if (range === 'all') {
        const times = dated.map(s => new Date(s.collected_at).getTime());
        const start = times.length ? startOfDay(new Date(Math.min(...times))) : end;
        return { sites: dated, start, end, prevSites: null };
    }

    const days = Number(range);
    const start = new Date(end.getTime() - (days - 1) * DAY_MS);
    const prevStart = new Date(start.getTime() - days * DAY_MS);
    const inWindow = (s, from, to) => {
        const t = new Date(s.collected_at).getTime();
        return t >= from.getTime() && t < to.getTime();
    };
    return {
        sites: dated.filter(s => inWindow(s, start, new Date(end.getTime() + DAY_MS))),
        prevSites: dated.filter(s => inWindow(s, prevStart, start)),
        start,
        end,
    };
}

function startOfDay(d) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function isManualReport(site) {
    return site.keyword_used === MANUAL_REPORT_KEYWORD;
}

function categoryName(category) {
    if (category === 'operator') return 'Gambling site';
    if (category === 'promotion') return 'Promotion page';
    return 'Unclassified';
}

function topLevelDomain(url) {
    const host = extractDomain(url);
    if (!host) return 'Unknown';
    if (/^[\d.]+$/.test(host)) return 'IP address';
    const parts = host.split('.');
    return '.' + parts[parts.length - 1];
}

// Returns [[label, count], ...] sorted by count, largest first
function countBy(items, keyFn) {
    const counts = new Map();
    items.forEach(item => {
        const key = keyFn(item);
        counts.set(key, (counts.get(key) || 0) + 1);
    });
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

// Counts each keyword once per site, merging case differences
function countDetectedKeywords(sites) {
    const counts = new Map();
    sites.forEach(site => {
        if (!Array.isArray(site.detected_keywords)) return;
        const seen = new Set();
        site.detected_keywords.forEach(raw => {
            const label = String(raw).trim();
            const key = label.toLowerCase();
            if (!label || seen.has(key)) return;
            seen.add(key);
            const entry = counts.get(key) || [label, 0];
            entry[1] += 1;
            counts.set(key, entry);
        });
    });
    return [...counts.values()].sort((a, b) => b[1] - a[1]);
}

// ── Stat tiles ───────────────────────────────────────────────

function renderAnalyticsStats(sites, prevSites, start, end) {
    const total = sites.length;
    const days = Math.round((end - start) / DAY_MS) + 1;
    const perDay = total / Math.max(days, 1);
    const domains = new Set(sites.map(s => extractDomain(s.url)).filter(Boolean)).size;
    const promotion = sites.filter(s => s.category === 'promotion').length;
    const reports = sites.filter(isManualReport).length;

    let delta = '';
    if (prevSites) {
        const diff = total - prevSites.length;
        const cls = diff > 0 ? 'up' : diff < 0 ? 'down' : 'flat';
        const sign = diff > 0 ? '+' : '';
        delta = `<span class="stat-trend ${cls}" title="Compared with the previous ${days} days">${sign}${diff} vs prev.</span>`;
    }

    const tiles = [
        { icon: '🚨', tone: 'danger',  label: 'Detections', value: total, delta },
        { icon: '📈', tone: 'primary', label: 'Per day (avg.)', value: perDay.toFixed(1) },
        { icon: '🌐', tone: 'success', label: 'Unique domains', value: domains },
        { icon: '📣', tone: 'warning', label: 'Promotion pages', value: promotion },
        { icon: '🙋', tone: 'primary', label: 'User reports', value: reports },
    ];

    document.getElementById('an-stats').innerHTML = tiles.map(t => `
        <div class="stat-card">
            <div class="stat-card-top">
                <div class="stat-icon ${t.tone}">${t.icon}</div>
                ${t.delta || ''}
            </div>
            <div class="stat-label">${t.label}</div>
            <div class="stat-value">${t.value}</div>
        </div>
    `).join('');
}

// ── Timeline ─────────────────────────────────────────────────

function renderTimeline(sites, start, end) {
    const spanDays = Math.round((end - start) / DAY_MS) + 1;
    // Long ranges are grouped by week so the columns stay readable
    const step = spanDays > 120 ? 7 : 1;
    const bins = [];
    for (let t = start.getTime(); t <= end.getTime(); t += step * DAY_MS) {
        bins.push({ from: new Date(t), value: 0 });
    }
    sites.forEach(site => {
        const day = startOfDay(new Date(site.collected_at)).getTime();
        const i = Math.floor((day - start.getTime()) / (step * DAY_MS));
        if (bins[i]) bins[i].value += 1;
    });

    bins.forEach(bin => {
        bin.label = shortDate(bin.from);
        bin.tip = step === 1 ? formatDate(bin.from) : `Week of ${formatDate(bin.from)}`;
    });

    document.getElementById('an-timeline-sub').textContent =
        step === 1 ? 'Sites detected per day' : 'Sites detected per week';
    drawColumns('an-timeline', bins, { height: 220, unit: 'sites' });
}

function shortDate(d) {
    return `${d.getMonth() + 1}/${d.getDate()}`;
}

// ── Confidence histogram ─────────────────────────────────────

function renderConfidence(sites) {
    const edges = [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001];
    const labels = ['<0.5', '0.5', '0.6', '0.7', '0.8', '0.9+'];
    const bins = labels.map((label, i) => ({
        label,
        value: 0,
        tip: i === 0 ? 'Below 0.5' : i === labels.length - 1 ? '0.9 – 1.0'
            : `${edges[i].toFixed(1)} – ${(edges[i + 1] - 0.01).toFixed(2)}`,
    }));
    sites.forEach(site => {
        const c = site.gemini_confidence || 0;
        const i = edges.findIndex((e, k) => c >= e && c < edges[k + 1]);
        if (i >= 0) bins[i].value += 1;
    });
    drawColumns('an-confidence', bins, { height: 180, unit: 'sites', labelEvery: 1 });
}

// ── Chart primitives ─────────────────────────────────────────

// Vertical column chart in SVG. bins: [{label, value, tip}]
function drawColumns(containerId, bins, { height = 200, unit = '', labelEvery } = {}) {
    const el = document.getElementById(containerId);
    const width = Math.max(el.clientWidth, 260);
    const pad = { top: 18, right: 8, bottom: 26, left: 34 };
    const plotW = width - pad.left - pad.right;
    const plotH = height - pad.top - pad.bottom;

    const max = Math.max(...bins.map(b => b.value), 0);
    if (max === 0) {
        el.innerHTML = '<div class="chart-empty">No detections in this period</div>';
        return;
    }

    const ticks = niceTicks(max);
    const top = ticks[ticks.length - 1];
    const y = v => pad.top + plotH - (v / top) * plotH;
    const slot = plotW / bins.length;
    const barW = Math.max(2, Math.min(24, slot * 0.7));
    const every = labelEvery || Math.ceil(bins.length / Math.max(1, Math.floor(plotW / 48)));
    const peak = bins.reduce((best, b, i) => (b.value > bins[best].value ? i : best), 0);

    let svg = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img">`;

    ticks.forEach(t => {
        svg += `<line class="grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(t)}" y2="${y(t)}"/>`;
        svg += `<text class="axis" x="${pad.left - 8}" y="${y(t) + 4}" text-anchor="end">${t}</text>`;
    });

    bins.forEach((b, i) => {
        const cx = pad.left + slot * i + slot / 2;
        if (b.value > 0) {
            svg += `<path class="bar" d="${roundedTopBar(cx - barW / 2, y(b.value), barW, y(0) - y(b.value))}"/>`;
        }
        if (i % every === 0) {
            svg += `<text class="axis" x="${cx}" y="${height - 8}" text-anchor="middle">${escapeHtml(b.label)}</text>`;
        }
        if (i === peak) {
            svg += `<text class="peak" x="${cx}" y="${y(b.value) - 6}" text-anchor="middle">${b.value}</text>`;
        }
        // Full-height hit target, wider than the bar itself
        svg += `<rect class="hit" x="${pad.left + slot * i}" y="${pad.top}" width="${slot}" height="${plotH}"
                      data-i="${i}" tabindex="0"/>`;
    });

    svg += `<line class="baseline" x1="${pad.left}" x2="${width - pad.right}" y1="${y(0)}" y2="${y(0)}"/>`;
    svg += '</svg>';
    el.innerHTML = svg;

    el.querySelectorAll('.hit').forEach(hit => {
        const b = bins[Number(hit.dataset.i)];
        const show = (evt) => {
            hit.classList.add('hover');
            showTooltip(evt, String(b.value), `${b.tip} · ${unit}`);
        };
        hit.addEventListener('pointermove', show);
        hit.addEventListener('focus', show);
        hit.addEventListener('pointerleave', () => { hit.classList.remove('hover'); hideTooltip(); });
        hit.addEventListener('blur', () => { hit.classList.remove('hover'); hideTooltip(); });
    });
}

// Bar path with 4px rounded data end and a square baseline
function roundedTopBar(x, yTop, w, h) {
    const r = Math.min(4, w / 2, h);
    return `M${x},${yTop + h} V${yTop + r} Q${x},${yTop} ${x + r},${yTop}
            H${x + w - r} Q${x + w},${yTop} ${x + w},${yTop + r} V${yTop + h} Z`;
}

function niceTicks(max) {
    const rough = max / 4;
    const mag = Math.pow(10, Math.floor(Math.log10(Math.max(rough, 1))));
    const step = [1, 2, 5, 10].map(m => m * mag).find(s => s >= rough) || mag;
    const ticks = [];
    for (let t = 0; t <= max + step - 1 && ticks.length < 8; t += step) ticks.push(t);
    if (ticks[ticks.length - 1] < max) ticks.push(ticks[ticks.length - 1] + step);
    return ticks;
}

// Horizontal bar list in HTML. Labels and values are always visible (no hover needed).
function renderBarList(containerId, entries, { limit, total, order, onClick } = {}) {
    const el = document.getElementById(containerId);
    if (order) {
        entries = [...entries].sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
    }
    if (limit && entries.length > limit) {
        const rest = entries.slice(limit).reduce((s, e) => s + e[1], 0);
        entries = entries.slice(0, limit);
        if (total) entries.push(['Other', rest]);
    }
    if (entries.length === 0) {
        el.innerHTML = '<div class="chart-empty">No data in this period</div>';
        return;
    }

    const max = Math.max(...entries.map(e => e[1]));
    el.innerHTML = `<div class="bar-list">${entries.map(([label, count]) => {
        const pct = total ? ` <span class="bar-pct">${Math.round((count / total) * 100)}%</span>` : '';
        const clickable = onClick && label !== 'Other';
        const tag = clickable ? 'button' : 'div';
        return `
            <${tag} class="bar-row${clickable ? ' clickable' : ''}" ${clickable ? `type="button" data-label="${escapeHtml(label)}"` : ''}>
                <span class="bar-label" title="${escapeHtml(label)}">${escapeHtml(label)}</span>
                <span class="bar-track"><span class="bar-fill" style="width:${(count / max) * 100}%"></span></span>
                <span class="bar-value">${count}${pct}</span>
            </${tag}>`;
    }).join('')}</div>`;

    if (onClick) {
        el.querySelectorAll('.bar-row.clickable').forEach(row => {
            row.addEventListener('click', () => onClick(row.dataset.label));
        });
    }
}

// ── Tooltip ──────────────────────────────────────────────────

function showTooltip(evt, value, label) {
    const tip = document.getElementById('chart-tooltip');
    tip.replaceChildren();
    const strong = document.createElement('strong');
    strong.textContent = value;
    const span = document.createElement('span');
    span.textContent = label;
    tip.append(strong, span);
    tip.hidden = false;

    let x = evt.clientX, yPos = evt.clientY;
    if (x === undefined) {
        const r = evt.target.getBoundingClientRect();
        x = r.left + r.width / 2;
        yPos = r.top;
    }
    const w = tip.offsetWidth;
    tip.style.left = `${Math.min(window.innerWidth - w - 8, Math.max(8, x - w / 2))}px`;
    tip.style.top = `${yPos - tip.offsetHeight - 12}px`;
}

function hideTooltip() {
    document.getElementById('chart-tooltip').hidden = true;
}
