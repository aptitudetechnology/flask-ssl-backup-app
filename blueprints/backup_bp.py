// Inside submitBackupFormAJAX() after `response => response.json()`
// Instead of .then(response => response.json()), you'd have:
fetch('/backup/create', {
    method: 'POST',
    body: formData
})
.then(response => {
    if (response.ok) {
        // If the backend sends a file, response.json() will fail.
        // We need to handle it as a blob.
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'backup.dat'; // Default filename
        if (contentDisposition && contentDisposition.indexOf('attachment') !== -1) {
            const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1];
            }
        }

        return response.blob().then(blob => {
            // Create a link element
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename; // Use the extracted filename
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            alert('Backup created and download initiated.'); // Only show this if successful
        });
    } else {
        // If the backend returns an error JSON (e.g., encryption failed), parse it as JSON
        return response.json().then(errorData => {
            alert('Backup failed: ' + (errorData.error || 'Unknown error'));
        }).catch(() => {
            // Fallback for non-JSON errors
            alert('Backup failed: Server error ' + response.status);
        });
    }
})
.catch(err => {
    alert('Backup failed: ' + err);
});