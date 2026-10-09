document.addEventListener('DOMContentLoaded', () => {
    // This is the main page. If a user lands here, we can assume
    // any ongoing report process should be cleared.
    // This is a simple way to handle abandoned processes.
    if (sessionStorage.getItem('report_id')) {
        console.log('Clearing abandoned report session.');
        clearReportAuth();
    }
});
