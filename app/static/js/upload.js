// Document Upload & Live Confirmation Handler
(function() {
    function initUploader() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('document_file');
        const filePreview = document.getElementById('filePreview');
        const fileNameSpan = document.getElementById('fileNameSpan');
        const fileSizeSpan = document.getElementById('fileSizeSpan');
        const fileThumbImg = document.getElementById('fileThumbImg');
        const fileTypeBadge = document.getElementById('fileTypeBadge');
        const uploadForm = document.getElementById('uploadForm');
        const submitBtn = document.getElementById('submitBtn');
        const progressModal = document.getElementById('progressModal');
        const progressStatusText = document.getElementById('progressStatusText');

        if (!dropZone || !fileInput) return;

        function formatBytes(bytes, decimals = 1) {
            if (!bytes || bytes === 0) return '0 B';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }

        function handleFile(file) {
            if (!file) return;

            // Update text details
            if (fileNameSpan) fileNameSpan.textContent = file.name;
            if (fileSizeSpan) fileSizeSpan.textContent = '(' + formatBytes(file.size) + ')';

            const ext = file.name.split('.').pop().toLowerCase();
            if (fileTypeBadge) {
                fileTypeBadge.textContent = ext.toUpperCase();
                fileTypeBadge.className = 'badge ' + (ext === 'pdf' ? 'badge-danger' : 'badge-success');
            }

            // Image Thumbnail
            if (fileThumbImg) {
                if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        fileThumbImg.src = e.target.result;
                        fileThumbImg.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                } else {
                    fileThumbImg.src = '';
                    fileThumbImg.style.display = 'none';
                }
            }

            // Reveal Preview Box
            if (filePreview) {
                filePreview.style.display = 'flex';
            }

            // DropZone visual change to green confirmation state
            dropZone.style.borderColor = '#16a34a';
            dropZone.style.backgroundColor = '#f0fdf4';
            const instruction = dropZone.querySelector('.drop-instruction');
            if (instruction) {
                instruction.innerHTML = '✓ <strong style="color: #166534;">' + file.name + '</strong> selected (' + formatBytes(file.size) + ')';
            }
        }

        // Global hook for convenience
        window.handleDocumentFileSelection = handleFile;

        // File input change
        fileInput.addEventListener('change', function(e) {
            if (e.target.files && e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });

        // Click on dropzone triggers file input
        dropZone.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                fileInput.click();
            }
        });

        // Drag & Drop
        ['dragenter', 'dragover'].forEach(function(eventName) {
            dropZone.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.add('dragover');
                dropZone.style.borderColor = '#0284c7';
                dropZone.style.backgroundColor = '#e0f2fe';
            }, false);
        });

        ['dragleave', 'drop'].forEach(function(eventName) {
            dropZone.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
                dropZone.classList.remove('dragover');
                if (fileInput.files && fileInput.files.length > 0) {
                    dropZone.style.borderColor = '#16a34a';
                    dropZone.style.backgroundColor = '#f0fdf4';
                } else {
                    dropZone.style.borderColor = '#94a3b8';
                    dropZone.style.backgroundColor = '#f8fafc';
                }
            }, false);
        });

        dropZone.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            if (dt && dt.files && dt.files.length > 0) {
                fileInput.files = dt.files;
                handleFile(dt.files[0]);
            }
        });

        // Form Submit
        if (uploadForm) {
            uploadForm.addEventListener('submit', function(e) {
                if (fileInput.files && fileInput.files.length > 0) {
                    if (submitBtn) {
                        submitBtn.disabled = true;
                        submitBtn.innerHTML = '⏳ Uploading & Analyzing Document...';
                    }
                    if (progressModal) {
                        progressModal.classList.add('open');
                        progressModal.style.display = 'flex';

                        const stages = [
                            "Validating document type & semantic template rules...",
                            "Screening image features against non-document criteria...",
                            "Querying official local database records...",
                            "Running Error Level Analysis (ELA) at Q95 compression...",
                            "Measuring spatial noise residuals & JPEG grid artifacts...",
                            "Computing multi-pillar authenticity score & generating verdict..."
                        ];
                        let idx = 0;
                        setInterval(function() {
                            if (idx < stages.length && progressStatusText) {
                                progressStatusText.textContent = stages[idx];
                                idx++;
                            }
                        }, 1200);
                    }
                }
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initUploader);
    } else {
        initUploader();
    }
})();
