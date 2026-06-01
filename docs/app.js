// Initialize Supabase client
const SUPABASE_URL = 'https://pimnyvbggbobuvnyezga.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBpbW55dmJnZ2JvYnV2bnllemdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAyMjc4MzMsImV4cCI6MjA5NTgwMzgzM30.UTTzmrEH6k_FVNgnbElR8ubQCJbbke2FrRIvc3a1mCw';

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Global variables
let allSites = [];
let filteredSites = [];

// Load data on page load
document.addEventListener('DOMContentLoaded', () => {
    loadData();

    // Search input event listener
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterSites(e.target.value);
    });
});

// Data load function
async function loadData() {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const tableEl = document.getElementById('sites-table');

    // Show loading indicator
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    tableEl.style.display = 'none';

    try {
        // Fetch illegal site data from Supabase
        const { data, error } = await supabaseClient
            .from('gambling_urls')
            .select('*')
            .eq('is_illegal', true)
            .order('collected_at', { ascending: false });

        if (error) {
            throw error;
        }

        // Store data
        allSites = data || [];
        filteredSites = [...allSites];

        // Update statistics
        updateStatistics(allSites);

        // Render table
        renderTable(filteredSites);

        // Hide loading, show table
        loadingEl.style.display = 'none';
        tableEl.style.display = 'table';

    } catch (error) {
        console.error('Failed to load data:', error);
        loadingEl.style.display = 'none';
        errorEl.textContent = `Failed to load data: ${error.message}`;
        errorEl.style.display = 'block';
    }
}

// Statistics update function
function updateStatistics(sites) {
    const totalCount = sites.length;
    const avgConfidence = sites.length > 0
        ? (sites.reduce((sum, site) => sum + (site.gemini_confidence || 0), 0) / sites.length).toFixed(2)
        : '0.00';

    const lastUpdate = sites.length > 0 && sites[0].collected_at
        ? formatDate(new Date(sites[0].collected_at))
        : '-';

    document.getElementById('total-count').textContent = totalCount;
    document.getElementById('avg-confidence').textContent = avgConfidence;
    document.getElementById('last-update').textContent = lastUpdate;
}

// Table render function
function renderTable(sites) {
    const tbody = document.getElementById('sites-tbody');
    tbody.innerHTML = '';

    if (sites.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #999;">No results found</td></tr>';
        return;
    }

    sites.forEach((site, index) => {
        const tr = document.createElement('tr');

        // Extract domain for favicon
        const domain = extractDomain(site.url);

        // Determine confidence badge class
        const confidenceClass = getConfidenceClass(site.gemini_confidence);

        tr.innerHTML = `
            <td>
                <img class="favicon" src="https://www.google.com/s2/favicons?domain=${domain}"
                     alt="favicon" onerror="this.src='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='">
            </td>
            <td>
                <a href="${site.url}" target="_blank" rel="noopener noreferrer" class="url-link">
                    ${truncateUrl(site.url, 60)}
                </a>
            </td>
            <td>${site.keyword_used || '-'}</td>
            <td>
                <span class="confidence-badge ${confidenceClass}">
                    ${(site.gemini_confidence || 0).toFixed(2)}
                </span>
            </td>
            <td class="date-text">${formatDateTime(site.collected_at)}</td>
            <td>
                <button class="detail-btn" onclick="showDetail(${index})">Details</button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// Site filter function
function filterSites(searchTerm) {
    const term = searchTerm.toLowerCase().trim();

    if (!term) {
        filteredSites = [...allSites];
    } else {
        filteredSites = allSites.filter(site =>
            site.url.toLowerCase().includes(term) ||
            (site.keyword_used && site.keyword_used.toLowerCase().includes(term))
        );
    }

    renderTable(filteredSites);
}

// Show detail modal
function showDetail(index) {
    const site = filteredSites[index];
    const modal = document.getElementById('detail-modal');
    const modalBody = document.getElementById('modal-body');

    // Build detected keyword tags
    let keywordTags = '';
    if (site.detected_keywords && Array.isArray(site.detected_keywords) && site.detected_keywords.length > 0) {
        keywordTags = site.detected_keywords
            .map(keyword => `<span class="keyword-tag">${keyword}</span>`)
            .join('');
    } else {
        keywordTags = '<span style="color: #999;">None</span>';
    }

    // Build screenshot section
    let screenshotSection = '';
    if (site.screenshot_url) {
        screenshotSection = `
            <div class="modal-section">
                <div class="modal-label">Screenshot</div>
                <div class="modal-value">
                    <img src="${site.screenshot_url}" alt="Screenshot" class="screenshot-img">
                </div>
            </div>
        `;
    }

    modalBody.innerHTML = `
        <div class="modal-section">
            <div class="modal-label">URL</div>
            <div class="modal-value">
                <a href="${site.url}" target="_blank" rel="noopener noreferrer" class="url-link">${site.url}</a>
            </div>
        </div>

        ${screenshotSection}

        <div class="modal-section">
            <div class="modal-label">Search Keyword</div>
            <div class="modal-value">${site.keyword_used || '-'}</div>
        </div>

        <div class="modal-section">
            <div class="modal-label">Confidence</div>
            <div class="modal-value">
                <span class="confidence-badge ${getConfidenceClass(site.gemini_confidence)}">
                    ${(site.gemini_confidence || 0).toFixed(2)}
                </span>
            </div>
        </div>

        <div class="modal-section">
            <div class="modal-label">Collected At</div>
            <div class="modal-value">${formatDateTime(site.collected_at)}</div>
        </div>

        <div class="modal-section">
            <div class="modal-label">AI Reasoning</div>
            <div class="modal-value">${site.gemini_reason || 'No information'}</div>
        </div>

        <div class="modal-section">
            <div class="modal-label">Detected Keywords</div>
            <div class="modal-value">${keywordTags}</div>
        </div>
    `;

    modal.style.display = 'block';
}

// Close modal
function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// Close modal on outside click
window.onclick = function(event) {
    const modal = document.getElementById('detail-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Utility functions

// Extract domain from URL
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch (e) {
        return '';
    }
}

// Truncate URL
function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// Return CSS class based on confidence score
function getConfidenceClass(confidence) {
    if (confidence >= 0.9) return 'confidence-high';
    if (confidence >= 0.7) return 'confidence-medium';
    return 'confidence-low';
}

// Format date (short form)
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format date and time
function formatDateTime(dateString) {
    if (!dateString) return '-';

    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${year}-${month}-${day} ${hours}:${minutes}`;
}
