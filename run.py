import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    print("=" * 60)
    print("GOVERNMENT DOCUMENT VERIFICATION & FORENSICS SYSTEM")
    print("=" * 60)
    print(f"Server Running At:  http://{host}:{port}")
    print("Default Admin:      admin / Admin@12345")
    print("Default User:       demo / Demo@12345")
    print("Phase 1 Source:     /verification_records/ (Local Registry)")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=False)
