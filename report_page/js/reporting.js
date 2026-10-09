document.addEventListener('DOMContentLoaded', () => {
    const auth = getReportAuth();

    if (!auth) {
        alert('No report ID found. Redirecting to the main page.');
        clearReportAuth();
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        // In the "reporting" phase, cancellation might be complex.
        // For now, we just navigate away. A real implementation might need to
        // signal the backend to halt the reporting process if possible.
        cancelButton.addEventListener('click', () => {
            alert('Report submission has been cancelled.');
            clearReportAuth();
            window.location.href = 'index.html';
            // Note: We are not setting status to 'cancel' here as the backend
            // might be in a final, non-cancellable state. This is a UI-only cancel.
        });
    }

    if (!supabaseClient) {
        alert('Failed to connect to the database.');
        clearReportAuth();
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    // Watch for the final 'reported' status
    const stopPolling = pollReport(
        auth,
        (report) => {
            if (report.status === 'reported') {
                stopPolling();
                window.location.href = 'report-complete.html';
            } else if (report.status === 'error') { // Handle backend errors during reporting
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

    // Add a timeout for the reporting process
    const timeout = setTimeout(() => {
        stopPolling();
        console.warn('Report submission is taking longer than expected.');
        clearReportAuth();
        window.location.href = 'report-error.html'; // Redirect to error page on timeout
    }, 120000); // 2 minutes timeout

    // Clear timeout if the page is left
    window.addEventListener('beforeunload', () => {
        clearTimeout(timeout);
        stopPolling();
    });
});
