// main.js - Handles regular (non-GPG) backup form submission and triggers download

document.addEventListener('DOMContentLoaded', function() {
    const backupForm = document.getElementById('backupForm');
    if (backupForm) {
        backupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(backupForm);
            const createBtn = document.getElementById('createBackupBtn');
            if (createBtn) createBtn.disabled = true;
            try {
                const response = await fetch('/backup/create', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.success && data.download_url) {
                    window.location.href = data.download_url;
                } else {
                    alert(data.error || 'Backup failed.');
                }
            } catch (err) {
                alert('Backup failed: ' + err.message);
            } finally {
                if (createBtn) createBtn.disabled = false;
            }
        });
    }
});
