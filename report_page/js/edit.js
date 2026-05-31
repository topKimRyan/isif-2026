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
            .select('reason, detected_keywords')
            .eq('id', reportId)
            .single();

        if (error || !data) {
            throw error || new Error('Report data not found.');
        }

        const editReasonTextarea = document.getElementById('reason');
        const keywordListEditable = document.getElementById('keyword-list-editable');
        const newKeywordInput = document.getElementById('new-keyword-input');
        const addKeywordButton = document.getElementById('add-keyword-button');
        const confirmEditButton = document.getElementById('confirm-edit-button');
        const backToConfirmButton = document.getElementById('back-to-confirm');

        editReasonTextarea.value = data.reason || '';
        let currentKeywords = data.detected_keywords || [];

        const renderKeywords = () => {
            keywordListEditable.innerHTML = '';
            currentKeywords.forEach((keyword, index) => {
                const item = document.createElement('div');
                item.className = 'keyword-item';
                item.innerHTML = `<span>${keyword}</span><button type="button" class="delete-keyword" data-index="${index}"><i class="fi fi-sr-cross-small"></i></button>`;
                keywordListEditable.appendChild(item);
            });
            // Re-add event listeners for delete buttons
            keywordListEditable.querySelectorAll('.delete-keyword').forEach(button => {
                button.addEventListener('click', (e) => {
                    // Use `closest` to be safe
                    const indexToDelete = e.target.closest('.delete-keyword').dataset.index;
                    currentKeywords.splice(indexToDelete, 1);
                    renderKeywords(); // Re-render the list
                });
            });
        };

        renderKeywords();

        addKeywordButton.addEventListener('click', () => {
            const newKeyword = newKeywordInput.value.trim();
            if (newKeyword && !currentKeywords.includes(newKeyword)) {
                currentKeywords.push(newKeyword);
                newKeywordInput.value = '';
                renderKeywords();
            } else if (currentKeywords.includes(newKeyword)) {
                alert('이미 존재하는 키워드입니다.');
            }
        });

        newKeywordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addKeywordButton.click();
            }
        });

        confirmEditButton.addEventListener('click', async () => {
            try {
                const { error } = await supabaseClient
                    .from('report_requests')
                    .update({
                        reason: editReasonTextarea.value,
                        detected_keywords: currentKeywords
                    })
                    .eq('id', reportId);
                
                if (error) throw error;
                
                // Redirect back to confirm page
                window.location.href = `report-confirm.html?id=${reportId}`;
            } catch (e) {
                console.error("Error updating report:", e);
                sessionStorage.removeItem('report_id'); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });

        backToConfirmButton.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = `report-confirm.html?id=${reportId}`;
        });

    } catch(error) {
        console.error('Error fetching report details for editing:', error);
        sessionStorage.removeItem('report_id'); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
    }
});