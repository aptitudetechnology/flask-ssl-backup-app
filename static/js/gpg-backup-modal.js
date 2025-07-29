// gpg-backup-modal.js - Fixed Implementation

// Variable to store the ID of the selected GPG key
let selectedKeyId = null;
let currentJobId = null; // Track the current backup job
let progressInterval = null; // Store the progress polling interval

/**
 * Fixed: Ensure modal buttons are properly contained and functional
 */
function ensureModalButtonsIntegrity() {
    const modal = document.getElementById("gpgConfirmationModal");
    const importBtn = document.getElementById("importKeyBtn");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");
    const cancelBtn = document.getElementById("cancelBackupBtn");
    
    if (!modal) {
        console.error("GPG modal not found");
        return false;
    }

    // Ensure buttons are within modal content
    const modalContent = modal.querySelector('.modal-content');
    const modalFooter = modal.querySelector('.modal-footer');
    
    if (!modalContent || !modalFooter) {
        console.error("Modal structure incomplete - missing .modal-content or .modal-footer");
        return false;
    }

    // Fix button positioning by ensuring they're in the modal footer
    if (importBtn && !modalFooter.contains(importBtn)) {
        console.warn("Import button found outside modal footer, moving it");
        modalFooter.appendChild(importBtn);
    }
    
    if (confirmBackupBtn && !modalFooter.contains(confirmBackupBtn)) {
        console.warn("Confirm button found outside modal footer, moving it");
        modalFooter.appendChild(confirmBackupBtn);
    }

    if (cancelBtn && !modalFooter.contains(cancelBtn)) {
        console.warn("Cancel button found outside modal footer, moving it");
        modalFooter.appendChild(cancelBtn);
    }

    // Ensure proper CSS classes for modal buttons
    [importBtn, confirmBackupBtn, cancelBtn].forEach(btn => {
        if (btn) {
            btn.classList.add('btn');
            btn.style.position = 'relative'; // Ensure not absolutely positioned
            btn.style.zIndex = 'auto';
        }
    });

    return true;
}

/**
 * Fixed: Properly bind event handlers to modal buttons
 */
function bindModalEventHandlers() {
    const importBtn = document.getElementById("importKeyBtn");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");
    const cancelBtn = document.getElementById("cancelBackupBtn");

    // Remove existing event listeners to prevent duplicates
    if (importBtn) {
        importBtn.replaceWith(importBtn.cloneNode(true));
        const newImportBtn = document.getElementById("importKeyBtn");
        newImportBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            importSelectedGPGKey();
        });
    }

    if (confirmBackupBtn) {
        confirmBackupBtn.replaceWith(confirmBackupBtn.cloneNode(true));
        const newConfirmBtn = document.getElementById("confirmCreateBackupBtn");
        newConfirmBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleConfirmBackup();
        });
    }

    if (cancelBtn) {
        cancelBtn.replaceWith(cancelBtn.cloneNode(true));
        const newCancelBtn = document.getElementById("cancelBackupBtn");
        newCancelBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            handleCancelBackup();
        });
    }
}

/**
 * Fixed: Handle confirm backup with proper error handling
 */
function handleConfirmBackup() {
    const modalEmailInput = document.getElementById("gpgModalEmail");
    const email = modalEmailInput ? modalEmailInput.value.trim() : '';
    
    if (!email) {
        alert('No email address found for encryption');
        return;
    }

    // Hide modal and trigger backup
    const modal = bootstrap.Modal.getInstance(document.getElementById("gpgConfirmationModal"));
    if (modal) {
        modal.hide();
    }

    // Trigger the actual backup creation
    if (window.createEncryptedBackup) {
        window.createEncryptedBackup();
    } else {
        console.error('createEncryptedBackup function not found');
        alert('Backup function not available. Please refresh the page and try again.');
    }
}

/**
 * Fixed: Handle cancel backup
 */
function handleCancelBackup() {
    const modal = bootstrap.Modal.getInstance(document.getElementById("gpgConfirmationModal"));
    if (modal) {
        modal.hide();
    }
    resetGPGModal();
}

/**
 * NEW: Local-first key checking function with improved error handling
 */
export async function checkLocalKeysFirst(email = null) {
    // Ensure modal integrity before proceeding
    if (!ensureModalButtonsIntegrity()) {
        console.error("Modal integrity check failed");
        return;
    }

    // Get email from multiple possible sources
    const gpgModalEmailInput = document.getElementById("gpgModalEmail");
    const mainPageEmailInput = document.getElementById("gpgEmail");
    const searchEmail = email || 
                       (gpgModalEmailInput ? gpgModalEmailInput.value.trim() : '') ||
                       (mainPageEmailInput ? mainPageEmailInput.value.trim() : '');
    
    const resultsContainer = document.getElementById("gpgKeyResults");
    const importBtn = document.getElementById("importKeyBtn");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");

    if (!searchEmail) {
        if (resultsContainer) {
            resultsContainer.innerHTML = `<div class="alert alert-warning">Please ensure an email address is provided to search for GPG keys.</div>`;
        }
        return;
    }

    // Reset UI state
    if (importBtn) {
        importBtn.disabled = true;
        importBtn.style.display = 'inline-block';
    }
    if (confirmBackupBtn) {
        confirmBackupBtn.disabled = true;
        confirmBackupBtn.style.display = 'none';
    }
    selectedKeyId = null;

    try {
        // Step 1: Check local keychain first
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="d-flex align-items-center text-muted">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Checking local keychain...
            </div>`;
        }

        const localCheckResponse = await fetch("/backup/gpg/check-local", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: searchEmail })
        });

        const localCheckData = await localCheckResponse.json();

        if (!localCheckData.success) {
            throw new Error(localCheckData.error || 'Local key check failed');
        }

        // Step 2: Handle local key found
        if (localCheckData.found) {
            const keyInfo = localCheckData.key_info || {};
            
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="bi bi-check-circle me-2"></i>
                    <strong>✓ Found key locally for ${searchEmail}</strong>
                    <div class="mt-2 small text-muted">
                        <div><strong>Key ID:</strong> ${keyInfo.keyid || 'Unknown'}</div>
                        ${keyInfo.expires && keyInfo.expires !== 'Never' ? `<div><strong>Expires:</strong> ${keyInfo.expires}</div>` : ''}
                        ${keyInfo.uids ? `<div><strong>UIDs:</strong> ${keyInfo.uids.join(', ')}</div>` : ''}
                    </div>
                    <div class="mt-3">
                        <i class="bi bi-shield-check text-success me-1"></i>
                        <strong class="text-success">Key validated and ready for encryption</strong>
                    </div>
                </div>`;
            }

            // Update UI for successful local key
            updateSelectedKeyInfo(searchEmail);
            if (importBtn) {
                importBtn.innerHTML = `<i class="bi bi-check-circle me-2"></i>✓ Key Ready`;
                importBtn.disabled = true;
                importBtn.classList.remove('btn-outline-success');
                importBtn.classList.add('btn-success');
            }
            if (confirmBackupBtn) {
                confirmBackupBtn.disabled = false;
                confirmBackupBtn.style.display = 'inline-block';
            }

            return; // Exit early - we found the key locally
        }

        // Step 3: No local key found, search keyserver
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="d-flex align-items-center text-muted mb-2">
                <span class="me-2">Key not found locally</span>
            </div>
            <div class="d-flex align-items-center text-muted">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                🔍 Searching Ubuntu keyserver...
            </div>`;
        }

        await searchKeyserverOnly(searchEmail);

    } catch (error) {
        console.error("Local-first key check failed:", error);
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Key search failed. Please check your connection and try again.
                <br><small class="text-muted">Error: ${error.message}</small>
                <div class="mt-3">
                    <button class="btn btn-sm btn-outline-secondary" onclick="checkLocalKeysFirst('${searchEmail}')">
                        <i class="bi bi-arrow-clockwise me-1"></i>Try Again
                    </button>
                </div>
            </div>`;
        }
    }
}

/**
 * Search keyserver only (used after local check fails)
 */
async function searchKeyserverOnly(email) {
    const resultsContainer = document.getElementById("gpgKeyResults");
    const importBtn = document.getElementById("importKeyBtn");

    try {
        const response = await fetch("/backup/gpg/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: email })
        });

        const data = await response.json();

        if (!data.success || !data.keys || !data.keys.length) {
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>❌ No key found for ${email}</strong>
                    <div class="mt-2 small text-muted">
                        The key was not found locally or on the Ubuntu keyserver.
                    </div>
                    <div class="mt-3">
                        <strong>Suggestions:</strong>
                        <ul class="small mt-2">
                            <li>Verify the email address is correct</li>
                            <li>Ask the key owner to upload their key to a keyserver</li>
                            <li>Import the key manually if you have the key file</li>
                        </ul>
                    </div>
                </div>`;
            }
            return;
        }

        // Found keys on keyserver
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-info mb-3">
                <i class="bi bi-info-circle me-2"></i>
                <strong>✓ Found ${data.keys.length} key(s) on keyserver</strong> for <strong>${email}</strong>
                <div class="small text-muted mt-1">Select one to import:</div>
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

        // Reset import button for keyserver keys
        if (importBtn) {
            importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
            importBtn.disabled = true;
            importBtn.classList.remove('btn-success');
            importBtn.classList.add('btn-outline-success');
        }

    } catch (error) {
        console.error("Keyserver search failed:", error);
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Keyserver search failed. Please check your connection and try again.
                <br><small class="text-muted">Error: ${error.message}</small>
            </div>`;
        }
    }
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
 * Update the selected key info display
 */
function updateSelectedKeyInfo(email) {
    const encryptEmailSpan = document.getElementById("gpgEncryptEmail");
    const encryptEmailHidden = document.getElementById("gpgModalEmail");
    const selectedKeyInfo = document.getElementById("selectedKeyInfo");
    
    if (encryptEmailSpan) encryptEmailSpan.textContent = email;
    if (encryptEmailHidden) encryptEmailHidden.value = email;
    if (selectedKeyInfo) selectedKeyInfo.style.display = "flex";
}

/**
 * Initialize modal with email from main page
 */
export function initializeModalWithEmail(email) {
    const gpgModalEmailInput = document.getElementById("gpgModalEmail");
    const encryptEmailSpan = document.getElementById("gpgEncryptEmail");
    const selectedKeyInfo = document.getElementById("selectedKeyInfo");

    // Set the email in modal's hidden field
    if (gpgModalEmailInput) {
        gpgModalEmailInput.value = email;
    }
    
    // Show the email in the display
    if (encryptEmailSpan) {
        encryptEmailSpan.textContent = email;
    }
    
    // Show the selected key info section
    if (selectedKeyInfo) {
        selectedKeyInfo.style.display = "flex";
    }

    // Ensure modal integrity and bind handlers
    ensureModalButtonsIntegrity();
    bindModalEventHandlers();

    // Automatically start the local-first search
    checkLocalKeysFirst(email);
}

/**
 * Enhanced GPG key validation and import function
 */
export function importSelectedGPGKey() {
    if (!selectedKeyId) {
        console.warn("No GPG key selected for import.");
        return;
    }

    const importBtn = document.getElementById("importKeyBtn");
    const resultsContainer = document.getElementById("gpgKeyResults");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");

    // Show importing state
    if (importBtn) {
        importBtn.disabled = true;
        importBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span>Importing & Validating...`;
    }

    fetch("/backup/gpg/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key_id: selectedKeyId })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) {
            // Enhanced error handling for different types of GPG errors
            let errorMessage = data.error || 'Import failed';
            let errorDetails = data.details || '';
            
            // Check for specific error types
            if (errorMessage.includes('expired')) {
                errorMessage = `GPG Key Has Expired`;
                errorDetails = `The selected GPG key expired on ${extractExpirationDate(data.error)}. Please select a different key or ask the key owner to extend the expiration date.`;
            } else if (errorMessage.includes('revoked')) {
                errorMessage = `GPG Key Has Been Revoked`;
                errorDetails = `This key has been revoked and cannot be used for encryption. Please select a different key.`;
            } else if (errorMessage.includes('not found')) {
                errorMessage = `GPG Key Not Found`;
                errorDetails = `The selected key could not be found on the keyserver. It may have been removed or the keyserver may be temporarily unavailable.`;
            } else if (errorMessage.includes('network') || errorMessage.includes('timeout')) {
                errorMessage = `Network Error`;
                errorDetails = `Unable to connect to the keyserver. Please check your internet connection and try again.`;
            } else if (errorMessage.includes('invalid') || errorMessage.includes('malformed')) {
                errorMessage = `Invalid Key Data`;
                errorDetails = `The key data appears to be corrupted or invalid. Please try selecting a different key.`;
            }

            console.error("GPG import failed:", data);
            
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>${errorMessage}</strong>
                    <div class="mt-2 small text-muted">${errorDetails}</div>
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-secondary me-2" onclick="window.location.reload()">
                            <i class="bi bi-arrow-clockwise me-1"></i>Start Over
                        </button>
                        <button class="btn btn-sm btn-outline-primary" onclick="searchGPGKeys()">
                            <i class="bi bi-search me-1"></i>Search Again
                        </button>
                    </div>
                </div>`;
            }

            // Reset import button to allow retry
            if (importBtn) {
                importBtn.disabled = false;
                importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
            }
            return;
        }

        // Import successful
        console.log("GPG key imported successfully:", data);
        
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle me-2"></i>
                <strong>✓ Key imported and validated successfully!</strong>
                <div class="mt-2 small text-muted">
                    ${data.message || 'The GPG key has been imported and is ready for encryption.'}
                </div>
                <div class="mt-3">
                    <i class="bi bi-shield-check text-success me-1"></i>
                    <strong class="text-success">Ready to create encrypted backup</strong>
                </div>
            </div>`;
        }

        // Update UI for successful import
        const gpgModalEmailInput = document.getElementById("gpgModalEmail");
        const email = gpgModalEmailInput ? gpgModalEmailInput.value.trim() : '';
        updateSelectedKeyInfo(email);

        if (importBtn) {
            importBtn.innerHTML = `<i class="bi bi-check-circle me-2"></i>✓ Key Imported`;
            importBtn.disabled = true;
            importBtn.classList.remove('btn-outline-success');
            importBtn.classList.add('btn-success');
        }

        if (confirmBackupBtn) {
            confirmBackupBtn.disabled = false;
            confirmBackupBtn.style.display = 'inline-block';
        }
    })
    .catch(error => {
        console.error("GPG import request failed:", error);
        
        if (resultsContainer) {
            resultsContainer.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Import Request Failed</strong>
                <div class="mt-2 small text-muted">
                    Unable to communicate with the server. Please check your connection and try again.
                </div>
                <div class="mt-3">
                    <button class="btn btn-sm btn-outline-secondary" onclick="importSelectedGPGKey()">
                        <i class="bi bi-arrow-clockwise me-1"></i>Try Again
                    </button>
                </div>
            </div>`;
        }

        // Reset import button for retry
        if (importBtn) {
            importBtn.disabled = false;
            importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
        }
    });
}

/**
 * Utility function to extract expiration date from error messages
 */
function extractExpirationDate(errorMessage) {
    // Try to extract date patterns from error message
    const dateMatch = errorMessage.match(/(\d{4}-\d{2}-\d{2})|(\w+ \d{1,2}, \d{4})/);
    return dateMatch ? dateMatch[0] : 'an unknown date';
}

/**
 * Reset the GPG modal to initial state
 */
export function resetGPGModal() {
    const resultsContainer = document.getElementById("gpgKeyResults");
    const importBtn = document.getElementById("importKeyBtn");
    const confirmBackupBtn = document.getElementById("confirmCreateBackupBtn");
    const selectedKeyInfo = document.getElementById("selectedKeyInfo");
    const gpgModalEmailInput = document.getElementById("gpgModalEmail");

    // Reset global state
    selectedKeyId = null;

    // Reset UI elements
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }

    if (importBtn) {
        importBtn.disabled = true;
        importBtn.innerHTML = `<i class="bi bi-download me-2"></i>Import Selected Key`;
        importBtn.classList.remove('btn-success');
        importBtn.classList.add('btn-outline-success');
        importBtn.style.display = 'inline-block';
    }

    if (confirmBackupBtn) {
        confirmBackupBtn.disabled = true;
        confirmBackupBtn.style.display = 'none';
    }

    if (selectedKeyInfo) {
        selectedKeyInfo.style.display = 'none';
    }

    if (gpgModalEmailInput) {
        gpgModalEmailInput.value = '';
    }
}

/**
 * Handle GPG modal close and cleanup
 */
export function handleGPGModalClose() {
    // Clean up any ongoing operations
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }

    // Reset modal state
    resetGPGModal();
}

/**
 * GPG Modal Class for managing the backup modal workflow - FIXED
 */
export class GPGBackupModal {
    constructor(modalId) {
        this.modalId = modalId;
        this.modalElement = document.getElementById(modalId);
        this.bsModal = null;
        this.onConfirm = null;
        
        if (this.modalElement && typeof bootstrap !== 'undefined') {
            this.bsModal = new bootstrap.Modal(this.modalElement);
        }
    }

    show() {
        if (this.bsModal) {
            // Ensure modal integrity before showing
            ensureModalButtonsIntegrity();
            bindModalEventHandlers();
            this.bsModal.show();
        }
    }

    hide() {
        if (this.bsModal) {
            this.bsModal.hide();
        }
    }

    setEncryptionEmail(email) {
        // Initialize the modal with the email and start key search
        initializeModalWithEmail(email);
    }

    onModalShown() {
        // Called when modal is fully visible
        // Ensure buttons are properly positioned and functional
        ensureModalButtonsIntegrity();
        bindModalEventHandlers();
        
        // Auto-start key search if email is available
        const email = document.getElementById("gpgModalEmail")?.value ||
                     document.getElementById("gpgEmail")?.value;
        if (email) {
            checkLocalKeysFirst(email);
        }
    }

    setupEventListeners() {
        if (this.modalElement) {
            // Setup modal shown event
            this.modalElement.addEventListener('shown.bs.modal', () => {
                this.onModalShown();
            });

            // Setup modal close cleanup
            this.modalElement.addEventListener('hidden.bs.modal', () => {
                handleGPGModalClose();
            });
        }
    }
}

/**
 * Initialize GPG modal event listeners - ENHANCED
 */
export function initializeGPGModal() {
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeGPGModal);
        return;
    }

    // Ensure modal integrity on initialization
    setTimeout(() => {
        ensureModalButtonsIntegrity();
        bindModalEventHandlers();
    }, 100);

    // Setup auto-search for main page email input
    const mainPageEmailInput = document.getElementById("gpgEmail");
    if (mainPageEmailInput) {
        mainPageEmailInput.addEventListener('input', (e) => {
            const email = e.target.value.trim();
            if (email && !isValidEmail(email)) {
                mainPageEmailInput.setCustomValidity('Please enter a valid email address');
            } else {
                mainPageEmailInput.setCustomValidity('');
            }
        });
    }

    // Initialize modal class if available
    const modalElement = document.getElementById("gpgConfirmationModal");
    if (modalElement && !window.gpgModalInstance) {
        window.gpgModalInstance = new GPGBackupModal("gpgConfirmationModal");
        window.gpgModalInstance.setupEventListeners();
    }
}

/**
 * Validate email format for GPG key search
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// LEGACY: Original searchGPGKeys function - now calls local-first approach
export function searchGPGKeys(email = null) {
    return checkLocalKeysFirst(email);
}

// Auto-initialize when the script loads
document.addEventListener('DOMContentLoaded', initializeGPGModal);

// Make functions available globally for onclick handlers and external access
window.checkLocalKeysFirst = checkLocalKeysFirst;
window.searchGPGKeys = searchGPGKeys;
window.selectGPGKey = selectGPGKey;
window.importSelectedGPGKey = importSelectedGPGKey;
window.resetGPGModal = resetGPGModal;
window.initializeModalWithEmail = initializeModalWithEmail;
window.GPGBackupModal = GPGBackupModal;
window.handleConfirmBackup = handleConfirmBackup;
window.handleCancelBackup = handleCancelBackup;

// Export for module usage (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        GPGBackupModal,
        checkLocalKeysFirst,
        searchGPGKeys,
        selectGPGKey,
        importSelectedGPGKey,
        resetGPGModal,
        initializeModalWithEmail
    };
}