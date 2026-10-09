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
            let url = urlInput.value.trim();
            if (!url) {
                alert('Please enter a site URL.');
                return;
            }

            // Accept bare domains like "example.com" by assuming https
            if (!/^[a-z][a-z0-9+.-]*:/i.test(url)) {
                url = `https://${url}`;
            }

            // Only http(s) URLs can be analyzed (the server enforces this too)
            try {
                const parsed = new URL(url);
                if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error();
                url = parsed.href;
            } catch {
                alert('Please enter a valid http(s) site URL.');
                return;
            }

            // Check if supabase client is available
            if (!supabaseClient) {
                alert('Failed to connect to the database. Please check your settings.');
                clearReportAuth(); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
                return;
            }

            // Disable button to prevent multiple submissions
            analysisButton.disabled = true;
            analysisButton.textContent = 'Requesting analysis...';

            try {
                // 1. Insert the new report into the database
                // The function returns the report id and its secret access token
                const report = await reportRpc('create_report', { p_url: url });

                if (report && report.id && report.token) {
                    // 2. Store the credentials in session storage
                    saveReportAuth(report.id, report.token);
                    // 3. Redirect to the analysis page
                    window.location.href = `analysis.html?${reportQuery({ id: report.id, token: report.token })}`;
                } else {
                    throw new Error('Report was not created.');
                }
            } catch (error) {
                console.error('Error submitting report:', error);
                if (error && error.code === 'PT429') {
                    alert('Too many reports from your network. Please try again later.');
                    analysisButton.disabled = false;
                    analysisButton.textContent = 'Start Analysis';
                    return;
                }
                clearReportAuth(); // Clear session storage
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });
    }
});
