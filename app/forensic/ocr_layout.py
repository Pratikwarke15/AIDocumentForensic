from typing import Dict, Any, Tuple, List
import numpy as np
import cv2

def extract_ocr_and_layout_features(image_np: np.ndarray) -> Tuple[Dict[str, Any], Dict[str, float]]:
    """
    Extracts OCR word bounding boxes, confidence, baseline alignment variance,
    and typography inconsistency signals using pytesseract if available.
    Safely falls back to morphological contour layout analysis if tesseract binary is missing.
    """
    ocr_data = {
        'available': False,
        'engine': 'tesseract',
        'word_count': 0,
        'extracted_text_preview': '',
        'boxes': [],
        'mean_confidence': 0.0,
        'confidence_variance': 0.0,
        'baseline_variance': 0.0,
        'suspicious_box_count': 0
    }

    features = {
        'layout_text_alignment_variance': 0.0,
        'ocr_confidence_variance': 0.0,
        'ocr_suspicious_box_count': 0.0
    }

    try:
        import pytesseract
        from pytesseract import Output
        
        # Test OCR invocation
        data = pytesseract.image_to_data(image_np, output_type=Output.DICT)
        ocr_data['available'] = True
        
        confidences = []
        baselines = []
        words = []
        suspicious_boxes = 0

        n_boxes = len(data['text'])
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            if text and conf > 0:
                confidences.append(conf)
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                
                # Bottom coordinate as text baseline approximation
                baseline = y + h
                baselines.append(baseline)
                words.append(text)
                
                # Check for suspicious outlier boxes (e.g. extreme aspect ratio or abnormally low conf)
                aspect = float(w / (h + 1e-4))
                if aspect > 15.0 or conf < 30:
                    suspicious_boxes += 1

                if len(ocr_data['boxes']) < 50:  # store sample boxes
                    ocr_data['boxes'].append({
                        'text': text, 'conf': conf, 'x': x, 'y': y, 'w': w, 'h': h
                    })

        ocr_data['word_count'] = len(words)
        ocr_data['extracted_text_preview'] = " ".join(words[:40]) + ("..." if len(words) > 40 else "")
        
        if confidences:
            c_np = np.array(confidences, dtype=np.float64)
            ocr_data['mean_confidence'] = float(np.mean(c_np))
            ocr_data['confidence_variance'] = float(np.var(c_np))
            features['ocr_confidence_variance'] = ocr_data['confidence_variance']

        if baselines:
            # Baseline alignment variance modulo standard line height
            b_np = np.array(baselines, dtype=np.float64)
            diffs = np.abs(np.diff(b_np))
            features['layout_text_alignment_variance'] = float(np.var(diffs)) if len(diffs) > 0 else 0.0
            ocr_data['baseline_variance'] = features['layout_text_alignment_variance']

        features['ocr_suspicious_box_count'] = float(suspicious_boxes)
        ocr_data['suspicious_box_count'] = suspicious_boxes

    except Exception as e:
        # Fallback to morphological contour text-line layout analysis
        ocr_data['available'] = False
        ocr_data['note'] = f"Tesseract engine not accessible or errored: {str(e)[:80]}. Used morphological layout fallback."
        
        if image_np.ndim == 3:
            gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            gray = image_np.copy()
            
        # Detect text lines via horizontal dilation
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 2))
        dilated = cv2.dilate(thresh, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        box_y = []
        suspicious_cnt = 0
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if w > 20 and h > 5:
                box_y.append(y + h)
                if w / h > 25.0:
                    suspicious_cnt += 1
                    
        if box_y:
            diffs = np.abs(np.diff(np.array(box_y, dtype=np.float64)))
            features['layout_text_alignment_variance'] = float(np.var(diffs)) if len(diffs) > 0 else 0.0
            features['ocr_suspicious_box_count'] = float(suspicious_cnt)
            ocr_data['baseline_variance'] = features['layout_text_alignment_variance']
            ocr_data['suspicious_box_count'] = suspicious_cnt

    return ocr_data, features
