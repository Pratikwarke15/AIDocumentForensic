# AI Forensics – Government Document Verification System

**Academic Title:** *AI Forensics – Documents Verification System: Detection and Localization of Potentially Manipulated Documents Using Error Level Analysis and Random Forest*

A production-grade, locally deployable web application and digital forensics platform for authenticating government-issued documents, detecting spliced typography, localized tamper patches, forged seals, and compression discrepancies.

---

## 1. Architectural Overview & Two-Layer Verification

The platform enforces strict separation of concerns between authoritative record existence and pixel-level forensic integrity:

`
+----------------------------------------------------------------------------------------------------+
|                                    DOCUMENT VERIFICATION SYSTEM                                    |
|                                                                                                    |
|            LAYER A: RECORD VERIFICATION                  LAYER B: AI FORENSIC ANALYSIS             |
|                                                                                                    |
|    VerificationProvider                                  1. File Validation (Magic Bytes)          |
|         |                                                2. SHA-256 Preservation                   |
|         +-- LocalRegistryProvider (Phase 1 Active)       3. PDF-Native Structural Forensics        |
|         |   (JSON Folder + DB Synchronization Cache)     4. High-Res Page Rasterization            |
|         |                                                5. Error Level Analysis (ELA Q95)         |
|         +-- FutureGovernmentAPIProvider (Stub)           6. Tamper Mask & Bounding Box Overlays    |
|             (DigiLocker / API Setu Interface)            7. 28+ Numerical Feature Extraction       |
|                                                          8. Trained Random Forest Classifier       |
|    Statuses:                                             9. Multi-Signal Corroboration Engine      |
|     - VERIFIED                                                                                     |
|     - RECORD NOT FOUND                                   Statuses:                                 |
|     - NOT CHECKED                                         - AUTHENTIC                              |
|                                                           - POTENTIALLY MANIPULATED                |
|                                                           - INCONCLUSIVE                           |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
                               +------------------------------------+
                               |    EVIDENCE AGGREGATION ENGINE     |
                               |  Combines Layer A + Layer B Signal |
                               |  Calculates Calibrated Confidence  |
                               +------------------+-----------------+
                                                  |
                         +------------------------+------------------------+
                         |                                                 |
                         v                                                 v
           +---------------------------+                     +---------------------------+
           |    WEB RESULT DASHBOARD   |                     |   5-PAGE PDF REPORT LAB   |
           | Heatmaps, Masks, Features |                     | Official Forensic Dossier |
           | & Audit Metadata Tabs     |                     | With Disclaimers          |
           +---------------------------+                     +---------------------------+
`

### Core Verification Metrics (Decoupled Architecture)

The system clearly distinguishes between **Layer A Authoritative Registry Matching** and **Layer B Statistical AI Forensics**:

1. **Original Document Match (Layer A - Local Registry)**:
   - Evaluates cryptographic hash and metadata correspondence against official reference copies in the registry.
   - Outputs **`100.0%`** when the document record and content match exactly.
   - Outputs **`0.0%`** on hash mismatch or conflicting holder identity.
   - Outputs **`N/A`** when unrecorded in the local registry (clearly stating that registry absence is neutral to forensic authenticity).

2. **Authenticity Confidence (Layer B - AI Forensics)**:
   - A calibrated probabilistic score (80.0% to 98.0% for authentic documents, 55.0% to 74.0% for review required) derived from cross-domain consensus across 6 independent domains (ELA, noise disparity, compression grid, copy-move clustering, metadata, and Random Forest).
   - Statistical models do not report an artificial 100% confidence without an exact reference file, reflecting normal physical variations (scanner optics, camera sensor noise, and benign JPEG recompression).

3. **Manipulation Risk Score**:
   - Continuous weighted composite anomaly score from 0.0% to 100.0%, eliminating artificial step jumps.

4. **Suspicious Region Area**:
   - Exact percentage of localized anomalous pixel area identified via morphological component analysis.

### Combined Assessment Outcomes:
- `VERIFIED RECORD & FORENSICALLY CONSISTENT`
- `VERIFIED RECORD BUT POSSIBLE DIGITAL MANIPULATION`
- `RECORD UNVERIFIED (LOCAL REGISTRY) — FORENSICALLY CONSISTENT`
- `RECORD UNVERIFIED (LOCAL REGISTRY) — POTENTIAL DIGITAL TAMPERING DETECTED`
- `REGISTRY DATA MISMATCH & POTENTIAL DIGITAL TAMPERING`
- `RECORD UNVERIFIED (LOCAL REGISTRY) — FORENSIC REVIEW REQUIRED`

---

## 2. Forensic Computer Vision Pipeline

1. **Cryptographic Preservation**: File is validated using magic bytes (JPEG \xFF\xD8\xFF, PNG \x89PNG\r\n\x1a\n, PDF %PDF-), and hashed via SHA-256 before any transformation. The original file is stored immutably.
2. **Dual-Path PDF Processing**:
   - **Path A (PDF-Native Forensics)**: Inspects xref objects, creation and modification timestamps, fonts, embedded image streams, and flags suspicious PDF editing producers (e.g., Photoshop, Canva, Illustrator, PDFtk).
   - **Path B (Page Raster Forensics)**: Renders Page 1 at high resolution (200 DPI via PyMuPDF) and normalizes dimensions (max 800x800) for standardized computer vision.
3. **Error Level Analysis (ELA)**:
   - Resaves the analysis image at quality factor  = 95$.
   - Calculates absolute difference $\Delta = |I_0 - I_{95}|$.
   - Amplifies differences by scale factor  = 15.0$.
   - Maps to Jet colormap (Blue = consistent compression, Red/Yellow = elevated anomaly).
   - Generates binary tamper mask via thresholding and morphological opening/closing.
   - Computes connected components to localize suspicious regions with red bounding box overlays.
4. **Multi-Signal Supporting Forensics**:
   - **Noise Inconsistency**: High-pass Laplacian noise residuals evaluated across an 8x8 grid of cells. Disparity between maximum and median cell variance flags spliced elements.
   - **JPEG Blockiness & DCT**: Evaluates 8x8 grid boundary discontinuities and high-frequency Discrete Cosine Transform energy distribution.
   - **ORB Copy-Move Detection**: Keypoint matching with spatial clustering to detect cloned seals, stamps, or duplicated numbers.
   - **Sharpness Consistency**: Local Laplacian focus variance across image patches.
   - **OCR & Typography Layout**: Evaluates word bounding boxes, baseline coordinate alignment variance, and word confidence disparity via Tesseract (with graceful morphological contour fallback).
5. **Random Forest Classifier**:
   - Consumes the ordered 31-dimensional numerical feature vector.
   - Outputs calibrated class probability (\text{Manipulated})$.
   - Saved as models/random_forest.joblib with companion models/feature_schema.json and models/model_metadata.json.

---

## 3. Local Verification Registry (Phase 1 Source of Truth)

Phase 1 operates an authoritative local file-system repository in:
`
verification_records/
├── aadhaar/
├── pan/
├── marksheets/
├── certificates/
├── caste_certificates/
├── income_certificates/
├── domicile_certificates/
├── driving_licence/
├── other/
└── README.md
`

Each record is a standard human-editable JSON document:
`json
{
    "record_id": "CERT-2026-0001",
    "document_type": "Income Certificate",
    "document_number": "MH/INC/2026/0001",
    "document_name": "Annual Income Certificate",
    "holder_name": "Demo User",
    "issue_date": "2026-06-15",
    "issuing_authority": "Revenue Department, Govt of Maharashtra",
    "status": "VERIFIED",
    "reference_file": "CERT-2026-0001.pdf"
}
`

### Folder Synchronization:
- The database acts as an indexed cache.
- Admins can edit, add, or remove JSON files directly on disk.
- Clicking **"SYNC FOLDER"** in the Admin Registry UI scans all JSON files, updates the database cache, and deactivates any removed records.

---

## 4. Default Demo Credentials

| Role | Username | Password | Email | Access |
|------|----------|----------|-------|--------|
| **Admin** | dmin | Admin@12345 | dmin@forensics.gov.local | Full Access (Registry CRUD, Model Management, Audit Logs, User Mgmt) |
| **Standard User** | demo | Demo@12345 | demo@forensics.local | Upload & Verify, Search Registry, Personal History |

---

## 5. Installation & Setup

### Prerequisites:
- Python 3.9+ (Tested on Python 3.9.5 Windows 64-bit)
- Tesseract OCR (Optional: if not on PATH, system uses automatic morphological layout fallback)

### Step 1: Install Dependencies
`powershell
pip install -r requirements.txt
`

### Step 2: Initialize Dataset & Train Machine Learning Model
`powershell
# 1. Generate synthetic authentic and manipulated document dataset
python scripts/prepare_dataset.py

# 2. Extract 28+ numerical features and train Random Forest model
python scripts/train_model.py

# 3. View model evaluation metrics
python scripts/evaluate_model.py
`

### Step 3: Run Automated Test Suites
```powershell
# 1. Run all 23 unit and integration tests
pytest tests/ -v

# 2. Run the 7-Condition Document Robustness Test Suite (HQ, Scanned, JPEG Q70, Photo, Stamp/QR, Spliced, Cloned)
python scripts/test_document_conditions.py

# 3. Run Unseen Held-Out Test Split Evaluation (18 unseen government documents)
python scripts/test_unseen_holdout.py
```

### Step 4: Run End-to-End Smoke Pipeline Test
```powershell
python scripts/test_pipeline.py
```

### Step 5: Launch Web Application
```powershell
python run.py
```
Open your web browser at: http://127.0.0.1:5000

---

## 6. REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/login | Authenticate API client with username and password |
| GET | /api/documents/search?document_number= | Search registry records and verification history |
| GET | /api/verifications/<id> | Retrieve full forensic verdict, features, and signals JSON |
| GET | /api/registry/records | List all active local registry records |
| POST | /api/registry/records | Programmatically add/update a registry record |
| POST | /api/registry/sync | Trigger folder-to-database synchronization |
| GET | /api/admin/dashboard | Retrieve platform-wide verification statistics |
| GET | /api/admin/model | Inspect active model version, metrics, and feature schema |

---

## 7. Future Government API Integration (Phase 2 Architecture)

The application implements a clean provider abstraction:
pp/verification/base.py -> VerificationProvider

In Phase 1, LocalRegistryProvider is the active provider. 
To transition to Phase 2, implement GovernmentVerificationProvider in pp/verification/future_government.py:
1. Connect X.509 client certificates or OAuth2 tokens for API Setu / DigiLocker.
2. In create_app(), set egistry_provider = GovernmentVerificationProvider(api_endpoint=...).
3. The frontend, scoring engine, audit logger, and PDF generator will continue operating without any code modifications.

---

## 8. Limitations & Disclaimers

1. **ELA Scope:** ELA is most effective on JPEG compression artifacts. PNG and scanned PDF documents are evaluated through rasterization and supporting signals (noise, blockiness, copy-move).
2. **Preliminary Screening:** Results generated by this platform are automated technical screening indicators and do not constitute legally certified testimony.
3. **Local Registry Scope:** In Phase 1, a status of RECORD NOT FOUND indicates absence from the local demonstration repository, not invalidation by a live government authority.
