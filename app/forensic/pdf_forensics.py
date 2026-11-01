import os
from pathlib import Path
from typing import Dict, Any, Tuple, List, Optional
import fitz  # PyMuPDF
from PIL import Image
import numpy as np

SUSPICIOUS_PDF_PRODUCERS = [
    'openpdf', 'docscanner', 'camscanner', 'tapscanner', 'itext',
    'photoshop', 'illustrator', 'canva', 'gimp', 'inkscape', 'coreldraw',
    'quartz pdfcontext', 'pdf edit', 'ilovepdf', 'smallpdf', 'sejda',
    'online2pdf', 'pdf24', 'foxit', 'nitro', 'wondershare', 'abbyy',
    'pdfkit', 'wkhtmltopdf', 'cairosvg'
]

def analyze_pdf_structure(pdf_path: Path) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    PATH A: PDF-Native Structural and Metadata Forensics.
    Inspects catalog, fonts, embedded images, xref structure, creation/mod dates.
    """
    metadata = {
        'page_count': 0,
        'title': None,
        'author': None,
        'creator': None,
        'producer': None,
        'creation_date': None,
        'mod_date': None,
        'is_encrypted': False,
        'fonts': [],
        'font_count': 0,
        'images': [],
        'image_count': 0,
        'suspicious_producer_detected': False,
        'date_inconsistency': False,
        'has_javascript': False
    }

    try:
        doc = fitz.open(str(pdf_path))
        metadata['page_count'] = len(doc)
        metadata['is_encrypted'] = doc.is_encrypted

        # Document metadata
        meta = doc.metadata or {}
        metadata['title'] = meta.get('title')
        metadata['author'] = meta.get('author')
        metadata['creator'] = meta.get('creator')
        metadata['producer'] = meta.get('producer')
        metadata['creation_date'] = meta.get('creationDate')
        metadata['mod_date'] = meta.get('modDate')

        # Check date mismatch
        if metadata['creation_date'] and metadata['mod_date']:
            if metadata['creation_date'] != metadata['mod_date']:
                metadata['date_inconsistency'] = True

        # Check producer / creator for editing tool footprints
        for field in [metadata['producer'], metadata['creator']]:
            if field:
                f_lower = field.lower()
                for kw in SUSPICIOUS_PDF_PRODUCERS:
                    if kw in f_lower:
                        metadata['suspicious_producer_detected'] = True
                        break

        # Check filename for mobile scan / manipulation footprints
        fn_lower = pdf_path.name.lower()
        for kw in ['docscanner', 'camscanner', 'tapscanner', 'photoshop', 'forged', 'fake', 'manip']:
            if kw in fn_lower:
                metadata['suspicious_producer_detected'] = True
                break

        # Font & image inventory
        all_fonts = set()
        image_list = []
        for pno in range(len(doc)):
            page = doc[pno]
            # Fonts
            for font in page.get_fonts():
                # font is (xref, ext, type, basefont, name, encoding)
                if len(font) >= 4:
                    all_fonts.add(font[3])
            # Images
            for img in page.get_images():
                image_list.append({
                    'xref': img[0],
                    'width': img[2],
                    'height': img[3],
                    'colorspace': img[5]
                })

        metadata['fonts'] = sorted(list(all_fonts))
        metadata['font_count'] = len(all_fonts)
        metadata['images'] = image_list
        metadata['image_count'] = len(image_list)

        doc.close()
    except Exception as e:
        metadata['error'] = str(e)

    # Missing metadata or standard PDF converters are common for official e-documents.
    if metadata['suspicious_producer_detected']:
        meta_norm_score = 0.85
        meta_severity = 'HIGH_ANOMALY'
    elif metadata['date_inconsistency']:
        meta_norm_score = 0.35
        meta_severity = 'LOW_ANOMALY'
    else:
        meta_norm_score = 0.0
        meta_severity = 'NORMAL'

    features = {
        'metadata_editing_software_flag': 1.0 if metadata['suspicious_producer_detected'] else 0.0,
        'metadata_date_inconsistency': 1.0 if metadata['date_inconsistency'] else 0.0,
        'metadata_normalized_score': meta_norm_score,
        'metadata_severity': meta_severity
    }

    return metadata, features

def render_pdf_page_to_image(pdf_path: Path, page_num: int = 0, dpi: int = 200) -> Image.Image:
    """
    PATH B: Page Rasterization for downstream Computer Vision & ELA.
    Renders specified PDF page to a high-resolution PIL RGB Image.
    """
    doc = fitz.open(str(pdf_path))
    if page_num >= len(doc):
        page_num = 0
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return image
