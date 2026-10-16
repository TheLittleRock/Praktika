import os
import time
import json
from starlette.testclient import TestClient
from app.main import app
from app.database import init_db, get_db

client = TestClient(app)

def test_autodetect_sample_pdfs():
    # Login as admin
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_resp.status_code == 200

    sample_files = [
        ("06 Kalorimetria_matuskovicova.pdf", "Matuškovičová", 6),
        ("6_chovancova_ema.pdf", "Chovancová", 6),
        ("FPRA1_1_Boczek.pdf", "Boczek", 1),
        ("FPRA1_Boril_uloha1_opravene.pdf", "Bořil", 1)
    ]

    for fname, expected_surname, expected_task_num in sample_files:
        if not os.path.exists(fname):
            continue
        with open(fname, "rb") as f:
            resp = client.post("/api/protocols/autodetect", files={"file": (fname, f, "application/pdf")})
        assert resp.status_code == 200, f"Autodetect failed for {fname}: {resp.text}"
        data = resp.json()
        assert expected_surname.lower() in data["student_name"].lower(), f"Expected surname {expected_surname} in {data['student_name']}"
        assert data["measurement_number"] == expected_task_num, f"Expected task {expected_task_num}, got {data['measurement_number']}"
        assert data["course_code"] in ["FPRA1", "FPRA2", "ZFM2"]

def test_slot_course_code_and_permissions():
    # Admin login
    login_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200

    # Create assistant user for testing
    u_name = f"asist_test_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Test Asistent",
        "password": "heslo123",
        "role": "assistant"
    })
    assert u_resp.status_code == 200
    u_id = u_resp.json()["id"]

    # Get active semester
    sem_resp = client.get("/api/semesters")
    semesters = sem_resp.json()
    active_sem = next((s for s in semesters if s["is_active"]), semesters[0])

    # Admin creates slot with course_code
    create_resp = client.post("/api/slots", json={
        "semester_id": active_sem["id"],
        "course_code": "FPRA2",
        "day_of_week": "Středa",
        "time_start": "14:00",
        "time_end": "17:00",
        "name": "Skupina C",
        "room": "F1"
    })
    assert create_resp.status_code == 200
    slot_data = create_resp.json()
    slot_id = slot_data["id"]
    assert slot_data["course_code"] == "FPRA2"

    # Admin updates slot
    update_resp = client.put(f"/api/slots/{slot_id}", json={
        "course_code": "ZFM2",
        "name": "Skupina C (Aktualizováno)",
        "room": "F2"
    })
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["course_code"] == "ZFM2"
    assert updated_data["room"] == "F2"

    # Logout and login as assistant
    client.post("/api/auth/logout")
    ass_login = client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    assert ass_login.status_code == 200

    # Assistant attempts to create slot -> 403
    ass_create = client.post("/api/slots", json={
        "semester_id": active_sem["id"],
        "course_code": "FPRA1",
        "day_of_week": "Pondělí",
        "time_start": "08:00",
        "time_end": "11:00",
        "name": "Nepovolený slot"
    })
    assert ass_create.status_code == 403

    # Assistant attempts to update slot -> 403
    ass_put = client.put(f"/api/slots/{slot_id}", json={"room": "F3"})
    assert ass_put.status_code == 403

    # Assistant attempts to delete slot -> 403
    ass_del = client.delete(f"/api/slots/{slot_id}")
    assert ass_del.status_code == 403

    # Cleanup as admin
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_del = client.delete(f"/api/slots/{slot_id}")
    assert admin_del.status_code == 200
    client.delete(f"/api/users/{u_id}")

def test_measurement_crud_permissions():
    # Admin creates assistant
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    u_name = f"asist_meas_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Test Asistent",
        "password": "heslo123",
        "role": "assistant"
    })
    u_id = u_resp.json()["id"]

    # Logout and login as assistant
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})

    # Assistant attempts to create task -> 403
    ass_task = client.post("/api/measurements", json={
        "code": "99",
        "number": 99,
        "name": "Testovací úloha",
        "semester_type": "ZS",
        "course_code": "FPRA1"
    })
    assert ass_task.status_code == 403

    # Login as admin
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_task = client.post("/api/measurements", json={
        "code": "99",
        "number": 99,
        "name": "Testovací úloha",
        "semester_type": "ZS",
        "course_code": "FPRA1"
    })
    assert adm_task.status_code == 200
    task_id = adm_task.json()["id"]

    # Assistant attempts to delete task -> 403
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    ass_del_task = client.delete(f"/api/measurements/{task_id}")
    assert ass_del_task.status_code == 403

    # Admin cleans up
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    adm_del_task = client.delete(f"/api/measurements/{task_id}")
    assert adm_del_task.status_code == 200
    client.delete(f"/api/users/{u_id}")

def test_assistant_protocol_assignment_and_delete_protection():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_user = client.get("/api/auth/me").json()

    u_name = f"asist_proto_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Test Asistent",
        "password": "heslo123",
        "role": "assistant"
    })
    asistent_user = u_resp.json()

    # Get sample protocol
    protos = client.get("/api/protocols").json()
    if not protos:
        return
    proto_id = protos[0]["id"]

    # Assign to admin
    client.put(f"/api/protocols/{proto_id}/assign", json={"evaluator_id": admin_user["id"]})

    # Login as assistant
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})

    # Assistant tries to delete protocol owned by admin -> 403
    del_resp = client.delete(f"/api/protocols/{proto_id}")
    assert del_resp.status_code == 403

    # Assistant tries to reassign admin's protocol -> 403
    reassign_resp = client.put(f"/api/protocols/{proto_id}/assign", json={"evaluator_id": asistent_user["id"]})
    assert reassign_resp.status_code == 403

    # Admin unassigns it
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    client.put(f"/api/protocols/{proto_id}/assign", json={"evaluator_id": None})

    # Now assistant can claim unassigned protocol
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    claim_resp = client.put(f"/api/protocols/{proto_id}/assign", json={"evaluator_id": asistent_user["id"]})
    assert claim_resp.status_code == 200

    # And assistant can unassign their own protocol
    unclaim_resp = client.put(f"/api/protocols/{proto_id}/assign", json={"evaluator_id": None})
    assert unclaim_resp.status_code == 200

    # Cleanup user
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    client.delete(f"/api/users/{asistent_user['id']}")

def test_personal_gemini_api_key():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    u_name = f"asist_key_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Test Key Asistent",
        "password": "heslo123",
        "role": "assistant"
    })
    u_id = u_resp.json()["id"]

    # Login as assistant
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})

    # Set personal API key
    test_key = "AIzaSyPersonalAssistantKey12345"
    save_resp = client.post("/api/settings/ai", json={"gemini_api_key": test_key})
    assert save_resp.status_code == 200

    # Check key is returned
    get_resp = client.get("/api/settings/ai")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["has_key"] is True
    assert data["gemini_api_key"] == test_key

    # Admin key is unaffected
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    admin_get = client.get("/api/settings/ai")
    assert admin_get.status_code == 200
    if admin_get.json().get("gemini_api_key"):
        assert admin_get.json()["gemini_api_key"] != test_key

    client.delete(f"/api/users/{u_id}")

if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj)]
    print(f"Running {len(tests)} v2.5 feature tests...")
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"  ✗ {t.__name__} FAILED: {e}")
            import traceback
            traceback.print_exc()
            exit(1)
    print(f"\nALL {passed}/{len(tests)} TESTS PASSED SUCCESSFULLY!")

