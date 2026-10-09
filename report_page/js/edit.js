document.addEventListener('DOMContentLoaded', async () => {
    const auth = getReportAuth();

    if (!auth) {
        alert('No report information found. Redirecting to the main page.');
        clearReportAuth(); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    if (!supabaseClient) {
        alert('Failed to connect to the database.');
        clearReportAuth(); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    try {
        const data = await fetchReport(auth);

        if (!data) {
            throw new Error('Report data not found.');
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
                item.innerHTML = `<span>${escapeHtml(keyword)}</span><button type="button" class="delete-keyword" data-index="${index}"><i class="fi fi-sr-cross-small"></i></button>`;
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
                alert('This keyword already exists.');
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
                const updated = await reportRpc('update_report_details', {
                    p_id: auth.id,
                    p_token: auth.token,
                    p_reason: editReasonTextarea.value,
                    p_keywords: currentKeywords
                });

                if (!updated) throw new Error('Report can no longer be edited.');

                // Redirect back to confirm page
                window.location.href = `report-confirm.html?${reportQuery(auth)}`;
            } catch (e) {
                console.error("Error updating report:", e);
                clearReportAuth(); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });

        backToConfirmButton.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = `report-confirm.html?${reportQuery(auth)}`;
        });

    } catch(error) {
        console.error('Error fetching report details for editing:', error);
        clearReportAuth(); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
    }
});
