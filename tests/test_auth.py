def test_user_login_success(client):
    response = client.post('/login', data={'username': 'demo', 'password': 'Demo@12345'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Verification Dashboard' in response.data or b'Welcome back' in response.data

def test_admin_login_success(client):
    response = client.post('/login', data={'username': 'admin', 'password': 'Admin@12345'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Admin Panel' in response.data or b'Welcome back' in response.data

def test_user_login_invalid_password(client):
    response = client.post('/login', data={'username': 'demo', 'password': 'WrongPassword'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username/email or password' in response.data

def test_user_registration(client):
    response = client.post('/register', data={
        'username': 'newuser',
        'email': 'newuser@test.local',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Account created successfully' in response.data

def test_rbac_admin_protected_routes(auth_client):
    # Regular user attempting admin dashboard should get 403 Forbidden
    response = auth_client.get('/admin/')
    assert response.status_code == 403

def test_admin_access_allowed(admin_client):
    response = admin_client.get('/admin/')
    assert response.status_code == 200
    assert b'Forensic Platform Analytics' in response.data
