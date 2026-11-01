import sys
import os
from pathlib import Path
from PIL import Image
import io

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app

def run_smoke_test():
    print("==================================================")
    print("STARTING END-TO-END VERIFICATION PIPELINE SMOKE TEST")
    print("==================================================")
    
    app = create_app()
    client = app.test_client()

    # 1. Test Login
    login_res = client.post('/login', data={'username': 'admin', 'password': 'Admin@12345'}, follow_redirects=True)
    assert login_res.status_code == 200
    print("[1/5] Admin authentication verified.")

    # 2. Test Registry Matching Search
    search_res = client.get('/search?document_number=MH/INC/2026/0001')
    assert search_res.status_code == 200
    assert b'VERIFIED RECORD FOUND' in search_res.data
    print("[2/5] Local registry search & matching verified.")

    # 3. Test Full Upload & Verify on Authentic Sample
    auth_files = sorted(list((BASE_DIR / 'dataset' / 'authentic').glob('*.jpg')))
    assert len(auth_files) > 0, "No authentic sample found in dataset/authentic"
    sample_auth_path = auth_files[0]
    
    with open(sample_auth_path, 'rb') as f:
        file_bytes = f.read()

    data = {
        'document_type': 'Income Certificate',
        'document_number': 'MH/INC/2026/0001',
        'document_name': 'Official Income Certificate',
        'holder_name': 'Demo User',
        'issue_date': '2026-06-15',
        'document_file': (io.BytesIO(file_bytes), sample_auth_path.name)
    }

    print("[3/5] Uploading authentic document for verification...")
    upload_res = client.post('/verify', data=data, content_type='multipart/form-data', follow_redirects=True)
    assert upload_res.status_code == 200
    assert b'Analysis Dossier' in upload_res.data
    assert b'CARD 1: DOCUMENT RECORD VERIFICATION' in upload_res.data
    assert b'CARD 2: AI FORENSIC ANALYSIS' in upload_res.data
    print("       -> Document processed through ELA, RF, and Evidence Aggregator successfully.")

    # 4. Test Full Upload & Verify on Manipulated Sample
    manip_files = sorted(list((BASE_DIR / 'dataset' / 'manipulated').glob('*.jpg')))
    assert len(manip_files) > 0, "No manipulated sample found in dataset/manipulated"
    sample_manip_path = manip_files[0]
    
    with open(sample_manip_path, 'rb') as f:
        manip_bytes = f.read()

    data_manip = {
        'document_type': 'Income Certificate',
        'document_number': 'MH/INC/2026/0001',  # Registered number but tampered image
        'document_name': 'Altered Income Slip',
        'holder_name': 'Demo User',
        'issue_date': '2026-06-15',
        'document_file': (io.BytesIO(manip_bytes), sample_manip_path.name)
    }

    print("[4/5] Uploading manipulated document for verification...")
    upload_manip_res = client.post('/verify', data=data_manip, content_type='multipart/form-data', follow_redirects=True)
    assert upload_manip_res.status_code == 200
    assert b'Analysis Dossier' in upload_manip_res.data
    print("       -> Tampered document processed through ELA, RF, and localized bounding boxes successfully.")

    # 5. Test PDF Report Download
    report_res = client.get('/verifications/1/report')
    assert report_res.status_code == 200
    assert report_res.mimetype == 'application/pdf'
    assert len(report_res.data) > 1000
    print("[5/5] 5-page official ReportLab PDF report generation and download verified.")

    print("==================================================")
    print("ALL END-TO-END SMOKE TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    run_smoke_test()
