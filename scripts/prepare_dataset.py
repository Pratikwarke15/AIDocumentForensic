import os
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / 'dataset'
AUTH_DIR = DATASET_DIR / 'authentic'
MANIP_DIR = DATASET_DIR / 'manipulated'
MASK_DIR = DATASET_DIR / 'masks'
META_DIR = DATASET_DIR / 'metadata'

for d in [AUTH_DIR, MANIP_DIR, MASK_DIR, META_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def create_synthetic_base_document(width=700, height=900, doc_id="MH/INC/2026/0001", name="Rahul Sharma", doc_type="Income Certificate"):
    # Subtle parchment paper background
    bg = np.ones((height, width, 3), dtype=np.uint8) * 248
    noise = np.random.randint(-5, 5, (height, width, 3), dtype=np.int16)
    bg = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    img = Image.fromarray(bg)
    draw = ImageDraw.Draw(img)

    # Decorative border
    draw.rectangle([25, 25, width - 25, height - 25], outline=(40, 60, 100), width=3)
    draw.rectangle([32, 32, width - 32, height - 32], outline=(150, 160, 180), width=1)

    # Header
    draw.text((width // 2 - 140, 60), "GOVERNMENT OF MAHARASHTRA", fill=(20, 30, 70))
    draw.text((width // 2 - 110, 85), "REVENUE & EXCISE DEPARTMENT", fill=(70, 80, 100))
    draw.text((width // 2 - 90, 120), f"OFFICIAL {doc_type.upper()}", fill=(180, 40, 30))

    draw.line([60, 150, width - 60, 150], fill=(100, 110, 130), width=1)

    # Body fields
    y = 190
    fields = [
        ("Certificate Number:", doc_id),
        ("Full Legal Name:", name),
        ("Father's Name:", "Suresh Sharma"),
        ("Date of Issuance:", "2026-06-15"),
        ("Annual Certified Income:", "INR 4,50,000 (Four Lakh Fifty Thousand Only)"),
        ("Issuing Tehsildar:", "Sub-Divisional Magistrate, Pune City"),
        ("Verification Status:", "OFFICIALLY RECORDED & VERIFIED")
    ]

    for label, val in fields:
        draw.text((70, y), label, fill=(50, 50, 60))
        draw.text((280, y), val, fill=(10, 20, 40))
        draw.line([70, y + 25, width - 70, y + 25], fill=(220, 225, 230), width=1)
        y += 50

    # Official Seal (Circular stamp)
    seal_x, seal_y = 140, height - 200
    draw.ellipse([seal_x - 50, seal_y - 50, seal_x + 50, seal_y + 50], outline=(30, 70, 150), width=3)
    draw.ellipse([seal_x - 42, seal_y - 42, seal_x + 42, seal_y + 42], outline=(30, 70, 150), width=1)
    draw.text((seal_x - 30, seal_y - 12), "* OFFICIAL *", fill=(30, 70, 150))
    draw.text((seal_x - 22, seal_y + 5), "SEAL", fill=(30, 70, 150))

    # Signature line
    sig_x = width - 220
    draw.line([sig_x, height - 160, sig_x + 150, height - 160], fill=(30, 30, 30), width=2)
    draw.text((sig_x + 15, height - 150), "Authorized Signatory", fill=(60, 60, 60))
    draw.text((sig_x + 30, height - 185), "~ S. Sharma ~", fill=(10, 20, 80))

    return img

def generate_synthetic_dataset(num_authentic=40, num_manipulated=40):
    print(f"[Dataset] Generating {num_authentic} authentic and {num_manipulated} manipulated document samples...")
    names = ["Aarav Patel", "Priya Singh", "Rohan Mehta", "Neha Gupta", "Vikram Joshi", "Ananya Verma", "Karan Reddy", "Sunita Nair"]
    types = ["Income Certificate", "Caste Certificate", "Domicile Certificate", "Marksheet", "Identity Card"]

    # Generate Authentic samples across diverse realistic qualities (scans, compressed JPEGs, photos)
    for i in range(num_authentic):
        name = random.choice(names)
        doc_type = random.choice(types)
        doc_id = f"DOC-AUTH-{i+1:04d}"
        img = create_synthetic_base_document(doc_id=doc_id, name=name, doc_type=doc_type)

        # Realistic document variations: diverse compression qualities (Q70-Q95)
        qual = random.choice([72, 78, 82, 86, 90, 95])
        
        # 25% of authentic docs get mild scanner blur or subtle noise
        if i % 4 == 0:
            img = img.filter(ImageFilter.GaussianBlur(radius=0.35))
        elif i % 4 == 1:
            # Slight warm illumination tint
            arr = np.array(img).astype(np.float32)
            arr[:, :, 0] = np.clip(arr[:, :, 0] + 3, 0, 255)
            img = Image.fromarray(arr.astype(np.uint8))

        out_path = AUTH_DIR / f"{doc_id}.jpg"
        img.save(out_path, 'JPEG', quality=qual)

    # Generate Manipulated samples across diverse compression levels
    for i in range(num_manipulated):
        name = random.choice(names)
        doc_type = random.choice(types)
        doc_id = f"DOC-MANIP-{i+1:04d}"
        img = create_synthetic_base_document(doc_id=doc_id, name=name, doc_type=doc_type)
        
        # Create ground truth binary mask
        mask = Image.new("L", img.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_img = ImageDraw.Draw(img)

        manip_type = random.choice(['spliced_number', 'cloned_seal', 'erased_text', 'forged_amount'])

        if manip_type == 'spliced_number':
            # Patch over document number with different font/compression
            patch_box = [275, 185, 480, 215]
            draw_img.rectangle(patch_box, fill=(240, 240, 245))
            draw_img.text((280, 190), f"FORGED-{random.randint(1000, 9999)}", fill=(0, 0, 0))
            draw_mask.rectangle(patch_box, fill=255)

        elif manip_type == 'cloned_seal':
            # Copy seal and paste duplicate at top-right
            seal_crop = img.crop((90, img.height - 250, 190, img.height - 150))
            paste_box = (img.width - 180, 180)
            img.paste(seal_crop, paste_box)
            draw_mask.rectangle([paste_box[0], paste_box[1], paste_box[0] + 100, paste_box[1] + 100], fill=255)

        elif manip_type == 'erased_text':
            # Smooth out a text area
            patch_box = [275, 235, 450, 265]
            draw_img.rectangle(patch_box, fill=(248, 248, 248))
            draw_mask.rectangle(patch_box, fill=255)

        elif manip_type == 'forged_amount':
            # Patch income amount with inconsistent text
            patch_box = [275, 385, 600, 415]
            draw_img.rectangle(patch_box, fill=(238, 242, 248))
            draw_img.text((280, 390), "INR 99,00,000 (Ninety Nine Lakh)", fill=(10, 10, 10))
            draw_mask.rectangle(patch_box, fill=255)

        # Diverse JPEG compression quality (Q70-Q95)
        qual = random.choice([72, 78, 82, 85, 88, 92])
        out_img_path = MANIP_DIR / f"{doc_id}.jpg"
        out_mask_path = MASK_DIR / f"{doc_id}_mask.png"
        
        img.save(out_img_path, 'JPEG', quality=qual)
        mask.save(out_mask_path, 'PNG')

    print(f"[Dataset] Successfully generated dataset in {DATASET_DIR}")

if __name__ == '__main__':
    generate_synthetic_dataset()
