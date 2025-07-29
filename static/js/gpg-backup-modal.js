// gpg-backup-modal.js - Local-First Implementation

// Variable to store the ID of the selected GPG key
let selectedKeyId = null;
let currentJobId = null; // Track the current backup job
let progressInterval = null; // Store the progress polling interval

/**
 * NEW: Local-first key checking function
 * Checks local keychain first, then searches keyserver if needed
 */
export async function checkLocalKeysFirst(email = null) {
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
 * LEGACY: Original searchGPGKeys function - now calls local-first approach
 * Kept for backward compatibility with any remaining calls
 */
export function searchGPGKeys(email = null) {
    return checkLocalKeysFirst(email);
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
 * NEW: Initialize modal with email from main page
 * This bridges the gap between main page #gpgEmail and modal #gpgModalEmail
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
 * Validate email format for GPG key search
 */
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Auto-search when email is entered (with debouncing)
 */
let searchTimeout;
export function handleEmailInput(email) {
    // Clear existing timeout
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }

    // Validate email format
    if (!isValidEmail(email)) {
        const resultsContainer = document.getElementById("gpgKeyResults");
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
        }
        return;
    }

    // Debounce the search (wait 500ms after user stops typing)
    searchTimeout = setTimeout(() => {
        checkLocalKeysFirst(email);
    }, 500);
}

/**
 * GPG Modal Class for managing the backup modal workflow
 */
export class GPGBackupModal {
    constructor(modalId) {
        this.modalId = modalId;
        this.modalElement = document.getElementById(modalId);
        this.bsModal = null;
        this.onConfirm = null; // Callback for when backup is confirmed
        
        if (this.modalElement && typeof bootstrap !== 'undefined') {
            this.bsModal = new bootstrap.Modal(this.modalElement);
        }
    }

    show() {
        if (this.bsModal) {
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
        // Auto-start key search if email is available
        const email = document.getElementById("gpgModalEmail")?.value ||
                     document.getElementById("gpgEmail")?.value;
        if (email) {
            checkLocalKeysFirst(email);
        }
    }

    setupEventListeners() {
        if (this.modalElement) {
            // Setup confirm backup button
            const confirmBtn = document.getElementById("confirmCreateBackupBtn");
            if (confirmBtn) {
                confirmBtn.addEventListener('click', () => {
                    if (this.onConfirm) {
                        this.onConfirm();
                    }
                });
            }

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
 * Initialize GPG modal event listeners
 */
export function initializeGPGModal() {
    // Setup auto-search for main page email input (optional)
    const mainPageEmailInput = document.getElementById("gpgEmail");
    if (mainPageEmailInput) {
        mainPageEmailInput.addEventListener('input', (e) => {
            // Optional: could provide real-time feedback on main page
            // For now, we'll just validate format
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