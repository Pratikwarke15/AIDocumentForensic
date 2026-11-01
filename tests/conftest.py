import os
import sys
import tempfile
import shutil
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from app.config import Config
from app.models import Base, User, VerificationRecord

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def auth_client(client, app):
    # Log in as demo user
    client.post('/login', data={'username': 'demo', 'password': 'Demo@12345'})
    return client

@pytest.fixture
def admin_client(client, app):
    # Log in as admin
    client.post('/login', data={'username': 'admin', 'password': 'Admin@12345'})
    return client
