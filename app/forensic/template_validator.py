import re
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple, Optional

# =====================================================================
# 1. Official Mathematical Checksum Algorithms
# =====================================================================

# Verhoeff algorithm multiplication table d
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Verhoeff permutation table p
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_verhoeff_checksum(number_str: str) -> bool:
    """
    Validates a number string using the Verhoeff checksum algorithm
    (Mandatory algorithmic standard used by UIDAI for 12-digit Aadhaar numbers).
    """
    digits = ''.join(c for c in number_str if c.isdigit())
    if len(digits) != 12:
        return False

    c = 0
    for idx, char in enumerate(reversed(digits)):
        digit = int(char)
        c = _VERHOEFF_D[c][_VERHOEFF_P[idx % 8][digit]]
    return c == 0

def validate_pan_structure(pan_str: str, holder_name: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validates Indian Permanent Account Number (PAN) structure and 5th-character rule:
    - Exactly 10 characters: 5 letters + 4 digits + 1 letter
    - 4th character denotes entity status (P = Individual, C = Company, etc.)
    - 5th character must match the initial of the cardholder's surname/last name
    """
    clean_pan = ''.join(c for c in pan_str if c.isalnum()).upper()
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', clean_pan):
        return False, f"Invalid PAN format '{clean_pan}'. Must be 5 uppercase letters, 4 digits, 1 letter."

    valid_types = {'P', 'C', 'H', 'F', 'A', 'T', 'B', 'L', 'J', 'G'}
    pan_type_char = clean_pan[3]
    if pan_type_char not in valid_types:
        return False, f"Invalid PAN taxpayer status code '{pan_type_char}'. Expected one of {sorted(list(valid_types))}."

    # Validate 5th character against surname if holder name is available
    if holder_name and pan_type_char == 'P':
        name_parts = [p.strip() for p in holder_name.strip().split() if p.strip()]
        if name_parts:
            surname = name_parts[-1].upper()
            expected_initial = surname[0]
            if clean_pan[4] != expected_initial:
                return False, (
                    f"PAN 5th character '{clean_pan[4]}' does not match holder surname initial '{expected_initial}' "
                    f"from provided name '{holder_name}'."
                )

    return True, "Valid PAN structure and taxpayer code."

def validate_driving_licence_structure(dl_str: str) -> Tuple[bool, str]:
    """
    Validates standard Indian Driving Licence structure (Parivahan / Sarathi standard).
    Format: 2-letter State Code + 2-digit RTO Code + Year + 7-digit Serial
    e.g. MH12 20260012345 or DL-0420260012345
    """
    clean_dl = re.sub(r'[\s\-_]', '', dl_str).upper()
    indian_states = {
        'AN', 'AP', 'AR', 'AS', 'BR', 'CH', 'CG', 'DD', 'DL', 'DN',
        'GA', 'GJ', 'HR', 'HP', 'JH', 'JK', 'KA', 'KL', 'LA', 'LD',
        'MH', 'ML', 'MN', 'MP', 'MZ', 'NL', 'OD', 'PB', 'PY', 'RJ',
        'SK', 'TN', 'TR', 'TS', 'UK', 'UP', 'WB'
    }

    state_code = clean_dl[:2]
    if state_code not in indian_states:
        return False, f"Invalid DL state prefix '{state_code}'. Must be an authorized Indian state/UT code."

    if not re.match(r'^[A-Z]{2}[0-9]{2}[0-9]{4}[0-9]{7}$', clean_dl) and not re.match(r'^[A-Z]{2}[0-9]{13}$', clean_dl):
        # Relaxed check for older formats
        if len(clean_dl) < 11 or len(clean_dl) > 16:
            return False, f"Driving Licence number length ({len(clean_dl)}) out of valid range (11-16 characters)."

    return True, f"Valid Driving Licence format for State: {state_code}."

# =====================================================================
# 2. Document Template Keyword & Semantic Dictionaries
# =====================================================================

DOCUMENT_TEMPLATES = {
    'Aadhaar': {
        'mandatory_keywords': [
            'government of india', 'unique identification', 'uidai',
            'aadhaar', 'enrollment', 'help@uidai', 'mera aadhaar'
        ],
        'secondary_keywords': [
            'male', 'female', 'dob', 'year of birth', 'yob', 'address',
            'vid', 'identity', 'authority', 'bharat sarkar'
        ],
        'id_regex': r'\b[0-9]{4}[\s\-][0-9]{4}[\s\-][0-9]{4}\b|\b[0-9]{12}\b',
        'required_authority': 'Unique Identification Authority of India',
        'aspect_ratio_range': (0.55, 1.85)
    },
    'PAN': {
        'mandatory_keywords': [
            'income tax department', 'govt of india', 'permanent account number',
            'father', 'signature', 'pan'
        ],
        'secondary_keywords': [
            'date of birth', 'dob', 'card', 'taxpayer', 'nsdl', 'utiitsl'
        ],
        'id_regex': r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
        'required_authority': 'Income Tax Department',
        'aspect_ratio_range': (1.35, 1.75)
    },
    'Driving Licence': {
        'mandatory_keywords': [
            'driving licence', 'union of india', 'transport department',
            'licence no', 'validity'
        ],
        'secondary_keywords': [
            'mcwg', 'lmv', 'authorized to drive', 'date of issue', 'rto',
            'date of birth', 'motor'
        ],
        'id_regex': r'\b[A-Z]{2}[0-9\-\s]{11,16}\b',
        'required_authority': 'Transport Department',
        'aspect_ratio_range': (1.35, 1.75)
    },
    'Caste Certificate': {
        'mandatory_keywords': [
            'caste certificate', 'scheduled caste', 'scheduled tribe',
            'backward class', 'vjnt', 'magistrate', 'tahsildar', 'act', 'competent authority'
        ],
        'secondary_keywords': [
            'sub-caste', 'ordinance', 'constitution', 'order', 'maharashtra',
            'government', 'seal', 'office', 'sub-divisional'
        ],
        'id_regex': r'[0-9A-Z\/\-]{8,25}',
        'required_authority': 'Competent Authority / Executive Magistrate',
        'aspect_ratio_range': (0.60, 0.90)  # Standard portrait page
    },
    'Non-Creamy Layer': {
        'mandatory_keywords': [
            'non-creamy layer', 'creamy layer', 'backward classes',
            'financial year', 'annual income', 'sub-divisional'
        ],
        'secondary_keywords': [
            'certificate', 'valid for', 'department of personnel',
            'office memorandum', 'schedule', 'tahsildar'
        ],
        'id_regex': r'[0-9A-Z\/\-]{8,25}',
        'required_authority': 'Sub-Divisional Officer / Tahsildar',
        'aspect_ratio_range': (0.60, 0.90)
    },
    'Caste Validity': {
        'mandatory_keywords': [
            'caste validity', 'scrutiny committee', 'district caste scrutiny',
            'validity certificate', 'regulation of issuance'
        ],
        'secondary_keywords': [
            'chairman', 'member secretary', 'verification', 'verification of caste',
            'divisional', 'decision', 'order'
        ],
        'id_regex': r'[0-9A-Z\/\-]{8,25}',
        'required_authority': 'Caste Scrutiny Committee',
        'aspect_ratio_range': (0.60, 0.90)
    },
    'Marksheet': {
        'mandatory_keywords': [
            'statement of marks', 'marksheet', 'examination', 'board of secondary',
            'seat no', 'roll no', 'subject', 'maximum marks', 'marks obtained'
        ],
        'secondary_keywords': [
            'result', 'passed', 'percentage', 'grade', 'controller of examinations',
            'university', 'school', 'division'
        ],
        'id_regex': r'[0-9A-Z\/\-]{6,20}',
        'required_authority': 'State Board / University',
        'aspect_ratio_range': (0.60, 1.45)
    },
    'Income Certificate': {
        'mandatory_keywords': [
            'income certificate', 'annual income', 'tahsildar', 'executive magistrate',
            'financial year', 'revenue'
        ],
        'secondary_keywords': [
            'resident', 'rupees', 'competent authority', 'sub-district', 'applicant'
        ],
        'id_regex': r'[0-9A-Z\/\-]{8,25}',
        'required_authority': 'Tahsildar / Revenue Department',
        'aspect_ratio_range': (0.60, 0.90)
    },
    'Domicile Certificate': {
        'mandatory_keywords': [
            'domicile certificate', 'resident', 'place of birth', 'executive magistrate',
            'tahsildar'
        ],
        'secondary_keywords': [
            'years', 'state of', 'citizenship', 'certified that', 'territory'
        ],
        'id_regex': r'[0-9A-Z\/\-]{8,25}',
        'required_authority': 'Executive Magistrate / Tahsildar',
        'aspect_ratio_range': (0.60, 0.90)
    }
}

# =====================================================================
# 3. Document Nature vs. Natural Image (Celebrity/Selfie/Scenery) Classifier
# =====================================================================

def evaluate_document_nature(image_np: np.ndarray, text_str: str) -> Tuple[bool, float, Dict[str, Any]]:
    """
    Differentiates a structured document from arbitrary natural photos (celebrities, portraits,
    landscapes, animals, memes) based on physical image properties:
    - Background paper luminance ratio (documents have > 50% high-luminance background)
    - Saturation distribution (documents have low average saturation; photos have high continuous saturation)
    - Horizontal text edge density vs isotropic natural texture
    - Extracted word count and text density
    """
    h, w = image_np.shape[:2]
    
    # 1. Color saturation analysis
    if image_np.ndim == 3:
        hsv = cv2.cvtColor(image_np, cv2.COLOR_RGB2HSV)
        sat = hsv[:, :, 1] / 255.0
        val = hsv[:, :, 2] / 255.0
        mean_sat = float(np.mean(sat))
        # Ratio of near-neutral paper background (low saturation, high value)
        paper_pixels = np.sum((sat < 0.22) & (val > 0.65))
        paper_ratio = float(paper_pixels / (h * w))
    else:
        mean_sat = 0.0
        paper_ratio = float(np.sum(image_np > 170) / (h * w))

    # 2. Text Edge & Horizontal Line Structure Analysis
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY) if image_np.ndim == 3 else image_np.copy()
    # Horizontal Sobel for text line detection
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag_x = np.mean(np.abs(grad_x))
    mag_y = np.mean(np.abs(grad_y))
    edge_ratio = float(mag_x / (mag_y + 1e-5))

    # 3. Word count & character analysis
    clean_text = ' '.join(text_str.split())
    words = [w for w in clean_text.split() if len(w) >= 2]
    word_count = len(words)

    # Scoring the document-likeness
    score = 0.0

    # Test A: Paper background
    if paper_ratio >= 0.45:
        score += 35.0
    elif paper_ratio >= 0.25:
        score += 15.0

    # Test B: Low global saturation (documents are not continuous vivid color portraits)
    if mean_sat <= 0.25:
        score += 30.0
    elif mean_sat <= 0.40:
        score += 15.0

    # Test C: Text presence
    if word_count >= 15:
        score += 35.0
    elif word_count >= 6:
        score += 20.0
    elif word_count >= 2:
        score += 10.0

    # Severe penalty for celebrity portrait / natural photo characteristics:
    # High saturation across frame (> 0.45) with almost no readable document text (< 5 words)
    is_natural_photo = (mean_sat > 0.42 and word_count < 5 and paper_ratio < 0.30)
    if is_natural_photo:
        score = min(score, 10.0)

    is_document = (score >= 40.0)

    diagnostics = {
        'mean_saturation': round(mean_sat, 3),
        'paper_background_ratio': round(paper_ratio, 3),
        'word_count': word_count,
        'horizontal_edge_ratio': round(edge_ratio, 2),
        'document_nature_score': round(score, 1),
        'is_natural_photo': is_natural_photo
    }

    return is_document, score, diagnostics

# =====================================================================
# 4. Master Template Validator Engine
# =====================================================================

def validate_document_template(
    image_np: np.ndarray,
    doc_type: str,
    doc_number: str,
    holder_name: str,
    extracted_text: str = ""
) -> Dict[str, Any]:
    """
    Comprehensive multi-point validation of document template, semantic integrity,
    category keywords, regex identifier schemas, and mathematical checksums.
    """
    clean_text = extracted_text.lower()
    h, w = image_np.shape[:2]
    aspect_ratio = float(w / (h + 1e-5))

    # Step 1: Document Nature Check (Prevents celebrity photos / scenery)
    is_doc, nature_score, nature_diag = evaluate_document_nature(image_np, extracted_text)

    if not is_doc or nature_diag['is_natural_photo']:
        return {
            'is_valid_template': False,
            'template_status': 'REJECTED: NON-DOCUMENT IMAGE',
            'template_score': float(nature_score),
            'confidence': 98.0,
            'rejection_reason': (
                "The uploaded file is not a valid government document. "
                "Analysis detected a natural photographic portrait or scene with high color saturation "
                "and absence of official document typography, headers, or structure."
            ),
            'matched_keywords': [],
            'missing_elements': ['Official Document Header', 'Government Seal / Emblem', 'Structured Typography'],
            'diagnostics': nature_diag
        }

    # Step 2: Category Template Lookup
    template_def = DOCUMENT_TEMPLATES.get(doc_type)
    if not template_def:
        # Generic document with passed nature check
        return {
            'is_valid_template': True,
            'template_status': 'GENERIC DOCUMENT ACCEPTED',
            'template_score': max(nature_score, 70.0),
            'confidence': 75.0,
            'rejection_reason': None,
            'matched_keywords': [],
            'missing_elements': [],
            'diagnostics': nature_diag
        }

    # Step 3: Keyword & Authority Matching
    mandatory_kw = template_def['mandatory_keywords']
    secondary_kw = template_def['secondary_keywords']

    matched_mandatory = [kw for kw in mandatory_kw if kw in clean_text]
    matched_secondary = [kw for kw in secondary_kw if kw in clean_text]

    mand_ratio = len(matched_mandatory) / len(mandatory_kw)
    sec_ratio = len(matched_secondary) / max(len(secondary_kw), 1)

    keyword_points = (mand_ratio * 35.0) + (sec_ratio * 15.0)

    # Step 4: Specific Algorithmic Checks
    id_valid = True
    id_notes = []

    if doc_type == 'Aadhaar':
        clean_num = ''.join(c for c in doc_number if c.isdigit())
        if len(clean_num) == 12:
            verhoeff_ok = validate_verhoeff_checksum(clean_num)
            if verhoeff_ok:
                id_notes.append("Verhoeff algorithmic checksum verified successfully.")
                keyword_points += 25.0
            else:
                id_valid = False
                id_notes.append("Failed Verhoeff algorithmic checksum (invalid 12-digit Aadhaar sequence).")
        else:
            id_valid = False
            id_notes.append("Aadhaar number must contain exactly 12 digits.")

    elif doc_type == 'PAN':
        pan_ok, pan_msg = validate_pan_structure(doc_number, holder_name=holder_name)
        if pan_ok:
            id_notes.append(pan_msg)
            keyword_points += 25.0
        else:
            id_valid = False
            id_notes.append(pan_msg)

    elif doc_type == 'Driving Licence':
        dl_ok, dl_msg = validate_driving_licence_structure(doc_number)
        if dl_ok:
            id_notes.append(dl_msg)
            keyword_points += 20.0
        else:
            id_valid = False
            id_notes.append(dl_msg)

    else:
        # Check if number matches general regex
        id_regex = template_def.get('id_regex')
        if id_regex and re.search(id_regex, doc_number):
            keyword_points += 20.0
            id_notes.append("Document number format adheres to official pattern.")
        else:
            keyword_points += 10.0

    # Step 5: Aspect Ratio Check
    min_asp, max_asp = template_def.get('aspect_ratio_range', (0.5, 2.0))
    aspect_valid = (min_asp <= aspect_ratio <= max_asp)
    if aspect_valid:
        keyword_points += 10.0

    # Total composite template score
    template_score = min(max(nature_score * 0.25 + keyword_points, 0.0), 100.0)

    missing = []
    if len(matched_mandatory) < 1:
        missing.append(f"Official {doc_type} Header / Identifying Keywords")
    if not id_valid:
        missing.extend(id_notes)

    # Threshold for template acceptance
    # If text is present but not a single category keyword matches and ID format fails:
    is_template_valid = (template_score >= 50.0 and id_valid)

    if not is_template_valid:
        if not id_valid:
            status = f"TEMPLATE MISMATCH: {id_notes[0] if id_notes else 'Invalid ID Format'}"
        else:
            status = f"TEMPLATE MISMATCH: Uploaded image does not match {doc_type} layout or official text"
    else:
        status = f"VALID {doc_type.upper()} TEMPLATE"

    return {
        'is_valid_template': is_template_valid,
        'template_status': status,
        'template_score': round(template_score, 1),
        'confidence': round(min(max(template_score, 65.0), 98.0), 1),
        'rejection_reason': None if is_template_valid else status,
        'matched_keywords': matched_mandatory + matched_secondary,
        'missing_elements': missing,
        'diagnostics': {
            **nature_diag,
            'aspect_ratio': round(aspect_ratio, 2),
            'id_valid': id_valid,
            'id_notes': id_notes
        }
    }
