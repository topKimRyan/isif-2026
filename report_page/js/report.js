document.addEventListener('DOMContentLoaded', () => {
    const analysisButton = document.getElementById('analysis-button');
    const urlInput = document.getElementById('site-url');

    // If a URL is passed from another page, populate it.
    const urlFromParams = new URLSearchParams(window.location.search).get('url');
    if (urlInput && urlFromParams) {
        urlInput.value = decodeURIComponent(urlFromParams);
    }
    
    if (analysisButton) {
        analysisButton.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                alert('사이트 URL을 입력해주세요.');
                return;
            }

            // Check if supabase client is available
            if (!supabaseClient) {
                alert('데이터베이스 연결에 실패했습니다. 설정을 확인해주세요.');
                sessionStorage.removeItem('report_id'); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
                return;
            }

            // Disable button to prevent multiple submissions
            analysisButton.disabled = true;
            analysisButton.textContent = '분석 요청중...';

            try {
                // 1. Insert the new report into the database
                const { data, error } = await supabaseClient
                    .from('report_requests')
                    .insert([
                        { url: url, status: 'submitted' }
                    ])
                    .select() // Return the inserted row
                    .single(); // Expect a single row back

                if (error) {
                    throw error;
                }

                if (data) {
                    const reportId = data.id;
                    // 2. Store the ID in session storage
                    sessionStorage.setItem('report_id', reportId);
                    // 3. Redirect to the analysis page
                    window.location.href = `analysis.html?id=${reportId}`;
                }
            } catch (error) {
                console.error('Error submitting report:', error);
                sessionStorage.removeItem('report_id'); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });
    }
});
