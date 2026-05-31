// Supabase 클라이언트 초기화
const SUPABASE_URL = 'https://ezpnbmglzbxujveexmvm.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV6cG5ibWdsemJ4dWp2ZWV4bXZtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ0Nzg5MjcsImV4cCI6MjA4MDA1NDkyN30.ngUP3-o0a3M2wG_8IfDZVLpQEbTCjh5P2HO2ncnymhY';

const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// 전역 변수
let allSites = [];
let filteredSites = [];

// 페이지 로드 시 데이터 불러오기
document.addEventListener('DOMContentLoaded', () => {
    loadData();
    
    // 검색 입력 이벤트 리스너
    document.getElementById('search-input').addEventListener('input', (e) => {
        filterSites(e.target.value);
    });
});

// 데이터 로드 함수
async function loadData() {
    const loadingEl = document.getElementById('loading');
    const errorEl = document.getElementById('error');
    const tableEl = document.getElementById('sites-table');
    
    // 로딩 표시
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    tableEl.style.display = 'none';
    
    try {
        // Supabase에서 불법 사이트 데이터 조회
        const { data, error } = await supabaseClient
            .from('gambling_urls')
            .select('*')
            .eq('is_illegal', true)
            .order('collected_at', { ascending: false });
        
        if (error) {
            throw error;
        }
        
        // 데이터 저장
        allSites = data || [];
        filteredSites = [...allSites];
        
        // 통계 업데이트
        updateStatistics(allSites);
        
        // 테이블 렌더링
        renderTable(filteredSites);
        
        // 로딩 숨기고 테이블 표시
        loadingEl.style.display = 'none';
        tableEl.style.display = 'table';
        
    } catch (error) {
        console.error('데이터 로드 실패:', error);
        loadingEl.style.display = 'none';
        errorEl.textContent = `데이터를 불러오는데 실패했습니다: ${error.message}`;
        errorEl.style.display = 'block';
    }
}

// 통계 업데이트 함수
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

// 테이블 렌더링 함수
function renderTable(sites) {
    const tbody = document.getElementById('sites-tbody');
    tbody.innerHTML = '';
    
    if (sites.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #999;">검색 결과가 없습니다</td></tr>';
        return;
    }
    
    sites.forEach((site, index) => {
        const tr = document.createElement('tr');
        
        // 도메인 추출 (파비콘용)
        const domain = extractDomain(site.url);
        
        // 신뢰도 클래스 결정
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
                <button class="detail-btn" onclick="showDetail(${index})">상세보기</button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

// 사이트 필터링 함수
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

// 상세 정보 모달 표시
function showDetail(index) {
    const site = filteredSites[index];
    const modal = document.getElementById('detail-modal');
    const modalBody = document.getElementById('modal-body');
    
    // 탐지된 키워드 태그 생성
    let keywordTags = '';
    if (site.detected_keywords && Array.isArray(site.detected_keywords) && site.detected_keywords.length > 0) {
        keywordTags = site.detected_keywords
            .map(keyword => `<span class="keyword-tag">${keyword}</span>`)
            .join('');
    } else {
        keywordTags = '<span style="color: #999;">없음</span>';
    }

    // 스크린샷 섹션 생성
    let screenshotSection = '';
    if (site.screenshot_url) {
        screenshotSection = `
            <div class="modal-section">
                <div class="modal-label">스크린샷</div>
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
            <div class="modal-label">검색 키워드</div>
            <div class="modal-value">${site.keyword_used || '-'}</div>
        </div>
        
        <div class="modal-section">
            <div class="modal-label">신뢰도</div>
            <div class="modal-value">
                <span class="confidence-badge ${getConfidenceClass(site.gemini_confidence)}">
                    ${(site.gemini_confidence || 0).toFixed(2)}
                </span>
            </div>
        </div>
        
        <div class="modal-section">
            <div class="modal-label">수집 일시</div>
            <div class="modal-value">${formatDateTime(site.collected_at)}</div>
        </div>
        
        <div class="modal-section">
            <div class="modal-label">AI 판단 이유</div>
            <div class="modal-value">${site.gemini_reason || '정보 없음'}</div>
        </div>
        
        <div class="modal-section">
            <div class="modal-label">탐지된 키워드</div>
            <div class="modal-value">${keywordTags}</div>
        </div>
    `;
    
    modal.style.display = 'block';
}

// 모달 닫기
function closeModal() {
    document.getElementById('detail-modal').style.display = 'none';
}

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modal = document.getElementById('detail-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// 유틸리티 함수들

// 도메인 추출
function extractDomain(url) {
    try {
        const urlObj = new URL(url);
        return urlObj.hostname;
    } catch (e) {
        return '';
    }
}

// URL 축약
function truncateUrl(url, maxLength) {
    if (url.length <= maxLength) return url;
    return url.substring(0, maxLength) + '...';
}

// 신뢰도에 따른 클래스 반환
function getConfidenceClass(confidence) {
    if (confidence >= 0.9) return 'confidence-high';
    if (confidence >= 0.7) return 'confidence-medium';
    return 'confidence-low';
}

// 날짜 포맷팅 (간단한 형식)
function formatDate(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// 날짜/시간 포맷팅
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

