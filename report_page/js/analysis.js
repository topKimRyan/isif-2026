document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const reportId = params.get('id') || sessionStorage.getItem('report_id');

    if (!reportId) {
        alert('신고 ID가 없습니다. 메인 페이지로 돌아갑니다.');
        window.location.href = 'index.html';
        return;
    }
    
    // Store it in session storage just in case it came from the URL
    if (params.get('id')) {
        sessionStorage.setItem('report_id', reportId);
    }


    const cancelButton = document.getElementById('cancel-button');
    if (cancelButton) {
        cancelButton.addEventListener('click', async () => {
            if (!supabaseClient) {
                alert('데이터베이스 연결에 실패했습니다.');
                return;
            }
            try {
                // Update status to 'cancel' in the database
                const { error } = await supabaseClient
                    .from('report_requests')
                    .update({ status: 'cancel' })
                    .eq('id', reportId);

                if (error) throw error;
                
                sessionStorage.removeItem('report_id'); // Clean up
                window.location.href = 'index.html';
            } catch (error) {
                console.error('Error cancelling report:', error);
                sessionStorage.removeItem('report_id');
                window.location.href = 'report-error.html'; // Redirect to error page
            }
        });
    }

    if (!supabaseClient) {
        alert('데이터베이스 연결에 실패했습니다.');
        return;
    }

    // Listen for changes to the report
    const channel = supabaseClient.channel(`report_analysis_${reportId}`);

    channel
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
                if (newStatus === 'analyzed') {
                    // Analysis is complete, move to the confirmation page
                    supabaseClient.removeChannel(channel); // Stop listening
                    window.location.href = `report-confirm.html?id=${reportId}`;
                } else if (newStatus === 'cancel') {
                    // If cancelled from another source
                    supabaseClient.removeChannel(channel);
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'index.html'; // Redirect to index for a clean cancel
                } else if (newStatus === 'error') { // Handle backend errors during analysis
                    supabaseClient.removeChannel(channel);
                    sessionStorage.removeItem('report_id');
                    window.location.href = 'report-error.html'; // Redirect to error page
                }
            }
        )
        .subscribe(status => {
            if (status === 'SUBSCRIBED') {
                console.log('Subscribed to analysis status updates.');
            } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
                console.error('Subscription error:', status);
                sessionStorage.removeItem('report_id');
                window.location.href = 'report-error.html'; // Redirect to error page for subscription errors
            }
        });
    
    // Add a timeout for the analysis, in case the backend fails
    const timeout = setTimeout(async () => {
        supabaseClient.removeChannel(channel);
        // Check if we are still on the analysis page before showing the alert
        if (window.location.pathname.includes('analysis.html')) { 
             alert('분석 시간이 초과되었습니다. 다시 시도해주세요.');
             // Also cancel the report on the backend
             try {
                await supabaseClient.from('report_requests').update({ status: 'cancel' }).eq('id', reportId);
             } catch (error) {
                console.error('Failed to cancel report on timeout:', error);
             } finally {
                sessionStorage.removeItem('report_id');
                window.location.href = 'index.html';
             }
        }
    }, 60000); // 60 seconds timeout

    // Clear timeout if the page is left for any reason
    window.addEventListener('beforeunload', () => {
        clearTimeout(timeout);
        supabaseClient.removeChannel(channel);
    });
});
