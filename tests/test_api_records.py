import io

from PIL import Image


def test_password_change_invalidates_existing_token(client, auth_headers):
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "correct horse battery staple",
            "new_password": "another strong password 456",
        },
    )
    assert changed.status_code == 204, changed.text
    assert client.get("/api/v1/auth/me", headers=auth_headers).status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "another strong password 456"},
    )
    assert login.status_code == 200


def test_duplicate_guards_lookup_dashboard_and_pdf(client, auth_headers, record_payload):
    created = client.post("/api/v1/records", headers=auth_headers, json=record_payload)
    assert created.status_code == 201, created.text
    assert created.json()["household"]["household_uid"] == "B-00001"

    duplicate_household = {**record_payload, "household_uid": " b 00001 ", "serial_number": "NEW-2"}
    response = client.post("/api/v1/records", headers=auth_headers, json=duplicate_household)
    assert response.status_code == 409
    assert "Household ID already exists" in response.json()["detail"]

    duplicate_stove = {**record_payload, "household_uid": "B-00002", "serial_number": "ps_ug_m0001"}
    response = client.post("/api/v1/records", headers=auth_headers, json=duplicate_stove)
    assert response.status_code == 409
    assert "Stove serial number already exists" in response.json()["detail"]

    found = client.get("/api/v1/records/b00001", headers=auth_headers)
    assert found.status_code == 200
    assert found.json()["stove"]["serial_number"] == "PS-UG-M0001"

    summary = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert summary.status_code == 200
    assert summary.json()["total_distributions"] == 1

    pdf = client.get("/api/v1/records/B-00001/form.pdf", headers=auth_headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF-")
    assert len(pdf.content) > 3000

    export = client.get("/api/v1/records/export.csv", headers=auth_headers)
    assert export.status_code == 200, export.text
    assert "B-00001" in export.text


def test_stakeholder_cannot_access_personal_records(client, auth_headers, record_payload):
    created = client.post("/api/v1/records", headers=auth_headers, json=record_payload)
    assert created.status_code == 201
    new_user = client.post(
        "/api/v1/admin/users",
        headers=auth_headers,
        json={
            "username": "stakeholder",
            "full_name": "Project Stakeholder",
            "password": "stakeholder secure password 123",
            "role": "stakeholder",
        },
    )
    assert new_user.status_code == 201, new_user.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "stakeholder", "password": "stakeholder secure password 123"},
    )
    token = login.json()["access_token"]
    stakeholder_headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/dashboard/summary", headers=stakeholder_headers).status_code == 200
    assert client.get("/api/v1/records/B-00001", headers=stakeholder_headers).status_code == 403


def test_signature_photo_is_hashed_and_status_changes(client, auth_headers, record_payload):
    response = client.post("/api/v1/records", headers=auth_headers, json=record_payload)
    assert response.status_code == 201
    image = Image.new("RGB", (120, 80), "white")
    raw = io.BytesIO()
    image.save(raw, format="JPEG")
    raw.seek(0)
    captured = client.post(
        "/api/v1/signatures/B-00001",
        headers=auth_headers,
        files={"evidence": ("signed.jpg", raw.getvalue(), "image/jpeg")},
        data={
            "beneficiary_name": "Sample Household",
            "witness_name": "Field Officer",
            "signed_at": "2026-09-01T12:30:00+03:00",
            "notes": "Signed at the distribution point",
        },
    )
    assert captured.status_code == 201, captured.text
    body = captured.json()
    assert body["signature_status"] == "captured"
    assert len(body["signature_evidence"]) == 1
    assert len(body["signature_evidence"][0]["sha256"]) == 64
