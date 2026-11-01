import io
import pytest
import fitz
from app.services.file_service import FileService, FileValidationError
from PIL import Image

def test_file_validation_valid_jpeg(tmp_path):
    service = FileService(tmp_path)
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, 'JPEG')
    buf.seek(0)
    buf.filename = 'test_document.jpg'

    res = service.validate_and_preserve_file(buf)
    assert res['file_type'] == 'jpeg'
    assert res['mime_type'] == 'image/jpeg'
    assert len(res['sha256']) == 64

def test_file_validation_valid_pdf(tmp_path):
    service = FileService(tmp_path)
    doc = fitz.open()
    page = doc.new_page(width=300, height=300)
    page.insert_text((50, 50), "Test PDF Document")
    buf = io.BytesIO(doc.tobytes())
    doc.close()
    buf.seek(0)
    buf.filename = 'test_doc.pdf'

    res = service.validate_and_preserve_file(buf)
    assert res['file_type'] == 'pdf'
    assert res['mime_type'] == 'application/pdf'
    assert len(res['sha256']) == 64

def test_file_validation_invalid_signature(tmp_path):
    service = FileService(tmp_path)
    buf = io.BytesIO(b'NOT A REAL JPEG OR PDF CONTENT')
    buf.filename = 'fake.jpg'

    with pytest.raises(FileValidationError) as exc:
        service.validate_and_preserve_file(buf)
    assert 'File signature verification failed' in str(exc.value)

def test_file_validation_unsupported_extension(tmp_path):
    service = FileService(tmp_path)
    buf = io.BytesIO(b'%PDF-1.4 dummy content')
    buf.filename = 'script.exe'

    with pytest.raises(FileValidationError) as exc:
        service.validate_and_preserve_file(buf)
    assert 'Unsupported file format' in str(exc.value)
