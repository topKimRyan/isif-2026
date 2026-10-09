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

        const { url, is_illegal, reason, detected_keywords: keywords } = data;

        const dynamicContent = document.getElementById('dynamic-content');
        const dynamicButtons = document.getElementById('dynamic-buttons');
        const backButton = document.getElementById('back-button-dynamic');

        let contentHTML = '';
        let buttonsHTML = '';

        if (is_illegal) {
            contentHTML = `
                <h1>Is the information below correct?</h1>
                <div class="result-card minimal-card">
                    <div class="result-header">
                        <div class="result-icon illegal"><i class="fi fi-sr-cross-circle"></i></div>
                        <div class="result-title"><h2>Suspected Illegal Site</h2></div>
                    </div>
                </div>
                <form id="confirmation-form">
                    <label for="site-url-confirm">Site URL</label>
                    <input type="url" id="site-url-confirm" name="site-url" value="${escapeHtml(url)}" readonly>
                    <label for="reason-confirm">Reason</label>
                    <textarea id="reason-confirm" name="reason" rows="4" readonly>${escapeHtml(reason || '')}</textarea>
                    ${(keywords && keywords.length > 0) ? `<h3>Detected Keywords</h3><ul class="keyword-list">${keywords.map(k => `<li>${escapeHtml(k)}</li>`).join('')}</ul>` : ''}
                </form>
            `;
            buttonsHTML = `
                <div class="confirm-buttons-stacked">
                    <button type="button" class="btn-primary" id="report-button">Report</button>
                    <button type="button" class="btn-secondary" id="edit-button">Edit</button>
                    <button type="button" class="btn-text-only" id="cancel-confirm-button">Cancel</button>
                </div>
            `;
        } else {
            contentHTML = `
                <h1>The site could not be<br>verified as illegal</h1>
                <div class="result-card minimal-card">
                    <div class="result-header">
                        <div class="result-icon legal"><i class="fi fi-sr-check-circle"></i></div>
                        <div class="result-title"><h2>Legitimate Site</h2></div>
                    </div>
                </div>
                <form id="confirmation-form">
                    <label for="site-url-confirm">Site URL</label>
                    <input type="url" id="site-url-confirm" name="site-url" value="${escapeHtml(url)}" readonly>
                    <label for="reason-confirm">Reason</label>
                    <textarea id="reason-confirm" name="reason" rows="4" readonly>${escapeHtml(reason || '')}</textarea>
                </form>
            `;
            buttonsHTML = `<button type="button" class="btn-primary" id="exit-button">Exit</button>`;
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
                    const confirmed = await reportRpc('confirm_report', { p_id: auth.id, p_token: auth.token });

                    if (!confirmed) throw new Error('Report can no longer be confirmed.');
                    window.location.href = `reporting.html?${reportQuery(auth)}`;
                } catch (error) {
                    console.error('Error confirming report:', error);
                    clearReportAuth();
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            });
        }

        const editButton = document.getElementById('edit-button');
        if (editButton) {
            editButton.addEventListener('click', () => {
                window.location.href = `edit-report.html?${reportQuery(auth)}`;
            });
        }

        const cancelConfirmButton = document.getElementById('cancel-confirm-button');
        if (cancelConfirmButton) {
            cancelConfirmButton.addEventListener('click', async () => {
                try {
                    await reportRpc('cancel_report', { p_id: auth.id, p_token: auth.token });
                    clearReportAuth();
                    window.location.href = 'index.html';
                } catch(error) {
                    console.error('Error cancelling report:', error);
                    clearReportAuth();
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            });
        }

        const exitButton = document.getElementById('exit-button');
        if (exitButton) {
            exitButton.addEventListener('click', () => {
                clearReportAuth();
                window.location.href = 'index.html';
            });
        }

    } catch (error) {
        console.error('Error fetching report details:', error);
        clearReportAuth();
        window.location.href = 'report-error.html'; // Redirect to error page
    }
});
