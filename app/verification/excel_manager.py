import io
import os
import csv
import json
import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Standard column schemas and sample data per document category
DOCUMENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    'Aadhaar': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'dob', 'gender',
            'father_name', 'address', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'UID-2026-0001',
                'document_number': '9876 5432 1098',
                'holder_name': 'Ramesh Suresh Patil',
                'dob': '1988-06-14',
                'gender': 'Male',
                'father_name': 'Suresh Patil',
                'address': 'Plot 42, Shivaji Nagar, Pune, Maharashtra 411005',
                'issuing_authority': 'Unique Identification Authority of India (UIDAI)'
            },
            {
                'record_id': 'UID-2026-0002',
                'document_number': '5432 1098 7654',
                'holder_name': 'Pooja Anand Deshmukh',
                'dob': '1994-11-22',
                'gender': 'Female',
                'father_name': 'Anand Deshmukh',
                'address': 'Flat 204, Green Heights, Thane, Maharashtra 400601',
                'issuing_authority': 'Unique Identification Authority of India (UIDAI)'
            }
        ]
    },
    'PAN': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'father_name', 'dob',
            'pan_type', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'PAN-2026-0001',
                'document_number': 'ABCPS1234F',
                'holder_name': 'Amit Kumar Sharma',
                'father_name': 'Rajendra Sharma',
                'dob': '1990-03-15',
                'pan_type': 'Individual (P)',
                'issuing_authority': 'Income Tax Department, Government of India'
            },
            {
                'record_id': 'PAN-2026-0002',
                'document_number': 'XYZPK5678G',
                'holder_name': 'Sunita Ramesh Kulkarni',
                'father_name': 'Ramesh Kulkarni',
                'dob': '1985-08-20',
                'pan_type': 'Individual (P)',
                'issuing_authority': 'Income Tax Department, Government of India'
            }
        ]
    },
    'Driving Licence': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'dob', 'issue_date',
            'validity_date', 'vehicle_classes', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'DL-2026-0001',
                'document_number': 'MH12 20260012345',
                'holder_name': 'Vikas Ashok Shinde',
                'dob': '1992-05-10',
                'issue_date': '2026-01-15',
                'validity_date': '2046-01-14',
                'vehicle_classes': 'MCWG, LMV',
                'issuing_authority': 'Regional Transport Office, Pune (MH-12)'
            }
        ]
    },
    'Caste Certificate': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'caste_category',
            'sub_caste', 'issue_date', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'CC-2026-0001',
                'document_number': 'MRC/CC/2026/89421',
                'holder_name': 'Prashant Eknath Gaikwad',
                'caste_category': 'Scheduled Caste (SC)',
                'sub_caste': 'Mahar',
                'issue_date': '2026-02-18',
                'issuing_authority': 'Sub-Divisional Magistrate / Competent Authority, Nagpur'
            }
        ]
    },
    'Non-Creamy Layer': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'caste_category',
            'financial_year', 'valid_upto', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'NCL-2026-0001',
                'document_number': 'NCL/MH/2026/34190',
                'holder_name': 'Sachin Babanराव Jadhav',
                'caste_category': 'Other Backward Class (OBC)',
                'financial_year': '2025-2026',
                'valid_upto': '2027-03-31',
                'issuing_authority': 'Office of the Sub-Divisional Officer, Nashik'
            }
        ]
    },
    'Caste Validity': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'caste_category',
            'scrutiny_committee', 'issue_date', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'CV-2026-0001',
                'document_number': 'CVS/PUNE/2026/09214',
                'holder_name': 'Rohit Dattatray More',
                'caste_category': 'Scheduled Caste (SC)',
                'scrutiny_committee': 'District Caste Scrutiny Committee No. 1, Pune',
                'issue_date': '2026-03-05',
                'issuing_authority': 'Divisional Caste Certificate Scrutiny Committee'
            }
        ]
    },
    'Marksheet': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'seat_number',
            'examination_name', 'passing_year', 'marks_obtained', 'total_marks',
            'percentage_or_grade', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'HSC-2026-0001',
                'document_number': 'HSC-PUNE-2026-8812',
                'holder_name': 'Aniket Vijay Joshi',
                'seat_number': 'M042819',
                'examination_name': 'Higher Secondary Certificate (HSC) Science',
                'passing_year': '2026',
                'marks_obtained': '542',
                'total_marks': '600',
                'percentage_or_grade': '90.33%',
                'issuing_authority': 'Maharashtra State Board of Secondary and Higher Secondary Education, Pune'
            }
        ]
    },
    'Income Certificate': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'annual_income',
            'financial_year', 'issue_date', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'INC-2026-0001',
                'document_number': 'MH/INC/2026/0001',
                'holder_name': 'Vijay Balasaheb Patil',
                'annual_income': '1,20,000',
                'financial_year': '2025-2026',
                'issue_date': '2026-01-10',
                'issuing_authority': 'Office of the Tahsildar, Haveli, Pune'
            }
        ]
    },
    'Domicile Certificate': {
        'columns': [
            'record_id', 'document_number', 'holder_name', 'place_of_birth',
            'resident_years', 'issue_date', 'issuing_authority'
        ],
        'required': ['record_id', 'document_number', 'holder_name'],
        'sample_rows': [
            {
                'record_id': 'DOM-2026-0001',
                'document_number': 'MH/DOM/2026/0452',
                'holder_name': 'Deepak Manohar Rane',
                'place_of_birth': 'Mumbai, Maharashtra',
                'resident_years': '25 Years',
                'issue_date': '2026-01-12',
                'issuing_authority': 'Executive Magistrate, Mumbai Suburban'
            }
        ]
    }
}

# Alias mapping for flexible header detection
COLUMN_ALIASES = {
    'doc_number': 'document_number',
    'id_number': 'document_number',
    'number': 'document_number',
    'card_number': 'document_number',
    'aadhaar_number': 'document_number',
    'pan_number': 'document_number',
    'dl_number': 'document_number',
    'cert_number': 'document_number',
    'certificate_no': 'document_number',
    'name': 'holder_name',
    'full_name': 'holder_name',
    'candidate_name': 'holder_name',
    'applicant_name': 'holder_name',
    'authority': 'issuing_authority',
    'issued_by': 'issuing_authority',
    'date': 'issue_date',
    'date_of_issue': 'issue_date',
    'rec_id': 'record_id',
    'id': 'record_id'
}

def generate_excel_template(doc_type: str) -> Tuple[io.BytesIO, str]:
    """
    Generates a pre-formatted, styled Excel workbook (.xlsx) with standard column headers
    and realistic sample data rows for the specified government document category.
    """
    schema = DOCUMENT_SCHEMAS.get(doc_type)
    if not schema:
        # Fallback schema
        schema = {
            'columns': ['record_id', 'document_number', 'holder_name', 'issue_date', 'issuing_authority'],
            'sample_rows': [{
                'record_id': 'REC-2026-001',
                'document_number': 'DOC-2026-9999',
                'holder_name': 'Sample Citizen Name',
                'issue_date': '2026-01-01',
                'issuing_authority': 'Government Competent Authority'
            }]
        }

    cols = schema['columns']
    samples = schema['sample_rows']

    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"{doc_type[:25]} Records"

        # Styles
        header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
        header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
        sample_font = Font(name="Arial", size=10, italic=False, color="1E293B")
        border_thin = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        # Write Header Row
        for col_idx, col_name in enumerate(cols, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = border_thin
        ws.row_dimensions[1].height = 28

        # Write Sample Data Rows
        for row_idx, row_data in enumerate(samples, start=2):
            for col_idx, col_name in enumerate(cols, start=1):
                val = row_data.get(col_name, '')
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = sample_font
                cell.border = border_thin
                cell.alignment = Alignment(vertical="center")
            ws.row_dimensions[row_idx].height = 20

        # Auto-adjust column widths
        for col_idx, col_name in enumerate(cols, start=1):
            max_len = max(len(col_name), 12)
            for row_data in samples:
                max_len = max(max_len, len(str(row_data.get(col_name, ''))))
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max_len + 4

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        filename = f"{doc_type.replace(' ', '_')}_Template.xlsx"
        return output, filename

    except ImportError:
        # Fallback to CSV format if openpyxl is not installed
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=cols)
        writer.writeheader()
        for row in samples:
            writer.writerow(row)
        
        b_output = io.BytesIO(output.getvalue().encode('utf-8'))
        filename = f"{doc_type.replace(' ', '_')}_Template.csv"
        return b_output, filename


def parse_uploaded_records(file_bytes: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parses uploaded .xlsx, .xls, or .csv files into a list of normalized row dictionaries.
    """
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    records = []

    if ext in ('xlsx', 'xls'):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                return []
            
            headers = [str(h).strip().lower().replace(' ', '_') if h is not None else '' for h in rows[0]]
            for r in rows[1:]:
                if not any(r):
                    continue
                row_dict = {}
                for idx, val in enumerate(r):
                    if idx < len(headers) and headers[idx]:
                        val_str = str(val).strip() if val is not None else ''
                        if val_str.endswith('.0') and headers[idx] in ('document_number', 'record_id', 'seat_number'):
                            val_str = val_str[:-2]
                        row_dict[headers[idx]] = val_str
                records.append(row_dict)
            return records
        except Exception:
            # Fallback to pandas
            try:
                import pandas as pd
                df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
                df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
                return df.fillna('').to_dict(orient='records')
            except Exception as e:
                raise ValueError(f"Failed to parse Excel file: {str(e)}")

    elif ext == 'csv':
        try:
            text = file_bytes.decode('utf-8-sig', errors='replace')
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                cleaned = {k.strip().lower().replace(' ', '_'): str(v).strip() for k, v in row.items() if k}
                records.append(cleaned)
            return records
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

    else:
        raise ValueError(f"Unsupported file format '.{ext}'. Please upload an .xlsx, .xls, or .csv file.")


def import_records_to_registry(
    file_bytes: bytes,
    filename: str,
    doc_type: str,
    session_factory,
    registry_provider
) -> Dict[str, Any]:
    """
    Parses and synchronizes records from an uploaded Excel or CSV file into the database
    and underlying filesystem registry (/verification_records/).
    """
    from app.models import VerificationRecord

    raw_records = parse_uploaded_records(file_bytes, filename)
    if not raw_records:
        return {'added': 0, 'updated': 0, 'errors': ['File is empty or contains no valid rows.']}

    session = session_factory()
    stats = {'added': 0, 'updated': 0, 'errors': []}

    try:
        for idx, row in enumerate(raw_records, start=2):
            # Normalize column aliases
            norm_row = {}
            for k, v in row.items():
                canonical = COLUMN_ALIASES.get(k, k)
                norm_row[canonical] = v

            doc_number = norm_row.get('document_number', '').strip()
            holder_name = norm_row.get('holder_name', '').strip()
            record_id = norm_row.get('record_id', '').strip()

            if not doc_number:
                stats['errors'].append(f"Row {idx}: Missing document_number (skipped)")
                continue
            if not holder_name:
                stats['errors'].append(f"Row {idx}: Missing holder_name (skipped)")
                continue

            if not record_id:
                # Generate clean record_id from doc_type and doc_number
                clean_num = ''.join(c for c in doc_number if c.isalnum())[-6:]
                record_id = f"{doc_type[:4].upper()}-{clean_num}"

            issuing_auth = norm_row.get('issuing_authority', '').strip() or f"Government Authority of {doc_type}"
            issue_date_str = norm_row.get('issue_date') or norm_row.get('dob') or None
            issue_date_val = None
            if issue_date_str:
                for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
                    try:
                        issue_date_val = datetime.datetime.strptime(issue_date_str.strip()[:10], fmt).date()
                        break
                    except ValueError:
                        pass

            # Prepare filesystem registry data
            json_data = {
                'record_id': record_id,
                'document_type': doc_type,
                'document_number': doc_number,
                'document_name': norm_row.get('document_name') or f"Official {doc_type}",
                'holder_name': holder_name,
                'issue_date': issue_date_val.strftime('%Y-%m-%d') if issue_date_val else None,
                'issuing_authority': issuing_auth,
                'status': 'VERIFIED',
                'extra_fields': {k: v for k, v in norm_row.items() if k not in (
                    'record_id', 'document_type', 'document_number', 'holder_name', 'issue_date', 'issuing_authority'
                )}
            }

            # Upsert into DB
            existing = session.query(VerificationRecord).filter_by(document_number=doc_number, document_type=doc_type).first()
            if not existing:
                existing = session.query(VerificationRecord).filter_by(record_id=record_id).first()

            if existing:
                existing.holder_name = holder_name
                existing.document_type = doc_type
                existing.document_number = doc_number
                existing.issuing_authority = issuing_auth
                existing.issue_date = issue_date_val
                existing.is_active = True
                existing.last_synced_at = datetime.datetime.utcnow()
                stats['updated'] += 1
            else:
                new_rec = VerificationRecord(
                    record_id=record_id,
                    document_type=doc_type,
                    document_number=doc_number,
                    document_name=json_data['document_name'],
                    holder_name=holder_name,
                    issue_date=issue_date_val,
                    issuing_authority=issuing_auth,
                    status='VERIFIED',
                    source_file_path=f"excel_import/{filename}",
                    is_active=True,
                    last_synced_at=datetime.datetime.utcnow()
                )
                session.add(new_rec)
                stats['added'] += 1

            # Sync to local /verification_records/ filesystem
            if registry_provider:
                try:
                    registry_provider.add_or_update_record(json_data)
                except Exception:
                    pass

        session.commit()
    except Exception as e:
        session.rollback()
        stats['errors'].append(f"Database transaction error: {str(e)}")
    finally:
        session.close()

    return stats
