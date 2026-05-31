document.addEventListener('DOMContentLoaded', () => {
    // Clean up any report ID from session storage
    sessionStorage.removeItem('report_id');

    // Redirect to the main page after a 3-second delay
    setTimeout(() => {
        window.location.href = 'index.html';
    }, 3000);
});
