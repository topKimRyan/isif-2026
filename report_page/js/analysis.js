document.addEventListener('DOMContentLoaded', () => {
    const auth = getReportAuth();

    if (!auth) {
        alert('No report ID found. Redirecting to the main page.');
        window.location.href = 'index.html';
        return;
    }

    // Store it in session storage just in case it came from the URL
    saveReportAuth(auth.id, auth.token);

    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        cancelButton.addEventListener('click', async () => {
            if (!supabaseClient) {
                alert('Failed to connect to the database.');
                return;
            }
            try {
                await reportRpc('cancel_report', { p_id: auth.id, p_token: auth.token });

                clearReportAuth(); // Clean up
                window.location.href = 'index.html';
            } catch (error) {
                console.error('Error cancelling report:', error);
                clearReportAuth();
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });
    }

    if (!supabaseClient) {
        alert('Failed to connect to the database.');
        return;
    }

    // Watch the report status until the worker finishes the analysis
    const stopPolling = pollReport(
        auth,
        (report) => {
            if (report.status === 'analyzed') {
                // Analysis is complete, move to the confirmation page
                stopPolling();
                window.location.href = `report-confirm.html?${reportQuery(auth)}`;
            } else if (report.status === 'cancel') {
                // If cancelled from another source
                stopPolling();
                clearReportAuth();
                window.location.href = 'index.html'; // Redirect to index for a clean cancel
            } else if (report.status === 'error') { // Handle backend errors during analysis
                stopPolling();
                clearReportAuth();
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        },
        (error) => {
            console.error('Failed to read report status:', error);
            clearReportAuth();
            window.location.href = 'report-error.html';
        }
    );

    // Add a timeout for the analysis, in case the backend fails
    const timeout = setTimeout(async () => {
        stopPolling();
        alert('Analysis timed out. Please try again.');
        // Also cancel the report on the backend
        try {
            await reportRpc('cancel_report', { p_id: auth.id, p_token: auth.token });
        } catch (error) {
            console.error('Failed to cancel report on timeout:', error);
        } finally {
            clearReportAuth();
            window.location.href = 'index.html';
        }
    }, 60000); // 60 seconds timeout

    // Clear timeout if the page is left for any reason
    window.addEventListener('beforeunload', () => {
        clearTimeout(timeout);
        stopPolling();
    });
});
