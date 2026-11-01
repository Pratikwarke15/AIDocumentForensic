import os
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional
from werkzeug.utils import secure_filename
from PIL import Image
import fitz

MAGIC_BYTES = {
    'jpeg': b'\xFF\xD8\xFF',
    'png': b'\x89PNG\r\n\x1a\n',
    'pdf': b'%PDF-'
}

class FileValidationError(Exception):
    pass

class FileService:
    def __init__(self, storage_dir: Path):
        self.storage_dir = Path(storage_dir)
        self.originals_dir = self.storage_dir / 'originals'
        self.processed_dir = self.storage_dir / 'processed'
        self.temp_dir = self.storage_dir / 'temp'
        
        for d in [self.originals_dir, self.processed_dir, self.temp_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def validate_and_preserve_file(self, file_storage, max_size_bytes: int = 16 * 1024 * 1024) -> Dict[str, Any]:
        """
        Stage 1 & 2: File Validation and Cryptographic Preservation.
        Validates magic bytes, calculates SHA-256, stores immutable original.
        """
        if not file_storage or not file_storage.filename:
            raise FileValidationError("No file uploaded or filename is empty.")

        original_filename = secure_filename(file_storage.filename)
        ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''
        
        if ext not in {'jpg', 'jpeg', 'png', 'pdf'}:
            raise FileValidationError(f"Unsupported file format '.{ext}'. Supported formats: PDF, JPG, JPEG, PNG.")

        # Read content to check size and magic bytes
        content = file_storage.read()
        file_size = len(content)

        if file_size == 0:
            raise FileValidationError("The uploaded file is empty (0 bytes).")
        if file_size > max_size_bytes:
            raise FileValidationError(f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed limit (16 MB).")

        # Validate magic bytes / file signatures
        detected_type = None
        if content.startswith(b'\xFF\xD8\xFF'):
            detected_type = 'jpeg'
            mime_type = 'image/jpeg'
        elif content.startswith(b'\x89PNG\r\n\x1a\n'):
            detected_type = 'png'
            mime_type = 'image/png'
        elif content.startswith(b'%PDF-'):
            detected_type = 'pdf'
            mime_type = 'application/pdf'
        else:
            raise FileValidationError("File signature verification failed: File contents do not match genuine JPEG, PNG, or PDF format.")

        # Verify extension matches detected format
        if detected_type in {'jpeg', 'jpg'} and ext not in {'jpg', 'jpeg'}:
            raise FileValidationError("File extension does not match its internal binary signature.")
        if detected_type == 'png' and ext != 'png':
            raise FileValidationError("File extension does not match its internal PNG signature.")
        if detected_type == 'pdf' and ext != 'pdf':
            raise FileValidationError("File extension does not match its internal PDF signature.")

        # Cryptographic Hash (SHA-256)
        sha256 = hashlib.sha256(content).hexdigest()

        # Save immutable original
        saved_filename = f"{sha256}.{ext}"
        saved_path = self.originals_dir / saved_filename
        if not saved_path.exists():
            with open(saved_path, 'wb') as f:
                f.write(content)

        # Integrity & Readability Test
        try:
            if detected_type in {'jpeg', 'png'}:
                with Image.open(saved_path) as img:
                    img.verify()
            elif detected_type == 'pdf':
                doc = fitz.open(str(saved_path))
                if len(doc) == 0:
                    doc.close()
                    raise FileValidationError("PDF document contains 0 pages.")
                doc.close()
        except Exception as e:
            if saved_path.exists():
                os.remove(saved_path)
            raise FileValidationError(f"File corrupted or unreadable: {str(e)}")

        return {
            'original_filename': original_filename,
            'extension': ext,
            'file_type': detected_type,
            'mime_type': mime_type,
            'file_size': file_size,
            'sha256': sha256,
            'saved_path': str(saved_path)
        }
