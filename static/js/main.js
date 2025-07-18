// Copy to clipboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Copy button functionality
    document.querySelectorAll('.copy-btn').forEach(button => {
        button.addEventListener('click', function() {
            const textToCopy = this.dataset.text;
            
            // Use the modern clipboard API if available
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    showCopySuccess(this);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                    fallbackCopy(textToCopy);
                    showCopySuccess(this);
                });
            } else {
                // Fallback for older browsers
                fallbackCopy(textToCopy);
                showCopySuccess(this);
            }
        });
    });

    // Show copy success feedback
    function showCopySuccess(button) {
        const originalContent = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i>';
        
        // Handle Tailwind CSS classes
        if (button.classList.contains('bg-blue-600')) {
            button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            button.classList.add('bg-green-600');
            
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.classList.remove('bg-green-600');
                button.classList.add('bg-blue-600', 'hover:bg-blue-700');
            }, 1000);
        } else {
            // Fallback for Bootstrap classes
            button.classList.add('btn-success');
            button.classList.remove('btn-outline-primary', 'btn-outline-success');
            
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-primary');
            }, 1000);
        }
    }

    // Fallback copy method for older browsers
    function fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
        } catch (err) {
            console.error('Fallback copy failed: ', err);
        }
        
        document.body.removeChild(textArea);
    }

    // Auto-hide alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        if (!alert.classList.contains('alert-info')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });

    // Confirm deletion forms
    document.querySelectorAll('form[action*="delete"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            const isEmail = this.action.includes('delete-email');
            const itemType = isEmail ? 'email address' : 'phone number';
            
            if (!confirm(`Are you sure you want to delete this ${itemType}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });

    // Add loading state to generation buttons
    document.querySelectorAll('form[action*="generate"]').forEach(form => {
        form.addEventListener('submit', function() {
            const button = this.querySelector('button[type="submit"]');
            const originalContent = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Generating...';
            button.disabled = true;
            
            // Add loading state styling for Tailwind
            if (button.classList.contains('bg-blue-600')) {
                button.classList.remove('hover:bg-blue-700');
                button.classList.add('opacity-75', 'cursor-not-allowed');
            }
            
            // Re-enable after 5 seconds in case of error
            setTimeout(() => {
                button.innerHTML = originalContent;
                button.disabled = false;
                button.classList.remove('opacity-75', 'cursor-not-allowed');
                if (button.classList.contains('bg-blue-600')) {
                    button.classList.add('hover:bg-blue-700');
                }
            }, 5000);
        });
    });

    // Time remaining updates
    updateTimeRemaining();
    setInterval(updateTimeRemaining, 60000); // Update every minute

    function updateTimeRemaining() {
        document.querySelectorAll('[data-expires]').forEach(element => {
            const expiresAt = new Date(element.dataset.expires);
            const now = new Date();
            const diff = expiresAt - now;
            
            if (diff <= 0) {
                element.textContent = 'Expired';
                element.classList.add('text-danger');
            } else {
                const hours = Math.floor(diff / (1000 * 60 * 60));
                const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
                
                if (hours > 0) {
                    element.textContent = `${hours}h ${minutes}m remaining`;
                } else {
                    element.textContent = `${minutes}m remaining`;
                }
                
                if (hours < 1) {
                    element.classList.add('text-warning');
                }
            }
        });
    }
});

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast element after it's hidden
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// New Functions for Single Page Actions
function refreshEmails() {
    const refreshIcon = document.querySelector('.refresh-icon');
    refreshIcon.classList.add('fa-spin');
    
    // Reload the page to get fresh emails
    location.reload();
}

function changeEmail() {
    if (confirm('Generate a new email address? This will delete the current one.')) {
        // Submit the generate form
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/generate-email';
        document.body.appendChild(form);
        form.submit();
    }
}

function deleteEmail(emailId) {
    if (confirm('Delete this email address? All received emails will be lost.')) {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/delete-email/${emailId}`;
        document.body.appendChild(form);
        form.submit();
    }
}

// Toggle email content visibility
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.toggle-email').forEach(button => {
        button.addEventListener('click', function() {
            const messageId = this.dataset.messageId;
            const content = document.getElementById(`email-content-${messageId}`);
            const icon = this.querySelector('i');
            
            if (content.classList.contains('hidden')) {
                content.classList.remove('hidden');
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                content.classList.add('hidden');
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
});
