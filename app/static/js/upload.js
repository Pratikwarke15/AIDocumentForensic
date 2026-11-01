/**
 * upload.js — Self-contained IIFE for document upload page.
 * Handles: file selection confirmation, drag-and-drop, thumbnail,
 * submit button state, and multi-stage forensic progress modal.
 * No external dependencies. Safe to cache.
 */
(function () {
    'use strict';

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 B';
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    function init() {
        var dropZone        = document.getElementById('dropZone');
        var fileInput       = document.getElementById('document_file');
        var filePreview     = document.getElementById('filePreview');
        var fileNameSpan    = document.getElementById('fileNameSpan');
        var fileSizeSpan    = document.getElementById('fileSizeSpan');
        var fileThumbImg    = document.getElementById('fileThumbImg');
        var fileTypeBadge   = document.getElementById('fileTypeBadge');
        var dropZoneIcon    = document.getElementById('dropZoneIcon');
        var dropInstruction = document.getElementById('dropInstruction');
        var dropSubtext     = document.getElementById('dropSubtext');
        var fileSelBadge    = document.getElementById('fileSelectedBadge');
        var uploadForm      = document.getElementById('uploadForm');
        var submitBtn       = document.getElementById('submitBtn');
        var resetBtn        = document.getElementById('resetBtn');
        var progressModal   = document.getElementById('progressModal');
        var progressStatus  = document.getElementById('progressStatusText');

        if (!dropZone || !fileInput) return;

        // ─── File Processing ──────────────────────────────────────────
        function showFile(file) {
            if (!file) return;
            var ext = (file.name.split('.').pop() || '').toLowerCase();
            var size = formatBytes(file.size);

            // Text spans
            if (fileNameSpan)  fileNameSpan.textContent  = file.name;
            if (fileSizeSpan)  fileSizeSpan.textContent  = '(' + size + ')';
            if (fileTypeBadge) {
                fileTypeBadge.textContent = ext.toUpperCase();
                fileTypeBadge.className = 'badge ' + (ext === 'pdf' ? 'badge-danger' : 'badge-success');
            }
            if (fileSelBadge) fileSelBadge.style.display = 'inline-block';

            // Drop zone → confirmed state
            dropZone.style.borderStyle      = 'solid';
            dropZone.style.borderColor      = '#16a34a';
            dropZone.style.backgroundColor  = '#f0fdf4';
            if (dropZoneIcon)    dropZoneIcon.textContent    = ext === 'pdf' ? '📕' : '🖼️';
            if (dropInstruction) dropInstruction.innerHTML   =
                '&#x2705; <strong style="color:#166534">' + file.name + '</strong> attached';
            if (dropSubtext) dropSubtext.innerHTML =
                '<span style="color:#16a34a;font-weight:600">Size: ' + size + ' &nbsp;&bull;&nbsp; Click or drag to replace</span>';

            // Thumbnail
            if (fileThumbImg) {
                if (['jpg','jpeg','png','webp'].indexOf(ext) !== -1) {
                    var reader = new FileReader();
                    reader.onload = function (e) {
                        fileThumbImg.src = e.target.result;
                        fileThumbImg.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                } else {
                    fileThumbImg.src = '';
                    fileThumbImg.style.display = 'none';
                }
            }

            // Preview card
            if (filePreview) filePreview.style.display = 'flex';
        }

        function resetDropZone() {
            if (filePreview)     filePreview.style.display    = 'none';
            if (fileSelBadge)    fileSelBadge.style.display   = 'none';
            if (fileThumbImg)    { fileThumbImg.src = ''; fileThumbImg.style.display = 'none'; }
            dropZone.style.borderStyle     = 'dashed';
            dropZone.style.borderColor     = '#94a3b8';
            dropZone.style.backgroundColor = '#f8fafc';
            if (dropZoneIcon)    dropZoneIcon.textContent    = '📄';
            if (dropInstruction) dropInstruction.textContent = 'Drag and drop document file here, or click to browse';
            if (dropSubtext)     dropSubtext.textContent     = 'Supported: PDF, JPG, JPEG, PNG (Max 16 MB)';
        }

        // ─── Wire events ──────────────────────────────────────────────
        fileInput.addEventListener('change', function (e) {
            if (e.target.files && e.target.files.length > 0) showFile(e.target.files[0]);
        });

        // Click on zone (not on labels/inputs) opens picker
        dropZone.addEventListener('click', function (e) {
            if (e.target === dropZone || e.target.id === 'dropZoneIcon' ||
                e.target.id === 'dropInstruction' || e.target.id === 'dropSubtext') {
                fileInput.click();
            }
        });

        // Reset button
        if (resetBtn) resetBtn.addEventListener('click', function () { setTimeout(resetDropZone, 30); });

        // Drag-and-drop
        ['dragenter', 'dragover'].forEach(function (ev) {
            dropZone.addEventListener(ev, function (e) {
                e.preventDefault(); e.stopPropagation();
                dropZone.style.borderColor     = '#0284c7';
                dropZone.style.backgroundColor = '#e0f2fe';
            }, false);
        });
        ['dragleave', 'drop'].forEach(function (ev) {
            dropZone.addEventListener(ev, function (e) {
                e.preventDefault(); e.stopPropagation();
                if (!fileInput.files || fileInput.files.length === 0) {
                    dropZone.style.borderColor     = '#94a3b8';
                    dropZone.style.backgroundColor = '#f8fafc';
                }
            }, false);
        });
        dropZone.addEventListener('drop', function (e) {
            var dt = e.dataTransfer;
            if (dt && dt.files && dt.files.length > 0) {
                fileInput.files = dt.files;
                showFile(dt.files[0]);
            }
        });

        // ─── Submit → progress modal ───────────────────────────────────
        if (uploadForm) {
            uploadForm.addEventListener('submit', function () {
                if (!fileInput.files || fileInput.files.length === 0) return;
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.textContent = '⏳ Uploading & Analyzing Document...';
                }
                if (progressModal) {
                    progressModal.classList.add('open');
                    progressModal.style.display = 'flex';
                    var stages = [
                        'Validating document type & algorithmic structure rules...',
                        'Screening image luminance, saturation & non-document patterns...',
                        'Querying official government database records...',
                        'Running Error Level Analysis (ELA) at Q95 compression...',
                        'Measuring spatial noise residuals & JPEG block artifacts...',
                        'Synthesizing 3-Pillar authenticity score & verdict...'
                    ];
                    var idx = 0;
                    var interval = setInterval(function () {
                        if (progressStatus && idx < stages.length) {
                            progressStatus.textContent = stages[idx++];
                        }
                        if (idx >= stages.length) clearInterval(interval);
                    }, 1300);
                }
            });
        }
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for inline usage if needed
    window._uploaderInit = init;
})();
