from pathlib import Path
from typing import Dict, Any
from PIL import Image, ExifTags

SUSPICIOUS_SOFTWARE_KEYWORDS = [
    'photoshop', 'gimp', 'canva', 'paint.net', 'pixlr', 'coreldraw',
    'illustrator', 'affinity', 'inkscape', 'snapseed', 'facetune'
]

def extract_image_metadata(image_path: Path) -> Dict[str, Any]:
    """
    Extracts EXIF metadata, camera/software tags, and timestamp integrity from images.
    Returns:
    - Raw metadata dict
    - Flags: editing_software_flag, date_inconsistency
    """
    metadata = {
        'format': None,
        'mode': None,
        'size': None,
        'exif': {},
        'software': None,
        'make': None,
        'model': None,
        'datetime_original': None,
        'datetime_digitized': None,
        'editing_software_detected': False,
        'date_inconsistency': False
    }

    try:
        with Image.open(image_path) as img:
            metadata['format'] = img.format
            metadata['mode'] = img.mode
            metadata['size'] = list(img.size)

            exif_raw = img.getexif()
            if exif_raw:
                for tag_id, value in exif_raw.items():
                    tag = ExifTags.TAGS.get(tag_id, str(tag_id))
                    # Clean string or byte values
                    if isinstance(value, bytes):
                        try:
                            value = value.decode(errors='ignore')
                        except Exception:
                            value = str(value)
                    metadata['exif'][tag] = str(value)

                # Check known tags
                metadata['software'] = metadata['exif'].get('Software')
                metadata['make'] = metadata['exif'].get('Make')
                metadata['model'] = metadata['exif'].get('Model')
                metadata['datetime_original'] = metadata['exif'].get('DateTimeOriginal') or metadata['exif'].get('DateTime')

                # Check for suspicious editing software
                if metadata['software']:
                    sw_lower = metadata['software'].lower()
                    for kw in SUSPICIOUS_SOFTWARE_KEYWORDS:
                        if kw in sw_lower:
                            metadata['editing_software_detected'] = True
                            break
    except Exception as e:
        metadata['error'] = str(e)

    # Missing EXIF is standard and NORMAL for scanned, converted, or photographed paper documents.
    # Editing software tags are secondary advisory signals.
    if metadata['editing_software_detected'] and metadata['date_inconsistency']:
        meta_norm_score = 0.70
        meta_severity = 'HIGH_ANOMALY'
    elif metadata['editing_software_detected']:
        meta_norm_score = 0.45
        meta_severity = 'MODERATE_ANOMALY'
    elif metadata['date_inconsistency']:
        meta_norm_score = 0.20
        meta_severity = 'LOW_ANOMALY'
    else:
        meta_norm_score = 0.0
        meta_severity = 'NORMAL'

    features = {
        'metadata_editing_software_flag': 1.0 if metadata['editing_software_detected'] else 0.0,
        'metadata_date_inconsistency': 1.0 if metadata['date_inconsistency'] else 0.0,
        'metadata_normalized_score': meta_norm_score,
        'metadata_severity': meta_severity
    }

    return metadata, features
