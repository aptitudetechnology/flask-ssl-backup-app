// gpg-backup-modal.js - Enhanced Version

// Variable to store the ID of the selected GPG key
let selectedKeyId = null;
let currentJobId = null; // Track the current backup job
let progressInterval = null; // Store the progress polling interval

/**
 * Searches for GPG keys on a key server based on the provided email.
 */
export function searchGPGKeys(email = null) {
    const emailInput = document.getElementById("gpgEmailInput");
    const resultsContainer = document.getElementById("gpgKeyResults");
    const importBtn = document.getElementById("importKeyBtn");

    // Use provided email or get from input
    const searchEmail = email || (emailInput ? emailInput.value.trim() : '');

    if (!searchEmail) {
        if (resultsContainer) {
            resultsContainer.innerHTML = `<div class="alert alert-warning">Please enter a valid email address.</div>`;
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
        const encryptionEmail = window.GPG_ENCRYPTION_EMAIL || 'selected key';
        
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
        if (importBtn) {
            importBtn.disabled = true;
            importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
        }
    });
}

/**
 * Enhanced GPGBackupModal class with real backup integration
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
        this.progressBar = document.getElementById('backupProgressBar');
        this.progressLabel = document.getElementById('backupProgressLabel');
        this.progressStatus = document.getElementById('backupProgressStatus');

        this.showStep('keySetup');
    }

    show() {
        if (this.bootstrapModal) {
            this.bootstrapModal.show();
            this.showStep('keySetup');
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
     * Real backup integration with your Flask backend
     */
    async startBackup() {
        this.showStep('progress');
        this.updateProgress(0, 'Initializing backup...');

        try {
            // Get form data
            const formData = new FormData();
            const format = document.querySelector('input[name="format"]:checked')?.value || 'zip';
            const includeAttachments = document.getElementById('include_attachments')?.checked || false;
            const gpgEmail = document.getElementById('gpgModalEmail')?.value;

            formData.append('format', format);
            if (includeAttachments) formData.append('include_attachments', 'on');
            formData.append('encrypt_gpg', 'on');
            formData.append('gpg_email', gpgEmail);

            // Start backup job
            const response = await fetch('/backup/create', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to start backup');
            }

            currentJobId = data.job_id;
            this.pollProgress();

        } catch (error) {
            console.error('Backup failed:', error);
            this.showError(error.message);
        }
    }

    /**
     * Poll backup progress
     */
    async pollProgress() {
        if (!currentJobId) return;

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
                setTimeout(() => this.pollProgress(), 1000);
            }

        } catch (error) {
            console.error('Progress polling failed:', error);
            this.showError(error.message);
        }
    }

    updateProgress(percentage, status) {
        if (this.progressBar) {
            this.progressBar.style.width = `${percentage}%`;
            this.progressBar.setAttribute('aria-valuenow', percentage);
        }
        if (this.progressLabel) {
            this.progressLabel.textContent = `${percentage}%`;
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
    }

    showError(message) {
        this.showStep('error');
        const errorElement = document.getElementById('errorMessage');
        if (errorElement) {
            errorElement.textContent = message;
        }
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
            clearInterval(progressInterval);
            progressInterval = null;
        }
        currentJobId = null;
    }

    setEncryptionEmail(email) {
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