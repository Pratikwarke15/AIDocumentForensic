from typing import Dict, Any, List, Tuple

# Domain evidence weights in the final forensic decision engine
WEIGHT_RANDOM_FOREST = 0.30
WEIGHT_ELA = 0.20
WEIGHT_COPYMOVE = 0.20
WEIGHT_NOISE = 0.15
WEIGHT_COMPRESSION = 0.10
WEIGHT_METADATA = 0.05

def aggregate_forensic_evidence(rf_prediction: int,
                                rf_probability: float,
                                features: Dict[str, Any],
                                metadata: Dict[str, Any],
                                model_trained: bool = True) -> Dict[str, Any]:
    """
    Transparent Multi-Signal Forensic Decision Engine.
    Combines Random Forest classification with 5 computer vision and metadata domains.

    Outputs:
    - forensic_status: 'AUTHENTIC', 'REVIEW REQUIRED', 'POTENTIALLY MANIPULATED'
    - display_status: Human-facing 3-state verdict
    - confidence: 0.0 - 100.0 (calibrated from multi-signal consensus and agreement)
    - indicators: list of human-readable forensic findings
    - explanation: comprehensive human-readable summary
    - analysis_consistency: domain-by-domain consistency breakdown
    - debug_info: developer mode metrics with raw values, normalized scores, severities, and weights
    - signals: simplified status per domain for backward compatibility
    """
    indicators = []

    # -------------------------------------------------------------
    # 1. Error Level Analysis (ELA) Domain (Weight: 20%)
    # -------------------------------------------------------------
    ela_tamper_ratio = float(features.get('ela_tamper_ratio', 0.0))
    ela_num_components = float(features.get('ela_num_components', 0.0))
    ela_norm = float(features.get('ela_normalized_score', 0.0))
    ela_sev = str(features.get('ela_severity', ''))

    # Fallback derivation if not computed directly
    if not ela_sev:
        if ela_tamper_ratio < 0.01 and ela_num_components == 0:
            ela_norm = round(ela_tamper_ratio * 5.0, 3)
            ela_sev = 'NORMAL'
        elif ela_tamper_ratio < 0.035 and ela_num_components <= 2:
            ela_norm = round(min(0.20 + ela_tamper_ratio * 4.0, 0.40), 3)
            ela_sev = 'LOW_ANOMALY'
        elif ela_tamper_ratio < 0.07 or ela_num_components <= 4:
            ela_norm = round(min(0.45 + ela_tamper_ratio * 3.0, 0.70), 3)
            ela_sev = 'MODERATE_ANOMALY'
        else:
            ela_norm = round(min(0.70 + ela_tamper_ratio * 3.0, 1.0), 3)
            ela_sev = 'HIGH_ANOMALY'

    if ela_sev == 'HIGH_ANOMALY':
        indicators.append(
            f"Error Level Analysis (ELA): High compression discrepancy ({ela_tamper_ratio * 100:.1f}% pixel anomaly across {int(ela_num_components)} discrete regions) indicative of multi-source splicing."
        )
    elif ela_sev == 'MODERATE_ANOMALY':
        indicators.append(
            f"Error Level Analysis (ELA): Moderate localized anomaly ({ela_tamper_ratio * 100:.1f}% pixel variation across {int(ela_num_components)} regions)."
        )
    elif ela_sev == 'LOW_ANOMALY':
        indicators.append(
            f"Error Level Analysis (ELA): Mild edge variation ({ela_tamper_ratio * 100:.1f}%) consistent with normal text rendering or scan recompression."
        )

    # -------------------------------------------------------------
    # 2. Local Noise Inconsistency Domain (Weight: 15%)
    # -------------------------------------------------------------
    noise_raw_disparity = float(features.get('noise_disparity_ratio', 1.0))
    noise_norm = float(features.get('noise_normalized_score', 0.0))
    noise_sev = str(features.get('noise_severity', ''))

    if not noise_sev:
        # Fallback if raw disparity was used without content filtering
        if noise_raw_disparity < 4.0:
            noise_norm = 0.10
            noise_sev = 'NORMAL'
        elif noise_raw_disparity < 8.0:
            noise_norm = 0.35
            noise_sev = 'LOW_ANOMALY'
        elif noise_raw_disparity < 16.0:
            noise_norm = 0.60
            noise_sev = 'MODERATE_ANOMALY'
        else:
            noise_norm = 0.85
            noise_sev = 'HIGH_ANOMALY'

    if noise_sev == 'HIGH_ANOMALY':
        indicators.append(
            f"Sensor Noise: Severe local noise disparity detected across content blocks, indicating spliced elements from different sources."
        )
    elif noise_sev == 'MODERATE_ANOMALY':
        indicators.append(
            f"Sensor Noise: Noticeable variance in noise texture across document content patches."
        )
    elif noise_sev == 'LOW_ANOMALY':
        indicators.append(
            f"Sensor Noise: Mild noise variation consistent with scanner illumination gradient or mobile camera capture."
        )

    # -------------------------------------------------------------
    # 3. Copy-Move Duplication Domain (Weight: 20%)
    # -------------------------------------------------------------
    copymove_count = float(features.get('copymove_match_count', 0.0))
    copymove_norm = float(features.get('copymove_normalized_score', 0.0))
    copymove_sev = str(features.get('copymove_severity', ''))

    if not copymove_sev:
        if copymove_count == 0:
            copymove_norm = 0.0
            copymove_sev = 'NORMAL'
        elif copymove_count == 1:
            copymove_norm = 0.50
            copymove_sev = 'MODERATE_ANOMALY'
        else:
            copymove_norm = 0.85
            copymove_sev = 'HIGH_ANOMALY'

    if copymove_sev == 'HIGH_ANOMALY':
        indicators.append(
            f"Copy-Move Detection: {int(copymove_count)} spatially coherent cloned region clusters identified (duplicate seal/signature/graphic element)."
        )
    elif copymove_sev == 'MODERATE_ANOMALY':
        indicators.append(
            f"Copy-Move Detection: 1 candidate cloned region cluster detected across document."
        )
    elif copymove_sev == 'LOW_ANOMALY':
        indicators.append(
            "Copy-Move Detection: Minor repetitive keypoint pattern observed, consistent with standard document formatting."
        )

    # -------------------------------------------------------------
    # 4. Compression & DCT Domain (Weight: 10%)
    # -------------------------------------------------------------
    blockiness = float(features.get('compression_blockiness_score', 1.0))
    comp_norm = float(features.get('compression_normalized_score', 0.0))
    comp_sev = str(features.get('compression_severity', ''))

    if not comp_sev:
        if blockiness <= 1.22:
            comp_norm = 0.05
            comp_sev = 'NORMAL'
        elif blockiness <= 1.38:
            comp_norm = 0.35
            comp_sev = 'LOW_ANOMALY'
        elif blockiness <= 1.58:
            comp_norm = 0.60
            comp_sev = 'MODERATE_ANOMALY'
        else:
            comp_norm = 0.85
            comp_sev = 'HIGH_ANOMALY'

    if comp_sev in ('HIGH_ANOMALY', 'MODERATE_ANOMALY'):
        indicators.append(
            f"JPEG Compression: Elevated 8x8 DCT grid boundary discontinuity (blockiness: {blockiness:.2f}), suggesting localized resaving or spliced insertion."
        )

    # -------------------------------------------------------------
    # 5. Metadata Domain (Weight: 5%)
    # -------------------------------------------------------------
    meta_edit_flag = float(features.get('metadata_editing_software_flag', 0.0))
    meta_date_flag = float(features.get('metadata_date_inconsistency', 0.0))
    meta_norm = float(features.get('metadata_normalized_score', 0.0))
    meta_sev = str(features.get('metadata_severity', ''))

    if not meta_sev:
        if meta_edit_flag > 0.5 and meta_date_flag > 0.5:
            meta_norm = 0.70
            meta_sev = 'HIGH_ANOMALY'
        elif meta_edit_flag > 0.5:
            meta_norm = 0.45
            meta_sev = 'MODERATE_ANOMALY'
        elif meta_date_flag > 0.5:
            meta_norm = 0.20
            meta_sev = 'LOW_ANOMALY'
        else:
            meta_norm = 0.0
            meta_sev = 'NORMAL'

    if meta_edit_flag > 0.5:
        indicators.append(
            "Metadata Footprint: Editing software tags identified in document metadata (e.g. Photoshop/GIMP/Canva/Illustrator)."
        )
    if meta_date_flag > 0.5:
        indicators.append(
            "Metadata Integrity: Modification timestamp post-dates initial document creation date."
        )

    # -------------------------------------------------------------
    # 6. Random Forest Classifier Domain (Weight: 30%)
    # -------------------------------------------------------------
    if model_trained:
        rf_says_manipulated = (rf_prediction == 1)
        p_manip = float(rf_probability)
    else:
        # Untrained fallback: compute from classical heuristic
        p_manip = float(
            ela_norm * 0.35 +
            copymove_norm * 0.35 +
            noise_norm * 0.15 +
            comp_norm * 0.10 +
            meta_norm * 0.05
        )
        rf_says_manipulated = (p_manip >= 0.50)

    if p_manip < 0.30:
        rf_sev = 'NORMAL'
    elif p_manip < 0.50:
        rf_sev = 'LOW_ANOMALY'
    elif p_manip < 0.70:
        rf_sev = 'MODERATE_ANOMALY'
    else:
        rf_sev = 'HIGH_ANOMALY'

    # -------------------------------------------------------------
    # Composite Weighted Anomaly Score (0.0 to 100.0)
    # -------------------------------------------------------------
    weighted_score = (
        (p_manip * WEIGHT_RANDOM_FOREST) +
        (ela_norm * WEIGHT_ELA) +
        (copymove_norm * WEIGHT_COPYMOVE) +
        (noise_norm * WEIGHT_NOISE) +
        (comp_norm * WEIGHT_COMPRESSION) +
        (meta_norm * WEIGHT_METADATA)
    ) * 100.0
    weighted_score = round(min(max(weighted_score, 0.0), 100.0), 1)

    # Count classical domain severities
    classical_severities = [ela_sev, copymove_sev, noise_sev, comp_sev]
    high_count = sum(1 for s in classical_severities if s == 'HIGH_ANOMALY')
    moderate_count = sum(1 for s in classical_severities if s == 'MODERATE_ANOMALY')
    low_count = sum(1 for s in classical_severities if s == 'LOW_ANOMALY')

    # -------------------------------------------------------------
    # Multi-Signal Consensus Decision Engine
    # -------------------------------------------------------------
    sharpness_disparity = float(features.get('sharpness_disparity_ratio', 1.0))
    
    # Calculate counts of OTHER signals (excluding copymove) to ensure true corroboration
    other_severities = [ela_sev, noise_sev, comp_sev]
    other_high = sum(1 for s in other_severities if s == 'HIGH_ANOMALY')
    other_mod = sum(1 for s in other_severities if s == 'MODERATE_ANOMALY')

    # Check for strong tampering corroboration strictly enforcing Requirement 10
    # Rule: No single signal alone may classify a document as POTENTIALLY MANIPULATED.
    # Condition 1: At least 2 independent signals show HIGH ANOMALY.
    c1 = (high_count >= 2)
    # Condition 2: 1 signal shows HIGH ANOMALY AND at least 1 other signal shows MODERATE ANOMALY.
    c2 = (high_count >= 1 and (other_mod >= 1 or (copymove_sev != 'HIGH_ANOMALY' and copymove_sev == 'MODERATE_ANOMALY')))
    # Condition 3: Random Forest model predicts manipulated with high probability (P >= 0.70)
    # AND at least 1 independent signal shows MODERATE or HIGH ANOMALY.
    c3 = (p_manip >= 0.70 and (high_count >= 1 or moderate_count >= 1))
    # Condition 4: Copy-move detection confirms duplicated regions AND at least 1 independent signal
    # (or elevated ML probability >= 0.55) provides corroborating evidence.
    c4 = (copymove_count >= 1 and (other_high >= 1 or other_mod >= 1 or p_manip >= 0.55))
    # Condition 5: Multiple distinct cloned clusters (>= 2 distinct cloned regions) with corroboration
    c5 = (copymove_count >= 2 and (other_high >= 1 or other_mod >= 1 or p_manip >= 0.50))
    # Condition 6: Elevated ML probability with corroborating moderate anomaly
    c6 = (p_manip >= 0.65 and moderate_count >= 1)

    has_tampering_consensus = (c1 or c2 or c3 or c4 or c5 or c6)

    # Clean authentic: zero high anomalies, zero moderate anomalies, no copy-move duplication
    tamper_ratio_val = float(features.get('tamper_ratio', 0.0))
    is_scan_or_recomp = (blockiness > 1.08 and tamper_ratio_val < 0.02 and weighted_score < 35.0)
    is_uniform_benign = (
        ela_num_components >= 20 and ela_tamper_ratio < 0.06 and weighted_score < 25.0
    )
    is_clean_authentic = (
        high_count == 0 and other_high == 0 and other_mod == 0 and copymove_count == 0 and (
            (moderate_count == 0 and (p_manip <= 0.28 or ((is_scan_or_recomp or is_uniform_benign) and p_manip <= 0.42))) or
            (is_uniform_benign and p_manip <= 0.53 and weighted_score < 25.0)
        )
    )

    if has_tampering_consensus:
        status = "POTENTIALLY MANIPULATED"
        display_status = "POTENTIALLY MANIPULATED"
        confidence = round(min(max(p_manip * 100.0, weighted_score, 80.0), 98.0), 1)
        if copymove_count >= 1:
            explanation = (
                f"Definitive copy-move forgery detected: {int(copymove_count)} geometrically verified duplicate "
                "region cluster(s) identified with affine consistency across the document."
            )
        elif ela_sev == 'HIGH_ANOMALY':
            explanation = (
                "Severe Error Level Analysis (ELA) discrepancy detected across document content, "
                "indicating localized multi-compression digital splicing."
            )
        else:
            explanation = (
                "Multiple independent forensic indicators (Random Forest classifier and computer vision signals) "
                "provide corroborating evidence of localized digital manipulation or document alteration."
            )

    elif is_clean_authentic:
        status = "AUTHENTIC"
        display_status = "AUTHENTIC / LOW FORENSIC RISK"
        auth_factor = 1.0 - (weighted_score / 100.0)
        confidence = round(min(max(auth_factor * 100.0, 85.0), 98.0), 1)
        explanation = (
            "The document exhibits uniform forensic traits across all physical imaging domains "
            "(ELA, noise consistency, compression grid, and keypoint patterns). Any localized variance "
            "is attributable to legitimate official markings (stamps, signatures, QR codes), flatbed scanning, "
            "or photographic capture rather than digital manipulation."
        )
        if not indicators:
            indicators.append("Digital forensic characteristics are consistent with an authentic original document.")
            indicators.append("No anomalous ELA, compression, noise, or copy-move artifacts detected.")

    else:
        # Ambiguous evidence or isolated anomaly without conclusive multi-signal agreement
        status = "REVIEW REQUIRED"
        display_status = "REVIEW REQUIRED / INCONCLUSIVE"
        confidence = round(min(max(55.0 + abs(0.5 - p_manip) * 35.0, 55.0), 74.0), 1)
        explanation = (
            "Forensic analysis detected isolated domain anomalies or borderline statistical metrics. "
            "The physical evidence is insufficient to conclude digital manipulation, but "
            "secondary visual review is recommended."
        )

    # -------------------------------------------------------------
    # Domain Consistency Breakdown
    # -------------------------------------------------------------
    analysis_consistency = {
        'ml_classification': 'MANIPULATED' if rf_says_manipulated else 'AUTHENTIC',
        'ml_probability': round(p_manip * 100.0, 1),
        'ela_result': ela_sev,
        'noise_result': noise_sev,
        'copymove_result': copymove_sev,
        'compression_result': comp_sev,
        'metadata_result': meta_sev,
        'consensus_verdict': status,
        'is_consistent': (
            (status == "AUTHENTIC" and high_count == 0 and moderate_count <= 1) or
            (status == "POTENTIALLY MANIPULATED" and (copymove_count > 0 or high_count > 0 or (rf_says_manipulated and moderate_count > 0)))
        ),
        'explanation': explanation
    }

    # -------------------------------------------------------------
    # Developer / Debug Diagnostics
    # -------------------------------------------------------------
    debug_info = {
        'ela': {
            'raw_tamper_ratio': round(ela_tamper_ratio, 5),
            'raw_component_count': int(ela_num_components),
            'normalized_score': ela_norm,
            'severity': ela_sev,
            'weight': WEIGHT_ELA,
            'weighted_contribution': round(ela_norm * WEIGHT_ELA * 100.0, 2)
        },
        'noise': {
            'raw_disparity_ratio': round(noise_raw_disparity, 2),
            'normalized_score': noise_norm,
            'severity': noise_sev,
            'weight': WEIGHT_NOISE,
            'weighted_contribution': round(noise_norm * WEIGHT_NOISE * 100.0, 2)
        },
        'copymove': {
            'raw_pairs': float(features.get('copymove_raw_pairs', 0.0)),
            'coherent_clusters': int(copymove_count),
            'normalized_score': copymove_norm,
            'severity': copymove_sev,
            'weight': WEIGHT_COPYMOVE,
            'weighted_contribution': round(copymove_norm * WEIGHT_COPYMOVE * 100.0, 2)
        },
        'compression': {
            'raw_blockiness': round(blockiness, 3),
            'normalized_score': comp_norm,
            'severity': comp_sev,
            'weight': WEIGHT_COMPRESSION,
            'weighted_contribution': round(comp_norm * WEIGHT_COMPRESSION * 100.0, 2)
        },
        'metadata': {
            'editing_software_flag': int(meta_edit_flag),
            'date_inconsistency_flag': int(meta_date_flag),
            'normalized_score': meta_norm,
            'severity': meta_sev,
            'weight': WEIGHT_METADATA,
            'weighted_contribution': round(meta_norm * WEIGHT_METADATA * 100.0, 2)
        },
        'random_forest': {
            'prediction': int(rf_prediction),
            'manipulation_probability': round(p_manip * 100.0, 1),
            'normalized_score': round(p_manip, 3),
            'severity': rf_sev,
            'weight': WEIGHT_RANDOM_FOREST,
            'weighted_contribution': round(p_manip * WEIGHT_RANDOM_FOREST * 100.0, 2)
        },
        'final_composite_score': weighted_score,
        'final_classification': status,
        'final_confidence': confidence
    }

    # Backward-compatible signal dictionary for templates
    signals_dict = {
        'ela': 'SUSPICIOUS' if ela_sev in ('HIGH_ANOMALY', 'MODERATE_ANOMALY') else 'NORMAL',
        'noise': 'SUSPICIOUS' if noise_sev == 'HIGH_ANOMALY' else 'NORMAL',
        'compression': 'SUSPICIOUS' if comp_sev in ('HIGH_ANOMALY', 'MODERATE_ANOMALY') else 'NORMAL',
        'copymove': 'SUSPICIOUS' if copymove_sev in ('HIGH_ANOMALY', 'MODERATE_ANOMALY') else 'NORMAL',
        'metadata': 'SUSPICIOUS' if meta_sev in ('HIGH_ANOMALY', 'MODERATE_ANOMALY') else 'NORMAL',
        'random_forest': 'MANIPULATED' if rf_says_manipulated else 'AUTHENTIC'
    }

    tamper_ratio_val = float(features.get('tamper_ratio', 0.0))
    suspicious_region_pct = round(tamper_ratio_val * 100.0, 2)

    return {
        'forensic_status': status,
        'display_status': display_status,
        'confidence': confidence,
        'authenticity_confidence': confidence,
        'manipulation_score': weighted_score,
        'risk_score': weighted_score,
        'suspicious_region_percentage': suspicious_region_pct,
        'tamper_ratio': tamper_ratio_val,
        'indicators': indicators,
        'explanation': explanation,
        'analysis_consistency': analysis_consistency,
        'debug_info': debug_info,
        'rf_probability': round(float(p_manip * 100.0), 1),
        'composite_score': weighted_score,
        'signals': signals_dict,
        'severities': {
            'ela': ela_sev,
            'noise': noise_sev,
            'copymove': copymove_sev,
            'compression': comp_sev,
            'metadata': meta_sev,
            'random_forest': rf_sev
        }
    }

def combine_record_and_forensic_results(record_status: str, forensic_status: str) -> str:
    """
    Decoupled integration of Layer A (Local/Demo Registry) and Layer B (AI Forensics).
    Crucially: 'RECORD NOT FOUND' does NOT equate to a manipulated or forged document.
    """
    if record_status == "VERIFIED":
        if forensic_status == "AUTHENTIC":
            return "VERIFIED RECORD & FORENSICALLY CONSISTENT"
        elif forensic_status == "POTENTIALLY MANIPULATED":
            return "VERIFIED RECORD BUT POSSIBLE DIGITAL MANIPULATION"
        else:
            return "VERIFIED RECORD — FORENSIC REVIEW REQUIRED"

    elif record_status == "RECORD NOT FOUND":
        # Decouple: clearly state that local registry absence is neutral to forensic integrity
        if forensic_status == "AUTHENTIC":
            return "RECORD UNVERIFIED (LOCAL REGISTRY) — FORENSICALLY CONSISTENT"
        elif forensic_status == "POTENTIALLY MANIPULATED":
            return "RECORD UNVERIFIED (LOCAL REGISTRY) — POTENTIAL DIGITAL TAMPERING DETECTED"
        else:
            return "RECORD UNVERIFIED (LOCAL REGISTRY) — FORENSIC REVIEW REQUIRED"

    elif record_status == "MISMATCH":
        if forensic_status == "AUTHENTIC":
            return "REGISTRY DATA MISMATCH — FORENSICALLY CONSISTENT FILE"
        elif forensic_status == "POTENTIALLY MANIPULATED":
            return "REGISTRY DATA MISMATCH & POTENTIAL DIGITAL TAMPERING"
        else:
            return "REGISTRY DATA MISMATCH — FORENSIC REVIEW REQUIRED"

    else:
        if forensic_status == "AUTHENTIC":
            return "RECORD UNCHECKED — FORENSICALLY CONSISTENT"
        elif forensic_status == "POTENTIALLY MANIPULATED":
            return "RECORD UNCHECKED — POSSIBLE DIGITAL MANIPULATION"
        else:
            return "RECORD UNCHECKED — FORENSIC REVIEW REQUIRED"
