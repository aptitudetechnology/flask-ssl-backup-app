// gpg-backup-modal.js - Fixed Version

// Variable to store the ID of the selected GPG key
let selectedKeyId = null;
let currentJobId = null; // Track the current backup job
let progressInterval = null; // Store the progress polling interval

/**
 * Searches for GPG keys on a key server based on the provided email.
 */
export function searchGPGKeys(email = null) {
    // Get email from provided argument or from the hidden input within the modal
    const gpgModalEmailInput = document.getElementById("gpgModalEmail");
    const searchEmail = email || (gpgModalEmailInput ? gpgModalEmailInput.value.trim() : '');
    const resultsContainer = document.getElementById("gpgKeyResults");
    const importBtn = document.getElementById("importKeyBtn");

    if (!searchEmail) {
        if (resultsContainer) {
            resultsContainer.innerHTML = `<div class="alert alert-warning">Please ensure an email address is provided to search for GPG keys.</div>`;
        }
        return;
    }

    // Update UI to show searching status
    if (resultsContainer) {
        resultsContainer.innerHTML = `
        <div class="d-flex align-items-center text-muted">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
            Searching for keys for ${searchEmail}...
        </div>`;
    }
    if (importBtn) {
        importBtn.disabled = true;
    }
    selectedKeyId = null;

    fetch("/backup/gpg/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: searchEmail })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success || !data.keys || !data.keys.length) {
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    No GPG keys found for <strong>${searchEmail}</strong>.
                    <br><small class="text-muted">Try searching with a different email or check if the key exists on the keyserver.</small>
                </div>`;
            }
            return;
        }

        // Enhanced key display with better formatting
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                Found ${data.keys.length} key(s) for <strong>${searchEmail}</strong>. Select one to import:
            </div>
            ${data.keys.map((key, index) => {
                const uidText = key.uids ? key.uids.join(", ") : 'No User IDs';
                const createdDate = key.created ? new Date(key.created * 1000).toLocaleDateString() : 'Unknown';
                return `
                <div class="card mb-2">
                    <div class="card-body">
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="keySelect"
                                id="keyRadio${index}" value="${key.key_id}"
                                onchange="selectGPGKey('${key.key_id}')">
                            <label class="form-check-label" for="keyRadio${index}">
                                <div class="fw-bold">${key.key_id}</div>
                                <div class="text-muted small">${uidText}</div>
                                <div class="text-muted small">Created: ${createdDate}</div>
                            </label>
                        </div>
                    </div>
                </div>
                `;
            }).join("")}
            `;
        }
    })
    .catch(err => {
        console.error("GPG Key search failed:", err);
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Search failed. Please check your connection and try again.
                <br><small class="text-muted">Error: ${err.message}</small>
            </div>`;
        }
    });
}

/**
 * Sets the globally selected GPG key ID and enables the import button.
 */
export function selectGPGKey(keyId) {
    selectedKeyId = keyId;
    const importBtn = document.getElementById("importKeyBtn");
    if (importBtn) {
        importBtn.disabled = false;
        importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
    }
}

/**
 * Imports the currently selected GPG key from the key server via the backend.
 */
export function importSelectedGPGKey() {
    if (!selectedKeyId) {
        console.warn("No GPG key selected for import.");
        return;
    }

    const importBtn = document.getElementById("importKeyBtn");
    const resultsContainer = document.getElementById("gpgKeyResults");
    const selectedKeyInfo = document.getElementById("selectedKeyInfo");
    const statusLine = document.getElementById("gpgStatusLine");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");

    // Show importing state
    if (importBtn) {
        importBtn.disabled = true;
        importBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Importing...`;
    }

    fetch("/backup/gpg/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key_id: selectedKeyId })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Import failed: ${data.error}
                    <br><small class="text-muted">${data.details || ''}</small>
                </div>`;
            }
            return;
        }

        // Success - update UI
        const encryptionEmail = document.getElementById("gpgModalEmail")?.value || 'selected key';
        // Update email displays
        const encryptEmailSpan = document.getElementById("gpgEncryptEmail");
        const encryptEmailHidden = document.getElementById("gpgModalEmail");
        if (encryptEmailSpan) encryptEmailSpan.textContent = encryptionEmail;
        if (encryptEmailHidden) encryptEmailHidden.value = encryptionEmail;

        // Show success message and enable backup
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle me-2"></i>
                Key imported successfully! Ready to create encrypted backup.
            </div>`;
        }

        if (selectedKeyInfo) selectedKeyInfo.style.display = "flex";
        if (statusLine) statusLine.style.display = "none";
        if (importBtn) importBtn.style.display = "none";
        if (confirmBackupBtn) {
            confirmBackupBtn.disabled = false;
            confirmBackupBtn.style.display = "inline-block";
        }
    })
    .catch(err => {
        console.error("GPG Key import request failed:", err);
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Import request failed. Please try again.
            </div>`;
        }
    })
    .finally(() => {
        // This finally block ensures button state is reset if needed, though in success case it's hidden.
        // For failed cases, it re-enables it.
        if (importBtn && importBtn.style.display !== 'none') { // Only reset if not hidden
            importBtn.disabled = false;
            importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
        }
    });
}

/**
 * Enhanced GPGBackupModal class with fixed backup integration
 */
export class GPGBackupModal {
    constructor(modalId) {
        this.modalElement = document.getElementById(modalId);
        if (!this.modalElement) {
            console.warn(`GPGBackupModal: Modal element with ID '${modalId}' not found.`);
            return;
        }

        this.bootstrapModal = new bootstrap.Modal(this.modalElement);
        // Get step elements
        this.keySetupStep = document.getElementById('keySetupStep');
        this.backupProgressStep = document.getElementById('backupProgressStep');
        this.successStep = document.getElementById('successStep');
        this.errorStep = document.getElementById('errorStep');

        // Get button elements
        this.confirmCreateBackupBtn = document.getElementById('confirmCreateBackupBtn');
        this.downloadBackupBtn = document.getElementById('downloadBackupBtn');
        this.cancelBackupBtn = document.getElementById('cancelBackupBtn');

        // Progress elements
        this.progressBar = document.getElementById('progressBar');
        this.progressLabel = document.getElementById('progressLabel');
        this.progressStatus = document.getElementById('backupStatusMessage');

        // Ensure the Create Encrypted Backup button has its click handler set
        if (this.confirmCreateBackupBtn) {
            this.confirmCreateBackupBtn.onclick = () => this.startBackup();
        }

        this.showStep('keySetup');
    }

    show() {
        if (this.bootstrapModal) {
            this.bootstrapModal.show();
            this.showStep('keySetup');
            // Auto-search for keys when the modal is shown
            const gpgEmail = document.getElementById('gpgModalEmail')?.value;
            if (gpgEmail) {
                searchGPGKeys(gpgEmail);
            }
        }
    }

    hide() {
        if (this.bootstrapModal) {
            this.bootstrapModal.hide();
        }
        this.cleanup();
    }

    showStep(stepName) {
        // Hide all steps
        [this.keySetupStep, this.backupProgressStep, this.successStep, this.errorStep]
            .forEach(step => step && (step.style.display = 'none'));

        // Show requested step and manage buttons
        switch (stepName) {
            case 'keySetup':
                if (this.keySetupStep) this.keySetupStep.style.display = 'block';
                this.setButtonVisibility(false, false, true);
                // Reset states for key setup
                const resultsContainer = document.getElementById("gpgKeyResults");
                const importBtn = document.getElementById("importKeyBtn");
                const selectedKeyInfo = document.getElementById("selectedKeyInfo");
                const statusLine = document.getElementById("gpgStatusLine");

                if (resultsContainer) resultsContainer.innerHTML = ''; // Clear previous results
                if (importBtn) {
                    importBtn.style.display = 'inline-block'; // Ensure button is visible
                    importBtn.disabled = true; // Disabled until key is selected
                    importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
                }
                if (selectedKeyInfo) selectedKeyInfo.style.display = "none";
                if (statusLine) statusLine.style.display = "none"; // Hide initial "Checking GPG config"
                selectedKeyId = null; // Clear selected key
                break;
            case 'progress':
                if (this.backupProgressStep) this.backupProgressStep.style.display = 'block';
                this.setButtonVisibility(false, false, true);
                break;
            case 'success':
                if (this.successStep) this.successStep.style.display = 'block';
                this.setButtonVisibility(false, true, false);
                break;
            case 'error':
                if (this.errorStep) this.errorStep.style.display = 'block';
                this.setButtonVisibility(false, false, true);
                break;
        }
    }

    setButtonVisibility(confirm, download, cancel) {
        if (this.confirmCreateBackupBtn) {
            this.confirmCreateBackupBtn.style.display = confirm ? 'inline-block' : 'none';
        }
        if (this.downloadBackupBtn) {
            this.downloadBackupBtn.style.display = download ? 'inline-block' : 'none';
        }
        if (this.cancelBackupBtn) {
            this.cancelBackupBtn.style.display = cancel ? 'inline-block' : 'none';
        }
    }

    /**
     * FIXED: Real backup integration with your Flask backend
     */
    async startBackup() {
        // Prevent backup if confirm button is disabled
        if (this.confirmCreateBackupBtn && this.confirmCreateBackupBtn.disabled) {
            return;
        }
        
        this.showStep('progress');
        this.updateProgress(10, 'Preparing backup request...');

        try {
            // Get form data from the main form
            const mainForm = document.getElementById('backupForm');
            if (!mainForm) {
                throw new Error('Main backup form not found');
            }

            const formData = new FormData(mainForm);
            
            // Ensure GPG encryption is enabled since we're in the GPG modal
            formData.set('encrypt_gpg', 'on');
            
            // Get the email from the modal
            const gpgEmail = document.getElementById('gpgModalEmail')?.value;
            if (gpgEmail) {
                formData.set('gpg_email', gpgEmail);
            }

            this.updateProgress(30, 'Sending backup request...');

            // Make the request
            const response = await fetch('/backup/create', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            this.updateProgress(60, 'Processing backup...');

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Check if response is JSON (error) or file (success)
            const contentType = response.headers.get('content-type') || '';
            
            if (contentType.includes('application/json')) {
                // Error response
                const data = await response.json();
                throw new Error(data.error || 'Backup creation failed');
            } else {
                // File response - handle download
                this.updateProgress(90, 'Preparing download...');
                
                const blob = await response.blob();
                const disposition = response.headers.get('content-disposition');
                let filename = 'encrypted_backup.gpg';
                
                // Extract filename from Content-Disposition header
                if (disposition && disposition.includes('filename=')) {
                    const matches = disposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                    if (matches && matches[1]) {
                        filename = matches[1].replace(/['"]/g, '');
                    }
                }

                // Create download link and trigger download
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
                
                // Cleanup
                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                }, 100);

                this.updateProgress(100, 'Download complete!');
                
                // Show success and auto-close modal
                setTimeout(() => {
                    this.showStep('success');
                    setTimeout(() => {
                        this.hide();
                    }, 2000);
                }, 500);
            }

        } catch (error) {
            console.error('Backup failed:', error);
            this.showError(error.message);
        }
    }

    /**
     * Poll backup progress (kept for compatibility but not used in fixed version)
     */
    async pollProgress() {
        if (!currentJobId) return;

        // Clear any existing interval before setting a new one to prevent multiple polls
        if (progressInterval) {
            clearTimeout(progressInterval);
        }

        try {
            const response = await fetch(`/backup/progress/${currentJobId}`);
            const data = await response.json();

            if (!data.success) {
                if (data.error) {
                    throw new Error(data.error);
                }
                return;
            }

            const progress = data.progress || {};
            this.updateProgress(progress.percentage || 0, progress.status || 'Processing...');

            if (data.completed) {
                if (data.download_url) {
                    this.showSuccess(data.download_url);
                } else {
                    throw new Error('Backup completed but no download URL provided');
                }
            } else {
                // Continue polling
                progressInterval = setTimeout(() => this.pollProgress(), 1000);
            }

        } catch (error) {
            console.error('Progress polling failed:', error);
            this.showError(error.message);
        }
    }

    updateProgress(percentage, status) {
        // Ensure progress bar elements are correctly targeted by their IDs as per gpg-modal.html
        if (this.progressBar) {
            this.progressBar.style.width = `${percentage}%`;
            this.progressBar.setAttribute('aria-valuenow', percentage);
        }
        if (this.progressLabel) {
            this.progressLabel.textContent = `Creating backup... ${percentage}%`;
        }
        if (this.progressStatus) {
            this.progressStatus.textContent = status;
        }
    }

    showSuccess(downloadUrl) {
        this.showStep('success');
        if (this.downloadBackupBtn) {
            this.downloadBackupBtn.onclick = () => {
                window.location.href = downloadUrl;
                this.hide();
            };
        }
        // Automatically trigger the download
        if (downloadUrl) {
            window.location.href = downloadUrl;
        }
        setTimeout(() => {
            this.hide();
        }, 2000);
    }

    showError(message) {
        this.showStep('error');
        const errorElement = document.getElementById('errorMessage');
        if (errorElement) {
            errorElement.textContent = message;
        }
        // Also ensure download and confirm buttons are hidden, cancel visible
        this.setButtonVisibility(false, false, true);
    }

    async cancelBackup() {
        if (currentJobId) {
            try {
                await fetch(`/backup/cancel/${currentJobId}`, { method: 'POST' });
            } catch (error) {
                console.error('Failed to cancel backup:', error);
            }
        }
        this.cleanup();
        this.hide();
    }

    cleanup() {
        if (progressInterval) {
            clearTimeout(progressInterval);
            progressInterval = null;
        }
        currentJobId = null;
        selectedKeyId = null; // Clear selected key on cleanup
        // Reset modal content/state when it's hidden for next use
        if (document.getElementById("gpgKeyResults")) {
            document.getElementById("gpgKeyResults").innerHTML = '';
        }
        if (document.getElementById("importKeyBtn")) {
            document.getElementById("importKeyBtn").style.display = 'inline-block';
            document.getElementById("importKeyBtn").disabled = true;
        }
        if (document.getElementById("selectedKeyInfo")) {
            document.getElementById("selectedKeyInfo").style.display = 'none';
        }
        if (document.getElementById("gpgStatusLine")) {
            document.getElementById("gpgStatusLine").style.display = 'none';
        }
        if (document.getElementById("confirmCreateBackupBtn")) {
            document.getElementById("confirmCreateBackupBtn").style.display = 'none';
        }
        if (document.getElementById("downloadBackupBtn")) {
            document.getElementById("downloadBackupBtn").style.display = 'none';
        }
        if (document.getElementById("errorMessage")) {
            document.getElementById("errorMessage").textContent = 'Unable to create encrypted backup. Please try again.';
        }
        // Reset progress bar to 0%
        this.updateProgress(0, '...');
    }

    setEncryptionEmail(email) {
        // window.GPG_ENCRYPTION_EMAIL is not strictly needed if we always read from gpgModalEmail
        // but keeping it for now if other parts of code might use it.
        window.GPG_ENCRYPTION_EMAIL = email;
        const elements = ['gpgEncryptEmail', 'gpgModalEmail'];
        elements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                if (element.tagName === 'INPUT') {
                    element.value = email;
                } else {
                    element.textContent = email;
                }
            }
        });
    }
}

// Make functions globally available for inline event handlers
window.selectGPGKey = selectGPGKey;
window.searchGPGKeys = searchGPGKeys;
window.importSelectedGPGKey = importSelectedGPGKey;