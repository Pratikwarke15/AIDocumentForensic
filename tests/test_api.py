import json

def test_api_login(client):
    res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'Admin@12345'})
    assert res.status_code == 200
    data = res.get_json()
    assert data['message'] == 'Login successful'
    assert data['user']['role'] == 'admin'

def test_api_search_documents(client):
    res = client.get('/api/documents/search?document_number=MH/INC/2026/0001')
    assert res.status_code == 200
    data = res.get_json()
    assert data['registry']['matched'] is True
    assert data['registry']['status'] == 'VERIFIED'

def test_api_registry_records(client):
    res = client.get('/api/registry/records')
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_api_admin_stats(client):
    res = client.get('/api/admin/dashboard')
    assert res.status_code == 200
    data = res.get_json()
    assert 'total_verifications' in data
    assert 'authentic' in data
