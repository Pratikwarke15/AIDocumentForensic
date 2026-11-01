import os
import sys
import json
import hashlib
import random
import io
from pathlib import Path
from typing import Dict, List, Tuple, Any
import requests
import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import cv2

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DATASET_DIR = BASE_DIR / 'dataset'
AUTH_DIR = DATASET_DIR / 'authentic'
MANIP_DIR = DATASET_DIR / 'manipulated'
MASK_DIR = DATASET_DIR / 'masks'
META_DIR = DATASET_DIR / 'metadata'

for d in [AUTH_DIR, MANIP_DIR, MASK_DIR, META_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------
# 1. Official Government PDF Sources (Public Domain / Open Access)
# ---------------------------------------------------------------------
OFFICIAL_SOURCES = [
    {
        'doc_id': 'IRS_F1040',
        'name': 'IRS Form 1040 - US Individual Income Tax Return',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1040.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_FW9',
        'name': 'IRS Form W-9 - Taxpayer Identification and Certification',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/fw9.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_FW4',
        'name': 'IRS Form W-4 - Employee Withholding Certificate',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/fw4.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1040ES',
        'name': 'IRS Form 1040-ES - Estimated Tax for Individuals',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1040es.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1040X',
        'name': 'IRS Form 1040-X - Amended US Individual Income Tax Return',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1040x.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F8822',
        'name': 'IRS Form 8822 - Change of Address',
        'category': 'administrative_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f8822.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F4506T',
        'name': 'IRS Form 4506-T - Request for Transcript of Tax Return',
        'category': 'administrative_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f4506t.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F941',
        'name': 'IRS Form 941 - Employer Quarterly Federal Tax Return',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f941.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1099MISC',
        'name': 'IRS Form 1099-MISC - Miscellaneous Information',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1099msc.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1099NEC',
        'name': 'IRS Form 1099-NEC - Nonemployee Compensation',
        'category': 'tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1099nec.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F8863',
        'name': 'IRS Form 8863 - Education Credits',
        'category': 'education_tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f8863.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F9465',
        'name': 'IRS Form 9465 - Installment Agreement Request',
        'category': 'administrative_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f9465.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1120',
        'name': 'IRS Form 1120 - US Corporation Income Tax Return',
        'category': 'corporate_tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1120.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'IRS_F1065',
        'name': 'IRS Form 1065 - US Return of Partnership Income',
        'category': 'corporate_tax_form',
        'agency': 'Internal Revenue Service (IRS)',
        'url': 'https://www.irs.gov/pub/irs-pdf/f1065.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'OPM_OF306',
        'name': 'OPM Form OF-306 - Declaration for Federal Employment',
        'category': 'employment_form',
        'agency': 'Office of Personnel Management (OPM)',
        'url': 'https://www.opm.gov/forms/pdf_fill/of0306.pdf',
        'max_pages': 3
    },
    {
        'doc_id': 'OPM_SF2809',
        'name': 'OPM Form SF-2809 - Health Benefits Election Form',
        'category': 'benefits_form',
        'agency': 'Office of Personnel Management (OPM)',
        'url': 'https://www.opm.gov/forms/pdf_fill/sf2809.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'OPM_SF2817',
        'name': 'OPM Form SF-2817 - Life Insurance Election Form',
        'category': 'benefits_form',
        'agency': 'Office of Personnel Management (OPM)',
        'url': 'https://www.opm.gov/forms/pdf_fill/sf2817.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'OPM_OPM71',
        'name': 'OPM Form 71 - Request for Leave or Approved Absence',
        'category': 'employment_form',
        'agency': 'Office of Personnel Management (OPM)',
        'url': 'https://www.opm.gov/forms/pdf_fill/opm71.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'GovInfo_FR1',
        'name': 'Federal Register Vol 89 No 1 - Public Health Notice',
        'category': 'public_notice',
        'agency': 'National Archives and Records Administration (NARA)',
        'url': 'https://www.govinfo.gov/content/pkg/FR-2024-01-02/pdf/2023-28888.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'GovInfo_FR2',
        'name': 'Federal Register Vol 89 No 2 - Transportation Directive',
        'category': 'regulatory_directive',
        'agency': 'Department of Transportation (DOT)',
        'url': 'https://www.govinfo.gov/content/pkg/FR-2024-01-03/pdf/2023-28945.pdf',
        'max_pages': 2
    },
    {
        'doc_id': 'GovInfo_FR3',
        'name': 'Federal Register Vol 89 No 3 - Environmental Protection Circular',
        'category': 'government_circular',
        'agency': 'Environmental Protection Agency (EPA)',
        'url': 'https://www.govinfo.gov/content/pkg/FR-2024-01-04/pdf/2023-28980.pdf',
        'max_pages': 2
    }
]

# ---------------------------------------------------------------------
# 2. Diverse Regional Government Certificate Layouts
# ---------------------------------------------------------------------
def generate_diverse_certificate(doc_idx: int, cert_type: str, authority: str, state: str) -> Image.Image:
    """
    Generates distinct government certificates across diverse regional layouts,
    fonts, borders, alignments, and circular stamp designs.
    """
    # Varied canvas sizes
    widths = [720, 750, 800, 700]
    heights = [960, 920, 1000, 900]
    w = widths[doc_idx % len(widths)]
    h = heights[doc_idx % len(heights)]

    # Varied background tones (cream, light blue-gray, light parchment, white)
    bg_tones = [
        (249, 248, 244),
        (244, 247, 250),
        (252, 250, 245),
        (247, 249, 247)
    ]
    bg_color = bg_tones[doc_idx % len(bg_tones)]
    bg = np.ones((h, w, 3), dtype=np.uint8) * np.array(bg_color, dtype=np.uint8)
    
    # Subtle authentic paper texture
    noise = np.random.randint(-3, 4, (h, w, 3), dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img)

    # Varied border styles (double, triple, ornamental)
    b_color = [(30, 50, 90), (60, 40, 30), (20, 60, 40), (50, 50, 60)][doc_idx % 4]
    draw.rectangle([20, 20, w - 20, h - 20], outline=b_color, width=2 + (doc_idx % 2))
    draw.rectangle([28, 28, w - 28, h - 28], outline=(180, 185, 195), width=1)

    # Header
    draw.text((w // 2 - 130, 45), f"GOVERNMENT OF {state.upper()}", fill=b_color)
    draw.text((w // 2 - 110, 70), authority.upper(), fill=(70, 75, 85))
    draw.text((w // 2 - 90, 100), f"OFFICIAL {cert_type.upper()}", fill=(160, 40, 30))
    draw.line([50, 125, w - 50, 125], fill=(120, 130, 140), width=1)

    # Unique certificate fields
    fields = [
        ("Registration Number:", f"{state[:2]}/{cert_type[:3]}/{2026}/{1000 + doc_idx}"),
        ("Holder Legal Name:", f"Candidate {chr(65 + doc_idx % 26)} Sharma"),
        ("Identification Token:", f"UID-{987654320000 + doc_idx * 17}"),
        ("Date of Certification:", f"2026-0{(doc_idx % 9) + 1}-15"),
        ("Jurisdiction Sub-District:", f"Tehsil Region {doc_idx + 1}, {state}"),
        ("Classification Tier:", f"Standard Tier {chr(65 + doc_idx % 3)}"),
        ("Validation Authority:", f"Sub-Divisional Executive Magistrate")
    ]

    y = 155
    line_spacing = 42 + (doc_idx % 6)
    for label, val in fields:
        draw.text((60, y), label, fill=(50, 55, 65))
        draw.text((270, y), val, fill=(15, 20, 35))
        draw.line([60, y + 25, w - 60, y + 25], fill=(225, 230, 235), width=1)
        y += line_spacing

    # Official Seal (different color and positioning)
    seal_x = 120 + ((doc_idx * 40) % 200)
    seal_y = h - 160
    seal_color = [(20, 60, 140), (140, 30, 30), (30, 100, 50), (60, 60, 70)][doc_idx % 4]
    draw.ellipse([seal_x - 45, seal_y - 45, seal_x + 45, seal_y + 45], outline=seal_color, width=2)
    draw.ellipse([seal_x - 38, seal_y - 38, seal_x + 38, seal_y + 38], outline=seal_color, width=1)
    draw.text((seal_x - 26, seal_y - 10), "* OFFICIAL *", fill=seal_color)
    draw.text((seal_x - 18, seal_y + 6), "SEAL", fill=seal_color)

    # Signature line
    sig_x = w - 210
    draw.line([sig_x, h - 130, sig_x + 140, h - 130], fill=(40, 40, 40), width=1)
    draw.text((sig_x + 15, h - 120), "Competent Authority", fill=(80, 80, 80))
    draw.text((sig_x + 25, h - 150), f"~ S. K. {state[:3]} ~", fill=(10, 20, 80))

    # Barcode/QR representation on alternating documents
    if doc_idx % 2 == 0:
        bx = w - 120
        by = 40
        draw.rectangle([bx, by, bx + 65, by + 65], fill=(255, 255, 255), outline=(0, 0, 0), width=1)
        draw.rectangle([bx + 6, by + 6, bx + 22, by + 22], fill=(0, 0, 0))
        draw.rectangle([bx + 43, by + 6, bx + 59, by + 22], fill=(0, 0, 0))
        draw.rectangle([bx + 6, by + 43, bx + 22, by + 59], fill=(0, 0, 0))
        for rx in range(bx + 26, bx + 42, 4):
            for ry in range(by + 26, by + 42, 4):
                if (rx + ry) % 8 == 0:
                    draw.rectangle([rx, ry, rx + 3, ry + 3], fill=(0, 0, 0))

    return img

# ---------------------------------------------------------------------
# 3. Perceptual Hashing (dhash) for Duplicate Detection
# ---------------------------------------------------------------------
def compute_dhash(image_pil: Image.Image, hash_size: int = 8) -> str:
    """Calculates 64-bit difference hash (dhash) for perceptual duplicate detection."""
    gray = image_pil.convert('L').resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.array(gray.getdata(), dtype=np.int32).reshape((hash_size, hash_size + 1))
    diff = pixels[:, 1:] > pixels[:, :-1]
    
    decimal_val = 0
    hex_parts = []
    for idx, bit in enumerate(diff.flatten()):
        if bit:
            decimal_val += 2 ** (idx % 8)
        if (idx % 8) == 7:
            hex_parts.append(hex(decimal_val)[2:].rjust(2, '0'))
            decimal_val = 0
    return ''.join(hex_parts)

def hamming_distance(hash1: str, hash2: str) -> int:
    """Computes bitwise Hamming distance between two hex hashes."""
    b1 = bin(int(hash1, 16))[2:].zfill(64)
    b2 = bin(int(hash2, 16))[2:].zfill(64)
    return sum(c1 != c2 for c1, c2 in zip(b1, b2))

# ---------------------------------------------------------------------
# 4. Realistic Controlled Manipulation Generators
# ---------------------------------------------------------------------
def generate_official_stamp(stamp_type: int = 0) -> Image.Image:
    """Generates an official circular government seal/stamp with rich keypoints."""
    size = 130
    stamp = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(stamp)
    colors = [
        (20, 60, 160, 240),   # Official Blue
        (180, 25, 25, 240),   # Official Red/Crimson
        (25, 110, 50, 240),   # Official Green
        (140, 90, 20, 240)    # Gold/Bronze
    ]
    color = colors[stamp_type % len(colors)]
    cx, cy = size // 2, size // 2

    # Outer and inner circular rings
    draw.ellipse([6, 6, size - 6, size - 6], outline=color, width=3)
    draw.ellipse([14, 14, size - 14, size - 14], outline=color, width=1)
    draw.ellipse([22, 22, size - 22, size - 22], outline=color, width=1)

    # Stars / dots along circle
    for i in range(16):
        ang = i * (2 * np.pi / 16)
        r = 18
        px = int(cx + r * np.cos(ang))
        py = int(cy + r * np.sin(ang))
        draw.rectangle([px - 2, py - 2, px + 2, py + 2], fill=color)

    # Center text
    draw.text((cx - 28, cy - 14), "* OFFICIAL *", fill=color)
    draw.text((cx - 22, cy), "REGISTRY", fill=color)
    draw.text((cx - 20, cy + 14), "VERIFIED", fill=color)

    return stamp

def create_manipulation(image_pil: Image.Image, manip_type: str, doc_idx: int = 0, is_certificate: bool = False) -> Tuple[Image.Image, Image.Image]:
    """
    Applies realistic digital tampering techniques:
    - Pre-compresses base at Q1 in [76, 84] to simulate genuine prior JPEG scan/distribution
    - Injects realistic tampering
    - Returns tampered image (PIL) and binary ground-truth mask (PIL)
    """
    w, h = image_pil.size
    mask = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask)

    # 1. Base pre-compression at Q1 (76-84)
    buf_base = io.BytesIO()
    q_base = random.choice([76, 80, 84])
    image_pil.save(buf_base, 'JPEG', quality=q_base)
    buf_base.seek(0)
    base_jpeg = Image.open(buf_base).convert('RGB')
    img = base_jpeg.copy()
    draw_img = ImageDraw.Draw(img)

    if manip_type == 'cloned_seal_or_block':
        # True copy-move cloning
        if is_certificate:
            # Clone official seal from bottom-left to top-right
            seal_box = [75, h - 205, 205, h - 75]
            seal_crop = img.crop(seal_box)
            paste_x = w - 220
            paste_y = 180
            img.paste(seal_crop, (paste_x, paste_y))
            draw_mask.rectangle([paste_x, paste_y, paste_x + seal_crop.width, paste_y + seal_crop.height], fill=255)
        else:
            # On forms: clone a content-dense text/checkbox block
            crop_box = [60, 220, 260, 300]
            if crop_box[2] < w and crop_box[3] < h:
                block = img.crop(crop_box)
                tgt_x = min(w - 210, 420)
                tgt_y = min(h - 100, 680)
                img.paste(block, (tgt_x, tgt_y))
                draw_mask.rectangle([tgt_x, tgt_y, tgt_x + block.width, tgt_y + block.height], fill=255)
            else:
                block = img.crop([40, 100, 240, 180])
                img.paste(block, (w - 250, h - 200))
                draw_mask.rectangle([w - 250, h - 200, w - 10, h - 120], fill=255)

    elif manip_type == 'spliced_stamp_seal':
        # Splicing an external official stamp from another department
        stamp = generate_official_stamp(doc_idx + 1)
        sw, sh = stamp.size
        sx = int(w * random.uniform(0.50, 0.72))
        sy = int(h * random.uniform(0.55, 0.75))
        img.paste(stamp, (sx, sy), stamp)
        draw_mask.rectangle([sx, sy, sx + sw, sy + sh], fill=255)

    elif manip_type == 'spliced_text':
        # Splicing altered text entry into a field box
        box_x = int(w * 0.30)
        box_y = int(h * random.uniform(0.22, 0.48))
        box_w = int(w * random.uniform(0.40, 0.50))
        box_h = int(h * 0.042)

        # Mismatched background patch with subtle color variation
        patch_color = (random.randint(236, 244), random.randint(240, 248), random.randint(244, 252))
        patch = Image.new('RGB', (box_w, box_h), patch_color)
        p_draw = ImageDraw.Draw(patch)
        p_draw.rectangle([1, 1, box_w - 1, box_h - 1], outline=(150, 155, 165), width=1)
        forged_entries = [
            f"ALTERED BENEFICIARY: REGISTRY TRUST CORP #{random.randint(1000, 9999)}",
            f"FORGED CLEARANCE - AUTH CODE: SEC-{random.randint(10000, 99999)}",
            f"EXEMPTION GRANTED - CLAIM VALUE: $4,850,000.00",
            f"LEGAL ASSIGNEE: CONTINENTAL HOLDINGS GMBH",
            f"SPECIAL WAIVER APPROVED - REF: WAIV-{random.randint(100, 999)}"
        ]
        text_entry = random.choice(forged_entries)
        p_draw.text((8, int(box_h * 0.25)), text_entry, fill=(5, 5, 10))

        p_np = np.array(patch)
        noise = np.random.normal(0, 3.5, p_np.shape).astype(np.int16)
        p_np = np.clip(p_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        patch = Image.fromarray(p_np)

        img.paste(patch, (box_x, box_y))
        draw_mask.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=255)

    elif manip_type == 'modified_number_date':
        # Financial amount or date modification with baseline offset
        box_x = int(w * random.uniform(0.38, 0.58))
        box_y = int(h * random.uniform(0.32, 0.62))
        box_w = int(w * 0.35)
        box_h = int(h * 0.038)

        patch_color = (random.randint(242, 248), random.randint(242, 248), random.randint(246, 252))
        patch = Image.new('RGB', (box_w, box_h), patch_color)
        p_draw = ImageDraw.Draw(patch)
        forged_numbers = [
            f"$9,850,000.00 (FORGED AMOUNT)",
            f"$14,750,000.00 (TAX ADJUSTED)",
            f"VALID UNTIL: 2035-12-31 (EXP: MODIFIED)",
            f"REG TOKEN: 9988-7766-5544-3322",
            f"ASSESSED VALUE: $5,250,000.00"
        ]
        text_num = random.choice(forged_numbers)
        p_draw.text((6, 4), text_num, fill=(0, 0, 0))

        p_np = np.array(patch)
        noise = np.random.normal(0, 3.0, p_np.shape).astype(np.int16)
        p_np = np.clip(p_np.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        patch = Image.fromarray(p_np)

        img.paste(patch, (box_x, box_y))
        draw_mask.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=255)

    elif manip_type == 'erased_text':
        # Inpainting / erasing text clause
        box_x = int(w * 0.22)
        box_y = int(h * random.uniform(0.24, 0.52))
        box_w = int(w * 0.55)
        box_h = int(h * 0.045)

        crop_bg = img.crop([max(0, box_x - 15), max(0, box_y - 15), box_x, box_y])
        avg_col = tuple(np.array(crop_bg).mean(axis=(0, 1)).astype(int))
        draw_img.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=avg_col)
        erased_crop = img.crop([box_x, box_y, box_x + box_w, box_y + box_h])
        erased_crop = erased_crop.filter(ImageFilter.GaussianBlur(radius=1.5))
        img.paste(erased_crop, (box_x, box_y))
        draw_mask.rectangle([box_x, box_y, box_x + box_w, box_y + box_h], fill=255)

    return img, mask

# ---------------------------------------------------------------------
# 5. Full Dataset Construction Pipeline
# ---------------------------------------------------------------------
def build_dataset():
    print("=" * 70)
    print("AI FORENSICS: BUILDING DIVERSE GOVERNMENT DOCUMENT DATASET")
    print("=" * 70)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    collected_records = []
    seen_hashes = {}  # dhash -> doc_id
    duplicate_count = 0

    temp_pdf_dir = DATASET_DIR / 'raw_pdfs'
    temp_pdf_dir.mkdir(parents=True, exist_ok=True)

    # --- Phase 1: Download & Render Official Public Domain PDFs ---
    for src in OFFICIAL_SOURCES:
        doc_id = src['doc_id']
        url = src['url']
        print(f"[Fetch] Downloading {doc_id}: {src['name']}...")
        pdf_path = temp_pdf_dir / f"{doc_id}.pdf"
        
        try:
            if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
                resp = requests.get(url, headers=headers, timeout=12)
                if resp.status_code == 200:
                    pdf_path.write_bytes(resp.content)
                else:
                    print(f"  Warning: failed to download {doc_id} (status {resp.status_code})")
                    continue
            
            doc = fitz.open(pdf_path)
            pages_to_render = min(len(doc), src['max_pages'])
            
            for p_idx in range(pages_to_render):
                page = doc[p_idx]
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                # Resize to normalized dimension (max 800px)
                max_dim = 800
                if max(img.size) > max_dim:
                    scale = max_dim / max(img.size)
                    new_size = (int(img.width * scale), int(img.height * scale))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Check duplicate hash
                h_val = compute_dhash(img)
                is_dup = False
                for existing_hash, existing_name in seen_hashes.items():
                    if hamming_distance(h_val, existing_hash) <= 3:
                        is_dup = True
                        duplicate_count += 1
                        print(f"  [Duplicate Removed] Page {p_idx+1} matches existing {existing_name} (dhash dist <= 3)")
                        break
                
                if not is_dup:
                    seen_hashes[h_val] = f"{doc_id}_p{p_idx+1}"
                    collected_records.append({
                        'doc_id': f"{doc_id}_p{p_idx+1}",
                        'document_name': src['name'],
                        'document_category': src['category'],
                        'source_agency': src['agency'],
                        'source_url': src['url'],
                        'page_number': p_idx + 1,
                        'image': img,
                        'dhash': h_val
                    })
                    print(f"  [OK] Added {doc_id} Page {p_idx+1} ({img.size[0]}x{img.size[1]})")

        except Exception as e:
            print(f"  Error processing {doc_id}: {e}")

    # --- Phase 2: Add Diverse Regional Public Certificates ---
    cert_definitions = [
        ("Income Certificate", "Revenue & Land Reforms Department", "Maharashtra"),
        ("Domicile Certificate", "General Administration Department", "Delhi"),
        ("Caste Certificate", "Social Welfare Department", "Karnataka"),
        ("Marksheet & Transcript", "State Board of Secondary Education", "Gujarat"),
        ("Identity Verification Record", "State Registration Authority", "Tamil Nadu"),
        ("Clearance Certificate", "Public Works Department", "Rajasthan"),
        ("Birth & Domicile Record", "Municipal Corporation of Greater Mumbai", "Maharashtra"),
        ("Excise Tax Exemption", "Commercial Taxes Department", "Punjab"),
        ("Land Ownership Extract", "Revenue Department (Satbara)", "Maharashtra"),
        ("Citizenship Registry Slip", "Department of Internal Affairs", "West Bengal")
    ]

    for idx, (c_type, auth, state) in enumerate(cert_definitions):
        c_img = generate_diverse_certificate(idx, c_type, auth, state)
        h_val = compute_dhash(c_img)
        seen_hashes[h_val] = f"CERT_{idx+1}"
        collected_records.append({
            'doc_id': f"CERT_{idx+1:02d}",
            'document_name': f"{state} Official {c_type}",
            'document_category': 'government_certificate',
            'source_agency': f"{state} {auth}",
            'source_url': 'local_standardized_public_template',
            'page_number': 1,
            'image': c_img,
            'dhash': h_val
        })

    print(f"\n[Acquisition Summary] Collected {len(collected_records)} unique authentic documents across government categories.")
    print(f"[Deduplication] Filtered out {duplicate_count} duplicate/near-duplicate page renderings.")

    # --- Phase 3: Leakage-Free Splitting by Document Group ---
    # Group by base document name so pages and derivative manipulations NEVER cross splits
    unique_groups = list(set(r['document_name'] for r in collected_records))
    random.seed(42)
    random.shuffle(unique_groups)

    n_groups = len(unique_groups)
    n_train = int(n_groups * 0.70)
    n_val = int(n_groups * 0.15)
    train_groups = set(unique_groups[:n_train])
    val_groups = set(unique_groups[n_train:n_train + n_val])
    test_groups = set(unique_groups[n_train + n_val:])

    print(f"[Splitting] {len(unique_groups)} Document Groups -> Train: {len(train_groups)}, Val: {len(val_groups)}, Test: {len(test_groups)}")

    # Clean existing directories
    for d in [AUTH_DIR, MANIP_DIR, MASK_DIR]:
        for f in d.glob('*.*'):
            try: f.unlink()
            except Exception: pass

    inventory_rows = []
    manip_types = ['cloned_seal_or_block', 'spliced_stamp_seal', 'spliced_text', 'modified_number_date', 'erased_text']

    # --- Phase 4: Save Authentic Samples and Controlled Manipulations ---
    for rec_idx, rec in enumerate(collected_records):
        d_name = rec['document_name']
        if d_name in train_groups:
            split_tag = 'train'
        elif d_name in val_groups:
            split_tag = 'val'
        else:
            split_tag = 'test'

        doc_slug = rec['doc_id']
        auth_filename = f"AUTH_{doc_slug}.jpg"
        auth_path = AUTH_DIR / auth_filename
        
        # Save authentic sample with diverse realistic JPEG quality (Q82 to Q94)
        qual = random.choice([82, 86, 90, 94])
        if random.random() < 0.45:
            exif_auth = rec['image'].getexif()
            exif_auth[0x0131] = random.choice([
                'HP ScanJet Pro 3500 f1',
                'Canon CanoScan LiDE 400',
                'Epson Perfection V39'
            ])
            rec['image'].save(auth_path, 'JPEG', quality=qual, exif=exif_auth)
        else:
            rec['image'].save(auth_path, 'JPEG', quality=qual)

        inventory_rows.append({
            'filename': auth_filename,
            'source_url': rec['source_url'],
            'document_name': rec['document_name'],
            'document_category': rec['document_category'],
            'source_agency': rec['source_agency'],
            'page_number': rec['page_number'],
            'label': 0,
            'label_name': 'authentic',
            'manipulation_type': 'none',
            'dhash': rec['dhash'],
            'split': split_tag,
            'jpeg_quality': qual
        })

        # Create 1 controlled realistic manipulation per authentic sample
        m_type = manip_types[rec_idx % len(manip_types)]
        is_cert = ('CERT_' in rec['doc_id'])
        manip_img, mask_img = create_manipulation(rec['image'], m_type, doc_idx=rec_idx, is_certificate=is_cert)
        
        manip_filename = f"MANIP_{doc_slug}.jpg"
        mask_filename = f"MASK_{doc_slug}.png"
        
        manip_path = MANIP_DIR / manip_filename
        mask_path = MASK_DIR / mask_filename

        m_qual = random.choice([82, 86, 90, 94])
        if random.random() < 0.45:
            exif_m = manip_img.getexif()
            exif_m[0x0131] = random.choice([
                'Adobe Photoshop 24.1 (Windows)',
                'GIMP 2.10.34',
                'Canva Desktop 1.72',
                'Paint.NET v4.3.11'
            ])
            exif_m[0x0132] = '2026:09:28 14:15:00'
            manip_img.save(manip_path, 'JPEG', quality=m_qual, exif=exif_m)
        else:
            manip_img.save(manip_path, 'JPEG', quality=m_qual)

        mask_img.save(mask_path, 'PNG')

        inventory_rows.append({
            'filename': manip_filename,
            'source_url': rec['source_url'],
            'document_name': rec['document_name'],
            'document_category': rec['document_category'],
            'source_agency': rec['source_agency'],
            'page_number': rec['page_number'],
            'label': 1,
            'label_name': 'manipulated',
            'manipulation_type': m_type,
            'dhash': compute_dhash(manip_img),
            'split': split_tag,
            'jpeg_quality': m_qual
        })

    # Save metadata inventory
    import pandas as pd
    inv_df = pd.DataFrame(inventory_rows)
    inv_csv_path = META_DIR / 'dataset_inventory.csv'
    inv_df.to_csv(inv_csv_path, index=False)

    print(f"\n[Dataset Complete] Successfully built dataset:")
    print(f"  Total Authentic samples:   {len(inv_df[inv_df['label'] == 0])}")
    print(f"  Total Manipulated samples: {len(inv_df[inv_df['label'] == 1])}")
    print(f"  Train samples:             {len(inv_df[inv_df['split'] == 'train'])}")
    print(f"  Val samples:               {len(inv_df[inv_df['split'] == 'val'])}")
    print(f"  Test samples:              {len(inv_df[inv_df['split'] == 'test'])}")
    print(f"  Inventory saved to:        {inv_csv_path}")

    return inv_df

if __name__ == '__main__':
    build_dataset()
