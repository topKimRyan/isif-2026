document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const reportId = params.get('id') || sessionStorage.getItem('report_id');

    if (!reportId) {
        alert('신고 ID가 없습니다. 메인 페이지로 돌아갑니다.');
        sessionStorage.removeItem('report_id'); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        // In the "reporting" phase, cancellation might be complex.
        // For now, we just navigate away. A real implementation might need to
        // signal the backend to halt the reporting process if possible.
        cancelButton.addEventListener('click', () => {
            alert('신고 진행이 취소되었습니다.');
            sessionStorage.removeItem('report_id');
            window.location.href = 'index.html';
            // Note: We are not setting status to 'cancel' here as the backend
            // might be in a final, non-cancellable state. This is a UI-only cancel.
        });
    }

    if (!supabaseClient) {
        alert('데이터베이스 연결에 실패했습니다.');
        sessionStorage.removeItem('report_id'); // Clear session storage
        window.location.href = 'report-error.html'; // Redirect to error page
        return;
    }

    // Listen for the final 'reported' status
    const channel = supabaseClient.channel(`report_reporting_${reportId}`);
    const subscription = channel
        .on(
            'postgres_changes',
            {
                event: 'UPDATE',
                schema: 'public',
                table: 'report_requests',
                filter: `id=eq.${reportId}`
            },
            (payload) => {
                const newStatus = payload.new.status;
                if (newStatus === 'reported') {
                    supabaseClient.removeChannel(subscription);
                    window.location.href = 'report-complete.html';
                } else if (newStatus === 'error') { // Handle backend errors during reporting
                    supabaseClient.removeChannel(subscription);
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            }
        )
        .subscribe(status => {
            if (status === 'SUBSCRIBED') {
                console.log('Subscribed to final report status.');
            } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
                console.error('Subscription error:', status);
                sessionStorage.removeItem('report_id');
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });

    // Add a timeout for the reporting process
    const timeout = setTimeout(() => {
        supabaseClient.removeChannel(subscription);
        if (window.location.pathname.includes('reporting.html')) {
            console.warn('신고 처리가 지연되고 있습니다.');
            sessionStorage.removeItem('report_id'); // Clear session storage
            window.location.href = 'report-error.html'; // Redirect to error page on timeout
        }
    }, 120000); // 2 minutes timeout

    // Clear timeout if the page is left
    window.addEventListener('beforeunload', () => {
        clearTimeout(timeout);
        supabaseClient.removeChannel(subscription);
    });
});