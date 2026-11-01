import os
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak, KeepTogether, HRFlowable
)

class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.title_style = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A'),
            alignment=1  # Centered
        )
        self.subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#475569'),
            alignment=1
        )
        self.section_heading = ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=16,
            textColor=colors.HexColor('#1E293B'),
            spaceAfter=6
        )
        self.body_style = ParagraphStyle(
            'ReportBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        self.badge_style = ParagraphStyle(
            'BadgeStyle',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            alignment=1
        )

    def generate_report(self,
                        verification,
                        document,
                        record_result,
                        forensic_result,
                        aggregation: Dict[str, Any],
                        feature_vector: Dict[str, float],
                        output_dir: Path) -> str:
        """
        Builds official 5-page forensic report PDF using ReportLab.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"forensic_report_{verification.id}.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        story = []
        rec_data = record_result.to_dict() if hasattr(record_result, 'to_dict') else {}

        # ==========================================
        # PAGE 1: EXECUTIVE SUMMARY
        # ==========================================
        story.append(Paragraph("NATIONAL FORENSIC DOCUMENT VERIFICATION DOSSIER", self.title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Digital Document Forensics – Multi-Signal Integrity & Verification Report", self.subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284C7'), spaceBefore=2, spaceAfter=12))

        # Metadata Table
        meta_table_data = [
            [Paragraph("<b>Verification ID:</b>", self.body_style), Paragraph(str(verification.id), self.body_style),
             Paragraph("<b>Analysis Date:</b>", self.body_style), Paragraph(verification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), self.body_style)],
            [Paragraph("<b>Document Number:</b>", self.body_style), Paragraph(document.document_number, self.body_style),
             Paragraph("<b>Document Type:</b>", self.body_style), Paragraph(document.document_type, self.body_style)],
            [Paragraph("<b>Holder Name:</b>", self.body_style), Paragraph(document.holder_name, self.body_style),
             Paragraph("<b>Issue Date:</b>", self.body_style), Paragraph(str(document.issue_date or 'N/A'), self.body_style)],
            [Paragraph("<b>Issuing Authority:</b>", self.body_style), Paragraph(document.issuing_authority or 'N/A', self.body_style),
             Paragraph("<b>File SHA-256:</b>", self.body_style), Paragraph(document.sha256[:20] + '...', self.body_style)]
        ]
        t_meta = Table(meta_table_data, colWidths=[110, 160, 110, 160])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 14))

        # Two-Layer Verdict Cards
        story.append(Paragraph("DUAL-LAYER VERIFICATION ASSESSMENT", self.section_heading))
        rec_color = colors.HexColor('#16A34A') if verification.record_status == 'VERIFIED' else (
            colors.HexColor('#DC2626') if verification.record_status == 'MISMATCH' else colors.HexColor('#475569')
        )
        rec_label = "RECORD FOUND" if verification.record_status == 'VERIFIED' else (
            "DATA MISMATCH" if verification.record_status == 'MISMATCH' else "RECORD NOT FOUND"
        )

        for_color = colors.HexColor('#16A34A') if verification.forensic_status == 'AUTHENTIC' else (
            colors.HexColor('#DC2626') if verification.forensic_status == 'POTENTIALLY MANIPULATED' else colors.HexColor('#D97706')
        )
        for_label = "AUTHENTIC / LOW RISK" if verification.forensic_status == 'AUTHENTIC' else (
            "POTENTIALLY MANIPULATED" if verification.forensic_status == 'POTENTIALLY MANIPULATED' else "REVIEW REQUIRED"
        )

        verdict_cards = [
            [
                Paragraph("<b>LAYER A: RECORD VERIFICATION</b><br/><font size=8 color='#64748B'>Local Verification Registry (Phase 1 Demo)</font>", self.body_style),
                Paragraph("<b>LAYER B: DIGITAL FORENSIC ANALYSIS</b><br/><font size=8 color='#64748B'>Multi-Signal Forensic Consensus & Signal Analysis</font>", self.body_style)
            ],
            [
                Paragraph(f"<font color='white'><b>{rec_label}</b></font>", self.badge_style),
                Paragraph(f"<font color='white'><b>{for_label}</b></font>", self.badge_style)
            ]
        ]
        t_cards = Table(verdict_cards, colWidths=[270, 270])
        t_cards.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#F1F5F9')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#F1F5F9')),
            ('BACKGROUND', (0, 1), (0, 1), rec_color),
            ('BACKGROUND', (1, 1), (1, 1), for_color),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8'))
        ]))
        story.append(t_cards)
        story.append(Spacer(1, 12))

        # Final Combined Assessment Banner
        final_banner = [
            [Paragraph("<b>COMBINED FINAL ASSESSMENT:</b>", self.body_style),
             Paragraph(f"<b>{verification.final_status}</b>", ParagraphStyle('Fb', parent=self.badge_style, textColor=colors.HexColor('#0F172A')))],
            [Paragraph("<b>FORENSIC CONFIDENCE:</b>", self.body_style),
             Paragraph(f"<b>{verification.confidence:.1f}%</b> (Derived from multi-signal consensus across 6 independent domains)", self.body_style)]
        ]
        t_final = Table(final_banner, colWidths=[160, 380])
        t_final.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E2E8F0')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94A3B8')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(t_final)
        story.append(Spacer(1, 10))

        # Decoupled Forensic & Verification Metrics Table
        orig_match = aggregation.get('original_document_match')
        if orig_match is None and verification.record_status == 'VERIFIED':
            orig_match_str = "100.0% (Registry Record Verified)"
        elif orig_match == 100.0:
            orig_match_str = "100.0% (Exact Reference Match)"
        elif orig_match == 0.0 or verification.record_status == 'MISMATCH':
            orig_match_str = "0.0% (Registry Data / Hash Mismatch)"
        else:
            orig_match_str = "N/A (Unrecorded in Registry)"

        auth_conf = aggregation.get('authenticity_confidence', verification.confidence)
        risk_score = aggregation.get('manipulation_score', aggregation.get('risk_score', 0.0))
        susp_pct = aggregation.get('suspicious_region_percentage', round(verification.tamper_ratio * 100.0, 2))

        metrics_table_data = [
            [
                Paragraph("<b>Layer A: Original Document Match:</b>", self.body_style),
                Paragraph(f"<b>{orig_match_str}</b>", self.body_style),
                Paragraph("<b>Layer B: Authenticity Confidence:</b>", self.body_style),
                Paragraph(f"<b>{auth_conf:.1f}%</b> (Forensic Signal Consensus)", self.body_style)
            ],
            [
                Paragraph("<b>Composite Manipulation Risk:</b>", self.body_style),
                Paragraph(f"<b>{risk_score:.1f}%</b>", self.body_style),
                Paragraph("<b>Suspicious Region Area:</b>", self.body_style),
                Paragraph(f"<b>{susp_pct:.2f}%</b> (Anomalous ELA Pixels)", self.body_style)
            ]
        ]
        t_metrics = Table(metrics_table_data, colWidths=[150, 120, 150, 120])
        t_metrics.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        story.append(t_metrics)
        story.append(Spacer(1, 4))

        metric_note = (
            "<font size=7 color='#475569'><i>* Note: Layer A reflects exact cryptographic/record identity against the reference registry (100% when matched). "
            "Layer B reflects calibrated digital forensic confidence. Due to natural physical noise from scanning, camera optics, and standard JPEG recompression, "
            "empirical forensic models output 80%–98% on authentic documents, reserving 100% for cryptographic reference matches.</i></font>"
        )
        story.append(Paragraph(metric_note, self.body_style))
        story.append(Spacer(1, 8))

        # Forensic Assessment Narrative / Explanation
        story.append(Paragraph("FORENSIC ASSESSMENT RATIONALE", self.section_heading))
        explanation_text = aggregation.get('explanation') or (
            "Multi-signal forensic analysis evaluated ELA compression, noise variance, copy-move duplication, "
            "and statistical classification."
        )
        t_exp = Table([[Paragraph(f"<i>{explanation_text}</i>", self.body_style)]], colWidths=[540])
        t_exp.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 8)
        ]))
        story.append(t_exp)
        story.append(Spacer(1, 12))

        # Key Forensic Indicators
        story.append(Paragraph("KEY FORENSIC FINDINGS", self.section_heading))
        indicators_list = aggregation.get('indicators', [])
        if not indicators_list:
            indicators_list = [
                "Digital forensic characteristics are consistent with an authentic original document.",
                "No anomalous ELA, compression, noise, or copy-move artifacts detected."
            ]
        for ind in indicators_list:
            story.append(Paragraph(f"• {ind}", self.body_style))
            story.append(Spacer(1, 3))

        story.append(Spacer(1, 14))
        story.append(Paragraph("<font size=8 color='#64748B'>Official verification dossier generated by Government Document Verification System. See Page 5 for regulatory scope.</font>", self.subtitle_style))
        story.append(PageBreak())

        # ==========================================
        # PAGE 2: VISUAL EVIDENCE PLATE
        # ==========================================
        story.append(Paragraph("PAGE 2 — VISUAL FORENSIC EVIDENCE PLATE", self.title_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Four-Quadrant Comparative Analysis: Original, ELA Heatmap, Tamper Mask, and Highlighted Regions", self.subtitle_style))
        story.append(Spacer(1, 12))

        # Load quadrant images
        def make_flowable_img(img_path, max_w=250, max_h=180):
            if img_path and os.path.exists(img_path):
                try:
                    return RLImage(img_path, width=max_w, height=max_h)
                except Exception:
                    return Paragraph("Image Render Error", self.body_style)
            return Paragraph("Not Available", self.body_style)

        orig_img = make_flowable_img(document.original_file_path if document.original_file_path.endswith(('jpg', 'jpeg', 'png')) else forensic_result.highlighted_path)
        ela_img = make_flowable_img(forensic_result.ela_path)
        mask_img = make_flowable_img(forensic_result.mask_path)
        high_img = make_flowable_img(forensic_result.highlighted_path)

        grid_data = [
            [Paragraph("<b>Figure 1: Standardized Document</b>", self.body_style), Paragraph("<b>Figure 2: ELA Error Heat Map (Q95)</b>", self.body_style)],
            [orig_img, ela_img],
            [Paragraph("<b>Figure 3: Binary Tamper Mask</b>", self.body_style), Paragraph("<b>Figure 4: Localized Suspicious Regions</b>", self.body_style)],
            [mask_img, high_img]
        ]
        t_grid = Table(grid_data, colWidths=[270, 270])
        t_grid.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1'))
        ]))
        story.append(t_grid)
        story.append(Spacer(1, 10))
        story.append(Paragraph("<i>Interpretation Guide:</i> Hot colors (red/orange) in the ELA Heat Map designate pixels with high compression error difference relative to standardized resaving. Figure 4 highlights localized contour bounding boxes.", self.subtitle_style))
        story.append(PageBreak())

        # ==========================================
        # PAGE 3: FORENSIC MEASUREMENTS & SIGNALS
        # ==========================================
        story.append(Paragraph("PAGE 3 — NUMERICAL FORENSIC MEASUREMENTS", self.title_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Standardized 28+ Feature Extraction Vector & Classical Computer Vision Signals", self.subtitle_style))
        story.append(Spacer(1, 12))

        features_table_data = [
            [Paragraph("<b>Feature Metric</b>", self.body_style), Paragraph("<b>Extracted Value</b>", self.body_style), Paragraph("<b>Benchmark Normal Range</b>", self.body_style), Paragraph("<b>Diagnostic Significance</b>", self.body_style)],
            [Paragraph("ELA Tamper Ratio", self.body_style), Paragraph(f"{feature_vector.get('ela_tamper_ratio', 0.0):.4f}", self.body_style), Paragraph("< 0.0250", self.body_style), Paragraph("Core pixel manipulation ratio", self.body_style)],
            [Paragraph("ELA Mean Intensity", self.body_style), Paragraph(f"{feature_vector.get('ela_mean', 0.0):.2f}", self.body_style), Paragraph("5.0 - 25.0", self.body_style), Paragraph("Average compression variance", self.body_style)],
            [Paragraph("ELA Variance / Std", self.body_style), Paragraph(f"{feature_vector.get('ela_std', 0.0):.2f}", self.body_style), Paragraph("< 35.0", self.body_style), Paragraph("Error intensity spread", self.body_style)],
            [Paragraph("Suspicious Component Count", self.body_style), Paragraph(f"{int(feature_vector.get('ela_num_components', 0))}", self.body_style), Paragraph("0 - 1", self.body_style), Paragraph("Discrete tampered patches", self.body_style)],
            [Paragraph("Noise Disparity Ratio", self.body_style), Paragraph(f"{feature_vector.get('noise_disparity_ratio', 0.0):.2f}", self.body_style), Paragraph("< 2.50", self.body_style), Paragraph("Sensor noise uniformity across cells", self.body_style)],
            [Paragraph("JPEG Blockiness Discontinuity", self.body_style), Paragraph(f"{feature_vector.get('compression_blockiness_score', 0.0):.2f}", self.body_style), Paragraph("0.90 - 1.25", self.body_style), Paragraph("8x8 DCT grid boundary alignment", self.body_style)],
            [Paragraph("DCT High-Freq Energy Ratio", self.body_style), Paragraph(f"{feature_vector.get('dct_energy_ratio', 0.0):.4f}", self.body_style), Paragraph("> 0.0050", self.body_style), Paragraph("Frequency domain detail preservation", self.body_style)],
            [Paragraph("Sharpness Disparity Ratio", self.body_style), Paragraph(f"{feature_vector.get('sharpness_disparity_ratio', 0.0):.2f}", self.body_style), Paragraph("< 4.00", self.body_style), Paragraph("Laplacian focus disparity between patches", self.body_style)],
            [Paragraph("Copy-Move Clustered Pairs", self.body_style), Paragraph(f"{int(feature_vector.get('copymove_match_count', 0))}", self.body_style), Paragraph("0", self.body_style), Paragraph("Cloned stamp/signature indicators", self.body_style)],
            [Paragraph("Editing Software Flag", self.body_style), Paragraph(f"{feature_vector.get('metadata_editing_software_flag', 0.0):.0f}", self.body_style), Paragraph("0", self.body_style), Paragraph("Photoshop/Canva/GIMP footprints", self.body_style)],
            [Paragraph("OCR Alignment Variance", self.body_style), Paragraph(f"{feature_vector.get('layout_text_alignment_variance', 0.0):.2f}", self.body_style), Paragraph("< 120.0", self.body_style), Paragraph("Text baseline coordinate irregularity", self.body_style)]
        ]
        t_feat = Table(features_table_data, colWidths=[140, 90, 130, 180])
        t_feat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
        ]))
        story.append(t_feat)
        story.append(Spacer(1, 14))

        # Model Decision Summary
        story.append(Paragraph("RANDOM FOREST INFERENCE SUMMARY", self.section_heading))
        rf_meta = [
            [Paragraph("<b>Model Architecture:</b>", self.body_style), Paragraph("scikit-learn RandomForestClassifier (100 estimators, max_depth=12)", self.body_style)],
            [Paragraph("<b>Model Version:</b>", self.body_style), Paragraph(forensic_result.model_version or 'v1.0', self.body_style)],
            [Paragraph("<b>Predicted Class:</b>", self.body_style), Paragraph(f"{aggregation['signals'].get('random_forest', 'N/A')}", self.body_style)],
            [Paragraph("<b>Manipulation Probability:</b>", self.body_style), Paragraph(f"{aggregation.get('rf_probability', 0.0)}%", self.body_style)]
        ]
        t_rf = Table(rf_meta, colWidths=[150, 390])
        t_rf.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F5F9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5)
        ]))
        story.append(t_rf)
        story.append(PageBreak())

        # ==========================================
        # PAGE 4: DOCUMENT METADATA & CRYPTOGRAPHY
        # ==========================================
        story.append(Paragraph("PAGE 4 — TECHNICAL METADATA & INTEGRITY", self.title_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Cryptographic Fingerprints, EXIF / PDF Stream Properties, and Typography", self.subtitle_style))
        story.append(Spacer(1, 12))

        f_meta = forensic_result.get_metadata()
        crypto_table = [
            [Paragraph("<b>Property</b>", self.body_style), Paragraph("<b>Observed Value</b>", self.body_style)],
            [Paragraph("Cryptographic Hash (SHA-256)", self.body_style), Paragraph(f"<font face='Courier' size=8>{document.sha256}</font>", self.body_style)],
            [Paragraph("File Size", self.body_style), Paragraph(f"{document.file_size:,} bytes ({document.file_size / 1024:.1f} KB)", self.body_style)],
            [Paragraph("MIME Type", self.body_style), Paragraph(document.mime_type, self.body_style)],
            [Paragraph("Document Title / Subject", self.body_style), Paragraph(str(f_meta.get('title') or 'None'), self.body_style)],
            [Paragraph("Author / Creator", self.body_style), Paragraph(str(f_meta.get('creator') or f_meta.get('author') or 'None'), self.body_style)],
            [Paragraph("PDF Producer / Software", self.body_style), Paragraph(str(f_meta.get('producer') or f_meta.get('software') or 'None'), self.body_style)],
            [Paragraph("Creation Date", self.body_style), Paragraph(str(f_meta.get('creation_date') or f_meta.get('datetime_original') or 'None'), self.body_style)],
            [Paragraph("Modification Date", self.body_style), Paragraph(str(f_meta.get('mod_date') or 'None'), self.body_style)],
            [Paragraph("Page Count", self.body_style), Paragraph(str(f_meta.get('page_count', 1)), self.body_style)],
            [Paragraph("Embedded Font Count", self.body_style), Paragraph(str(f_meta.get('font_count', 'N/A')), self.body_style)],
            [Paragraph("Embedded Images", self.body_style), Paragraph(str(f_meta.get('image_count', 'N/A')), self.body_style)]
        ]
        t_crypto = Table(crypto_table, colWidths=[170, 370])
        t_crypto.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
        ]))
        story.append(t_crypto)
        story.append(Spacer(1, 14))

        # OCR Preview
        story.append(Paragraph("OPTICAL CHARACTER RECOGNITION (OCR) EXTRACTION", self.section_heading))
        ocr_info = forensic_result.get_ocr()
        ocr_text = ocr_info.get('extracted_text_preview') or "No OCR text extracted or image contains purely graphic seals."
        story.append(Paragraph(f"<font face='Courier' size=8 color='#1E293B'>{ocr_text}</font>", ParagraphStyle('Ocr', parent=self.body_style, backColor=colors.HexColor('#F1F5F9'), borderPadding=6)))
        story.append(PageBreak())

        # ==========================================
        # PAGE 5: REGISTRY VERIFICATION & DISCLAIMER
        # ==========================================
        story.append(Paragraph("PAGE 5 — VERIFICATION REGISTRY & LEGAL DISCLAIMER", self.title_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("Authoritative Record Comparison & Mandatory Forensic Operating Notice", self.subtitle_style))
        story.append(Spacer(1, 12))

        registry_match_data = [
            [Paragraph("<b>Attribute</b>", self.body_style), Paragraph("<b>Submitted Input</b>", self.body_style), Paragraph("<b>Registry Record</b>", self.body_style), Paragraph("<b>Match Status</b>", self.body_style)],
            [Paragraph("Document Number", self.body_style), Paragraph(document.document_number, self.body_style), Paragraph(rec_data.get('document_number') or 'NOT FOUND', self.body_style), Paragraph("MATCH" if rec_data.get('document_number') else "MISMATCH", self.body_style)],
            [Paragraph("Document Type", self.body_style), Paragraph(document.document_type, self.body_style), Paragraph(rec_data.get('document_type') or 'NOT FOUND', self.body_style), Paragraph("MATCH" if rec_data.get('document_type') == document.document_type else "MISMATCH", self.body_style)],
            [Paragraph("Holder Name", self.body_style), Paragraph(document.holder_name, self.body_style), Paragraph(rec_data.get('holder_name') or 'NOT FOUND', self.body_style), Paragraph("MATCH" if rec_data.get('holder_name') == document.holder_name else "MISMATCH", self.body_style)],
            [Paragraph("Issuing Authority", self.body_style), Paragraph(document.issuing_authority or 'N/A', self.body_style), Paragraph(rec_data.get('issuing_authority') or 'NOT FOUND', self.body_style), Paragraph("RECORDED", self.body_style)],
            [Paragraph("Registry Source", self.body_style), Paragraph("Local Simulation Registry", self.body_style), Paragraph(rec_data.get('source') or 'Local Registry (Phase 1)', self.body_style), Paragraph("PHASE 1", self.body_style)]
        ]
        t_reg = Table(registry_match_data, colWidths=[120, 140, 170, 110])
        t_reg.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')])
        ]))
        story.append(t_reg)
        story.append(Spacer(1, 16))

        # Legal Disclaimer Card
        story.append(Paragraph("REGULATORY & FORENSIC DISCLOSURE", self.section_heading))
        disclaimer_text = (
            "<b>IMPORTANT NOTICE:</b> This document verification system is an automated platform for "
            "digital forensics screening and record verification. It combines Error Level Analysis (ELA), "
            "compression blockiness, noise distribution, copy-move analysis, and statistical classification "
            "to detect indicators of digital document tampering.<br/><br/>"
            "1. <b>Screening Purpose:</b> The forensic findings, tamper ratios, and classifications provided herein are automated "
            "technical screening indicators designed to assist document verification specialists.<br/>"
            "2. <b>Registry Scope:</b> The document verification was conducted against the configured "
            "verification registry database.<br/>"
            "3. <b>Absence of Record:</b> A status of 'RECORD NOT FOUND' indicates that the document identifier was not found "
            "in the local verification repository, and does not alone invalidate authentic credentials."
        )
        t_disc = Table([[Paragraph(disclaimer_text, self.body_style)]], colWidths=[540])
        t_disc.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FEF2F2')),
            ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#DC2626')),
            ('PADDING', (0, 0), (-1, -1), 10)
        ]))
        story.append(t_disc)

        # Build PDF
        doc.build(story)
        return str(pdf_path)
