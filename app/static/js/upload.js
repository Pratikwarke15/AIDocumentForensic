document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('document_file');
    const filePreview = document.getElementById('filePreview');
    const fileNameSpan = document.getElementById('fileNameSpan');
    const fileSizeSpan = document.getElementById('fileSizeSpan');
    const uploadForm = document.getElementById('uploadForm');
    const progressModal = document.getElementById('progressModal');
    const progressStatusText = document.getElementById('progressStatusText');

    if (!dropZone || !fileInput) return;

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
        if (files.length > 0) {
            fileInput.files = files;
            updatePreview(files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            updatePreview(fileInput.files[0]);
        }
    });

    function updatePreview(file) {
        if (!filePreview || !fileNameSpan || !fileSizeSpan) return;
        fileNameSpan.textContent = file.name;
        const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
        fileSizeSpan.textContent = ( MB - );
        filePreview.style.display = 'flex';
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', () => {
            if (fileInput.files.length > 0 && progressModal) {
                progressModal.classList.add('open');
                
                // Animate pipeline stages
                const stages = [
                    "Validating magic bytes & computing SHA-256 hash...",
                    "Querying local verification registry records...",
                    "Executing Error Level Analysis (ELA) at Q95...",
                    "Analyzing noise residuals and JPEG blockiness...",
                    "Extracting 28+ dimensional numerical feature vector...",
                    "Evaluating Random Forest classifier probabilities...",
                    "Compiling 5-page official forensic PDF dossier..."
                ];
                let idx = 0;
                setInterval(() => {
                    if (idx < stages.length) {
                        progressStatusText.textContent = stages[idx];
                        idx++;
                    }
                }, 1200);
            }
        });
    }
});
