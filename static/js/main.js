document.addEventListener('DOMContentLoaded', function() {
    
    // File Upload Preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Show file info
                const fileInfo = document.createElement('div');
                fileInfo.className = 'alert alert-info mt-2';
                fileInfo.innerHTML = `
                    <strong>File dipilih:</strong> ${file.name} 
                    <small>(${formatFileSize(file.size)})</small>
                `;
                
                // Remove previous info if exists
                const existingInfo = input.parentElement.querySelector('.alert-info');
                if (existingInfo) existingInfo.remove();
                
                input.parentElement.appendChild(fileInfo);
            }
        });
    });
    
    // File Upload Form Validation
    const uploadForms = document.querySelectorAll('form[action*="upload"]');
    uploadForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const fileInput = form.querySelector('input[type="file"]');
            
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                showAlert('Please select a file first', 'warning');
                return false;
            }
            
            const file = fileInput.files[0];
            const maxSize = 50 * 1024 * 1024; // 50MB
            
            if (file.size > maxSize) {
                e.preventDefault();
                showAlert('The file size is too large. Maximum 50MB', 'error');
                return false;
            }
            
            // Show loading
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Uploading...';
            }
        });
    });
    
});


// =====================================
// FEEDBACK FORM HANDLER
// =====================================

// Feedback Form Validation
const feedbackForms = document.querySelectorAll('form[action*="feedback"]');
feedbackForms.forEach(form => {
    form.addEventListener('submit', function(e) {
        const textarea = form.querySelector('textarea');
        const action = e.submitter?.value || form.querySelector('input[name="action"]')?.value;
        
        if (action === 'revision' && (!textarea.value || textarea.value.trim() === '')) {
            e.preventDefault();
            showAlert('Please provide comments for revisions', 'warning');
            textarea.focus();
            return false;
        }
        
        if (action === 'approve') {
            if (!confirm('Are you sure you want to approve this project? The project will be considered complete')) {
                e.preventDefault();
                return false;
            }
        }
    });
});


// =====================================
// DESIGN PREVIEW MODAL
// =====================================

function previewDesign(imageSrc, filename) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'previewModal';
    modal.innerHTML = `
        <div class="modal-dialog modal-xl modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${filename}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body text-center">
                    <img src="${imageSrc}" class="img-fluid" alt="${filename}">
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Tutup</button>
                    <a href="${imageSrc}" download="${filename}" class="btn btn-primary">Download</a>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    
    // Remove modal after hidden
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
    });
}

// Add preview button handlers
document.addEventListener('DOMContentLoaded', function() {
    const previewButtons = document.querySelectorAll('[data-preview]');
    previewButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const imageSrc = this.getAttribute('data-preview');
            const filename = this.getAttribute('data-filename') || 'Design Preview';
            previewDesign(imageSrc, filename);
        });
    });
});


// =====================================
// UTILITY FUNCTIONS
// =====================================

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function showAlert(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };
    
    const alert = document.createElement('div');
    alert.className = `alert ${alertClass[type]} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
    alert.style.zIndex = '9999';
    alert.style.minWidth = '300px';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Link copied successfully!', 'success');
    }).catch(() => {
        showAlert('Failed to copy link', 'error');
    });
}


// =====================================
// PROGRESS BAR ANIMATION
// =====================================

document.addEventListener('DOMContentLoaded', function() {
    const progressBars = document.querySelectorAll('.progress-bar');
    
    progressBars.forEach(bar => {
        const targetWidth = bar.style.width;
        bar.style.width = '0%';
        
        setTimeout(() => {
            bar.style.transition = 'width 1s ease-in-out';
            bar.style.width = targetWidth;
        }, 100);
    });
});


// =====================================
// CHARACTER COUNTER FOR TEXTAREA
// =====================================

document.addEventListener('DOMContentLoaded', function() {
    const textareas = document.querySelectorAll('textarea[maxlength]');
    
    textareas.forEach(textarea => {
        const maxLength = textarea.getAttribute('maxlength');
        
        // Create counter element
        const counter = document.createElement('small');
        counter.className = 'text-muted float-end';
        counter.innerHTML = `0 / ${maxLength}`;
        
        // Insert after textarea
        textarea.parentElement.appendChild(counter);
        
        // Update counter on input
        textarea.addEventListener('input', function() {
            const currentLength = this.value.length;
            counter.innerHTML = `${currentLength} / ${maxLength}`;
            
            if (currentLength >= maxLength * 0.9) {
                counter.classList.add('text-warning');
            } else {
                counter.classList.remove('text-warning');
            }
        });
    });
});


// =====================================
// DEADLINE COUNTDOWN
// =====================================

function updateDeadlineCountdown() {
    const deadlineElements = document.querySelectorAll('[data-deadline]');
    
    deadlineElements.forEach(element => {
        const deadline = new Date(element.getAttribute('data-deadline'));
        const now = new Date();
        const diff = deadline - now;
        
        if (diff > 0) {
            const days = Math.floor(diff / (1000 * 60 * 60 * 24));
            const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            
            if (days > 0) {
                element.textContent = `${days} days left`;
            } else if (hours > 0) {
                element.textContent = `${hours} hours left`;
            } else {
                element.textContent = 'Less than 1 hour';
            }
            
            // Add warning class if deadline is soon
            if (days <= 1) {
                element.classList.add('text-danger', 'fw-bold');
            }
        } else {
            element.textContent = 'Deadline missed';
            element.classList.add('text-danger', 'fw-bold');
        }
    });
}

// Update countdown every minute
document.addEventListener('DOMContentLoaded', function() {
    updateDeadlineCountdown();
    setInterval(updateDeadlineCountdown, 60000);
});


// =====================================
// SEARCH FUNCTIONALITY 
// =====================================

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.querySelector('input[placeholder*="Cari"]');
    
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const projectCards = document.querySelectorAll('.project-card');
            
            projectCards.forEach(card => {
                const title = card.querySelector('h3')?.textContent.toLowerCase() || '';
                const client = card.querySelector('.text-muted')?.textContent.toLowerCase() || '';
                
                if (title.includes(searchTerm) || client.includes(searchTerm)) {
                    card.closest('.col-12').style.display = '';
                } else {
                    card.closest('.col-12').style.display = 'none';
                }
            });
        });
    }
});