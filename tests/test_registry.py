import json
from app.verification.local_registry import LocalRegistryProvider

def test_local_registry_matching(app):
    provider = app.registry_provider
    # Should match demo record CERT-2026-0001
    res = provider.verify_document(
        document_type="Income Certificate",
        document_number="MH/INC/2026/0001",
        holder_name="Demo User"
    )
    assert res.matched is True
    assert res.status == "VERIFIED"
    assert res.holder_name == "Demo User"
    assert "Revenue Department" in res.issuing_authority

def test_local_registry_not_found(app):
    provider = app.registry_provider
    res = provider.verify_document(
        document_type="Aadhaar",
        document_number="NON-EXISTENT-999999"
    )
    assert res.matched is False
    assert res.status == "RECORD NOT FOUND"
    assert "does not exist in the current local verification registry" in res.message

def test_local_registry_sync(app):
    provider = app.registry_provider
    stats = provider.sync_folder()
    assert 'total_active' in stats
    assert stats['total_active'] >= 1
