document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------------------------------
    // 1. Tab Switching Handlers
    // -----------------------------------------------------------------
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            const parent = btn.closest('.tabs-container') || document;
            
            parent.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            parent.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const targetContent = document.getElementById(targetId);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        });
    });

    // -----------------------------------------------------------------
    // 2. Modal Open / Close Handlers
    // -----------------------------------------------------------------
    document.querySelectorAll('[data-modal-target]').forEach(trigger => {
        trigger.addEventListener('click', () => {
            const targetId = trigger.getAttribute('data-modal-target');
            const modal = document.getElementById(targetId);
            if (modal) modal.classList.add('open');
        });
    });

    document.querySelectorAll('[data-modal-close]').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            const modal = closeBtn.closest('.modal-overlay');
            if (modal) modal.classList.remove('open');
        });
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('open');
            }
        });
    });

    // -----------------------------------------------------------------
    // 3. Document Upload Confirmation, Drag-and-Drop & Live Preview
    // -----------------------------------------------------------------
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('document_file');
    const filePreview = document.getElementById('filePreview');
    const fileNameSpan = document.getElementById('fileNameSpan');
    const fileSizeSpan = document.getElementById('fileSizeSpan');
    const fileThumbImg = document.getElementById('fileThumbImg');
    const fileTypeBadge = document.getElementById('fileTypeBadge');
    const uploadForm = document.getElementById('uploadForm');
    const progressModal = document.getElementById('progressModal');
    const progressStatusText = document.getElementById('progressStatusText');

    function formatBytes(bytes, decimals = 1) {
        if (!+bytes) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
    }

    function handleFileSelection(file) {
        if (!file) return;

        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = `(${formatBytes(file.size)})`;

        const ext = file.name.split('.').pop().toLowerCase();
        if (fileTypeBadge) {
            fileTypeBadge.textContent = ext.toUpperCase();
        }

        // Live Thumbnail preview for images
        if (fileThumbImg) {
            if (['jpg', 'jpeg', 'png'].includes(ext)) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    fileThumbImg.src = e.target.result;
                    fileThumbImg.style.display = 'block';
                };
                reader.readAsDataURL(file);
            } else if (ext === 'pdf') {
                fileThumbImg.src = '';
                fileThumbImg.style.display = 'none';
            }
        }

        if (filePreview) {
            filePreview.style.display = 'flex';
        }
        if (dropZone) {
            dropZone.style.borderColor = '#16a34a';
            dropZone.style.backgroundColor = '#f0fdf4';
            const instruction = dropZone.querySelector('.drop-instruction');
            if (instruction) {
                instruction.innerHTML = `✓ <strong>${file.name}</strong> selected (${formatBytes(file.size)})`;
            }
        }
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    if (dropZone) {
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            if (files && files.length > 0) {
                fileInput.files = files;
                handleFileSelection(files[0]);
            }
        }, false);
    }

    // -----------------------------------------------------------------
    // 4. Verification Form Submission & Multi-Stage Animation
    // -----------------------------------------------------------------
    if (uploadForm && progressModal) {
        uploadForm.addEventListener('submit', () => {
            progressModal.classList.add('open');
            
            const steps = [
                'Validating file integrity & computing SHA-256...',
                'Executing semantic document template & layout validator...',
                'Verifying citizen details against official registry database...',
                'Performing multi-signal digital forensics (ELA, noise, compression)...'
            ];
            let currentStep = 0;
            const interval = setInterval(() => {
                currentStep++;
                if (currentStep < steps.length && progressStatusText) {
                    progressStatusText.textContent = steps[currentStep];
                } else {
                    clearInterval(interval);
                }
            }, 800);
        });
    }
});
