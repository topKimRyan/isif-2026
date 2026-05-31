document.addEventListener('DOMContentLoaded', async () => {
    const params = new URLSearchParams(window.location.search);
    const reportId = params.get('id') || sessionStorage.getItem('report_id');

    if (!reportId) {
        alert('정보가 없습니다. 메인 페이지로 돌아갑니다.');
        sessionStorage.removeItem('report_id'); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    if (!supabaseClient) {
        alert('데이터베이스 연결에 실패했습니다.');
        sessionStorage.removeItem('report_id'); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    try {
        const { data, error } = await supabaseClient
            .from('report_requests')
            .select('url, is_illegal, reason, detected_keywords')
            .eq('id', reportId)
            .single();

        if (error || !data) {
            throw error || new Error('Report data not found.');
        }
        
        const { url, is_illegal, reason, detected_keywords: keywords } = data;

        const dynamicContent = document.getElementById('dynamic-content');
        const dynamicButtons = document.getElementById('dynamic-buttons');
        const backButton = document.getElementById('back-button-dynamic');

        let contentHTML = '';
        let buttonsHTML = '';
        
        if (is_illegal) {
            contentHTML = `
                <h1>아래 내용이 정확한가요?</h1>
                <div class="result-card minimal-card">
                    <div class="result-header">
                        <div class="result-icon illegal"><i class="fi fi-sr-cross-circle"></i></div>
                        <div class="result-title"><h2>불법 의심 사이트</h2></div>
                    </div>
                </div>
                <form id="confirmation-form">
                    <label for="site-url-confirm">사이트 URL</label>
                    <input type="url" id="site-url-confirm" name="site-url" value="${url}" readonly>
                    <label for="reason-confirm">사유</label>
                    <textarea id="reason-confirm" name="reason" rows="4" readonly>${reason || ''}</textarea>
                    ${(keywords && keywords.length > 0) ? `<h3>탐지된 키워드</h3><ul class="keyword-list">${keywords.map(k => `<li>${k}</li>`).join('')}</ul>` : ''}
                </form>
            `;
            buttonsHTML = `
                <div class="confirm-buttons-stacked">
                    <button type="button" class="btn-primary" id="report-button">신고하기</button>
                    <button type="button" class="btn-secondary" id="edit-button">수정하기</button>
                    <button type="button" class="btn-text-only" id="cancel-confirm-button">취소하기</button>
                </div>
            `;
        } else {
            contentHTML = `
                <h1>불법 사이트 검증에<br>실패했습니다</h1>
                <div class="result-card minimal-card">
                    <div class="result-header">
                        <div class="result-icon legal"><i class="fi fi-sr-check-circle"></i></div>
                        <div class="result-title"><h2>정상 사이트</h2></div>
                    </div>
                </div>
                <form id="confirmation-form">
                    <label for="site-url-confirm">사이트 URL</label>
                    <input type="url" id="site-url-confirm" name="site-url" value="${url}" readonly>
                    <label for="reason-confirm">사유</label>
                    <textarea id="reason-confirm" name="reason" rows="4" readonly>${reason || ''}</textarea>
                </form>
            `;
            buttonsHTML = `<button type="button" class="btn-primary" id="exit-button">종료하기</button>`;
        }

        dynamicContent.innerHTML = contentHTML;
        dynamicButtons.innerHTML = buttonsHTML;

        backButton.addEventListener('click', (e) => { 
            e.preventDefault(); 
            window.location.href = `report.html?url=${encodeURIComponent(url)}`; 
        });

        // Event Listeners for buttons
        const reportButton = document.getElementById('report-button');
        if (reportButton) {
            reportButton.addEventListener('click', async () => {
                try {
                    const { error } = await supabaseClient
                        .from('report_requests')
                        .update({ status: 'confirmed' })
                        .eq('id', reportId);

                    if (error) throw error;
                    window.location.href = `reporting.html?id=${reportId}`;
                } catch (error) {
                    console.error('Error confirming report:', error);
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            });
        }

        const editButton = document.getElementById('edit-button');
        if (editButton) {
            editButton.addEventListener('click', () => {
                window.location.href = `edit-report.html?id=${reportId}`;
            });
        }
        
        const cancelConfirmButton = document.getElementById('cancel-confirm-button');
        if (cancelConfirmButton) {
            cancelConfirmButton.addEventListener('click', async () => {
                try {
                    const { error } = await supabaseClient.from('report_requests').update({ status: 'cancel' }).eq('id', reportId);
                    if (error) throw error;
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'index.html';
                } catch(error) { 
                    console.error('Error cancelling report:', error);
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            });
        }

        const exitButton = document.getElementById('exit-button');
        if (exitButton) {
            exitButton.addEventListener('click', () => {
                sessionStorage.removeItem('report_id');
                window.location.href = 'index.html';
            });
        }

    } catch (error) {
        console.error('Error fetching report details:', error);
        sessionStorage.removeItem('report_id');
        window.location.href = 'report-error.html'; // Redirect to error page
    }
});