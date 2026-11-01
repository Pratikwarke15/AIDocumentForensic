import io
import os
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
from PIL import Image, ImageOps

def load_and_preprocess_image(file_path: Path, max_dimension: int = 800) -> Tuple[np.ndarray, Image.Image, Tuple[int, int]]:
    """
    Loads an image file, corrects EXIF orientation, standardizes dimensions 
    (max_dimension = 800), and returns:
    1. Standardized image as RGB numpy array
    2. PIL Image analysis object
    3. Original (width, height) tuple
    """
    image = Image.open(file_path)
    
    # Correct orientation if EXIF tags exist
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    # Ensure RGB
    if image.mode != 'RGB':
        image = image.convert('RGB')

    orig_size = image.size  # (width, height)
    w, h = orig_size

    # Resize preserving aspect ratio if larger than max_dimension
    if max(w, h) > max_dimension:
        if w > h:
            new_w = max_dimension
            new_h = int(h * (max_dimension / w))
        else:
            new_h = max_dimension
            new_w = int(w * (max_dimension / h))
        image_resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        image_resized = image.copy()

    image_np = np.array(image_resized)
    return image_np, image_resized, orig_size

def save_standardized_copy(image: Image.Image, output_path: Path, quality: int = 95) -> str:
    """
    Saves standardized analysis copy as normalized JPEG at quality 95.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, 'JPEG', quality=quality)
    return str(output_path)
