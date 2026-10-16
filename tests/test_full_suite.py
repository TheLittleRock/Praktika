from starlette.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
import os

client = TestClient(app)

def test_health_and_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Praktika Studio" in response.text
    assert "favicon.svg" in response.text

def test_favicon():
    response = client.get("/static/favicon.svg")
    assert response.status_code == 200
    assert "svg" in response.headers["content-type"]

def test_login_and_auth_flow():
    # Login as admin
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["role"] == "admin"
    assert data["user"]["username"] == "admin"

    # Check /me
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "admin"

def test_measurements_crud():
    # List measurements
    resp = client.get("/api/measurements?semester_type=ZS")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) >= 12
    # Verify Task 1 is Vzduchová dráha
    assert tasks[0]["number"] == 1
    assert "dráh" in tasks[0]["name"].lower()

    # Add a custom measurement for LS
    new_task = {
        "code": "LS13",
        "number": 13,
        "name": "Měření modulu pružnosti",
        "semester_type": "LS"
    }
    create_resp = client.post("/api/measurements", json=new_task)
    assert create_resp.status_code == 200
    t_id = create_resp.json()["id"]

    # Rename
    put_resp = client.put(f"/api/measurements/{t_id}", json={"name": "Měření modulu pružnosti v tahu"})
    assert put_resp.status_code == 200

    # Delete
    del_resp = client.delete(f"/api/measurements/{t_id}")
    assert del_resp.status_code == 200

def test_presets_crud():
    # Get deduction presets
    resp = client.get("/api/presets?type=deduction")
    assert resp.status_code == 200
    deductions = resp.json()
    assert len(deductions) > 0

    # Add deduction preset
    new_preset = {
        "type": "deduction",
        "category": "format",
        "pts": 0.25,
        "text": "Nečitelný popisek osy"
    }
    create_resp = client.post("/api/presets", json=new_preset)
    assert create_resp.status_code == 200
    p_id = create_resp.json()["id"]

    # Delete deduction preset
    del_resp = client.delete(f"/api/presets/{p_id}")
    assert del_resp.status_code == 200

def test_slots_and_semesters():
    sem_resp = client.get("/api/semesters")
    assert sem_resp.status_code == 200
    semesters = sem_resp.json()
    assert len(semesters) > 0
    active_sem = [s for s in semesters if s["is_active"]][0]

    slots_resp = client.get(f"/api/slots?semester_id={active_sem['id']}")
    assert slots_resp.status_code == 200
    slots = slots_resp.json()
    assert len(slots) > 0

    # Add new slot
    new_slot = {
        "semester_id": active_sem["id"],
        "day_of_week": "Čtvrtek",
        "time_start": "14:00",
        "time_end": "16:00",
        "name": "Skupina C",
        "room": "F1"
    }
    create_slot_resp = client.post("/api/slots", json=new_slot)
    assert create_slot_resp.status_code == 200
    slot_id = create_slot_resp.json()["id"]

    # Delete slot
    del_slot_resp = client.delete(f"/api/slots/{slot_id}")
    assert del_slot_resp.status_code == 200

def test_user_roles_and_assistant_restrictions():
    import time
    # Ensure admin logged in
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    u_name = f"asist_{int(time.time())}"
    # Admin creates assistant user
    create_user_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Ing. Jan Asistent",
        "password": "heslo123",
        "role": "assistant"
    })
    assert create_user_resp.status_code == 200
    u_id = create_user_resp.json()["id"]

    # Logout admin
    client.post("/api/auth/logout")

    # Login as assistant
    login_resp = client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    assert login_resp.status_code == 200

    # Assistant attempts to view /api/users -> should be 403 Forbidden!
    users_resp = client.get("/api/users")
    assert users_resp.status_code == 403

    # Assistant can change their password
    chg_pw_resp = client.post("/api/auth/change-password", json={
        "old_password": "heslo123",
        "new_password": "heslo456"
    })
    assert chg_pw_resp.status_code == 200

    # Login with new password
    client.post("/api/auth/logout")
    login2_resp = client.post("/api/auth/login", json={"username": u_name, "password": "heslo456"})
    assert login2_resp.status_code == 200

    # Switch back to admin and delete test user
    client.post("/api/auth/logout")
    admin_login = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200

    del_resp = client.delete(f"/api/users/{u_id}")
    assert del_resp.status_code == 200

def test_protocol_evaluation_and_burn():
    # Check seeded protocol
    protos_resp = client.get("/api/protocols")
    assert protos_resp.status_code == 200
    protos = protos_resp.json()
    assert len(protos) > 0
    p = protos[0]
    p_id = p["id"]

    # Save evaluation with deductions and annotations (including text_direct!)
    eval_payload = {
        "protocol_id": p_id,
        "vysledky_score": 2.5,
        "diskuze_score": 2.5,
        "format_score": 1.5,
        "chyby_score": 2.0,
        "total_points": 8.5,
        "grade": "B",
        "manual_grade_override": False,
        "deductions": [
            {"category": "format", "pts": 0.5, "reason": "Chybějící popisek grafu"},
            {"category": "vysledky", "pts": 0.5, "reason": "Zaokrouhlení chyby"}
        ],
        "raw_output_1": "Výsledky: 2.5 / 3, Diskuze: 2.5 / 3, Formát: 1.5 / 2, Chyby: 2 / 2, Celkem bodů: 8.50 / 10, Známka: B",
        "raw_output_2": "Vysledky: 2.5 b / 3 b\nDiskuze: 2.5 b / 3 b\nFormat: 1.5 b / 2 b\nChyby: 2.0 b / 2 b\nCelkem: 8.5 b / 10 b\nZnamka: B",
        "annotations": [
            {
                "page": 1,
                "type": "text_direct",
                "point": [150, 200],
                "content": "Opravil: Asistent. Doplňte nejistoty!",
                "fontsize": 13,
                "color": [0.88, 0.11, 0.18]
            },
            {
                "page": 1,
                "type": "highlight",
                "rect": [100, 150, 300, 170],
                "content": "To není akademický styl"
            }
        ]
    }

    save_resp = client.post(f"/api/protocols/{p_id}/evaluation", json=eval_payload)
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["status"] == "ok"
    assert save_data["corrected_pdf_created"] is True

    # Verify bodovani.txt export
    txt_resp = client.get(f"/api/protocols/{p_id}/export/bodovani.txt")
    assert txt_resp.status_code == 200
    assert "Celkem" in txt_resp.text

    # Verify corrected PDF download
    pdf_resp = client.get(f"/api/protocols/{p_id}/pdf/corrected")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"

def test_strikeout_annotation_and_revision_status():
    protos_resp = client.get("/api/protocols")
    assert protos_resp.status_code == 200
    protos = protos_resp.json()
    assert len(protos) > 0
    p_id = protos[0]["id"]

    eval_payload = {
        "protocol_id": p_id,
        "vysledky_score": 1.5,
        "diskuze_score": 1.0,
        "format_score": 1.0,
        "chyby_score": 1.0,
        "total_points": 4.5,
        "grade": "F",
        "manual_grade_override": False,
        "status": "revision",
        "deductions": [
            {"category": "diskuze", "pts": 1.5, "reason": "Chybí zhodnocení chyb"}
        ],
        "raw_output_1": "Výsledky: 1.5 / 3, Diskuze: 1.0 / 3, Formát: 1.0 / 2, Chyby: 1.0 / 2, Celkem: 4.50 / 10, Známka: F",
        "raw_output_2": "Vysledky: 1.5 b\nCelkem: 4.5 b\nZnamka: F",
        "burn_to_pdf": True,
        "annotations": [
            {
                "page": 1,
                "type": "strikeout",
                "rect": [120, 220, 320, 235],
                "content": "Chybný výpočet střední hodnoty"
            }
        ]
    }

    save_resp = client.post(f"/api/protocols/{p_id}/evaluation", json=eval_payload)
    assert save_resp.status_code == 200
    save_data = save_resp.json()
    assert save_data["status"] == "ok"
    assert save_data["corrected_pdf_created"] is True

    # Check updated protocol status is 'revision'
    get_p = client.get(f"/api/protocols/{p_id}")
    assert get_p.status_code == 200
    assert get_p.json()["status"] == "revision"

def test_assign_evaluator_to_protocol():
    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    protos_resp = client.get("/api/protocols")
    assert protos_resp.status_code == 200
    p_id = protos_resp.json()[0]["id"]

    # Assign evaluator
    assign_resp = client.put(f"/api/protocols/{p_id}/assign", json={"evaluator_id": 1})
    assert assign_resp.status_code == 200
    assert assign_resp.json()["evaluator_id"] == 1

    # Unassign
    unassign_resp = client.put(f"/api/protocols/{p_id}/assign", json={"evaluator_id": None})
    assert unassign_resp.status_code == 200
    assert unassign_resp.json()["evaluator_id"] is None

def test_zip_export():
    import zipfile
    import io

    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    resp = client.get("/api/export/zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "praktika_export_" in resp.headers["content-disposition"]

    # Verify valid zip file
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    namelist = zf.namelist()
    assert len(namelist) > 0
    # Check that at least one .pdf or .txt is inside
    assert any(n.endswith(".pdf") or n.endswith(".txt") for n in namelist)

def test_csv_export():
    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "praktika_vysledky_" in resp.headers["content-disposition"]

    # Excel Czech CSV check: UTF-8 BOM and semicolon delimited
    text = resp.content.decode("utf-8-sig")
    assert text.startswith("Student;Úloha;")
    lines = text.strip().split("\n")
    assert len(lines) >= 2  # Header + at least 1 protocol row
    assert ";" in lines[0]

def test_update_protocol_metadata():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    protos_resp = client.get("/api/protocols")
    assert protos_resp.status_code == 200
    p = protos_resp.json()[0]
    p_id = p["id"]

    new_name = "Karel Testovací-Nový"
    update_payload = {
        "student_name": new_name,
        "semester_id": p["semester_id"],
        "slot_id": p["slot_id"],
        "measurement_id": p["measurement_id"]
    }
    put_resp = client.put(f"/api/protocols/{p_id}/metadata", json=update_payload)
    assert put_resp.status_code == 200
    updated_p = put_resp.json()
    assert updated_p["student_name"] == new_name

    # Verify persistence via get
    get_resp = client.get(f"/api/protocols/{p_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["student_name"] == new_name

def test_ai_settings_and_analysis():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    
    # Check GET AI settings
    get_ai = client.get("/api/settings/ai")
    assert get_ai.status_code == 200
    assert "ai_enabled" in get_ai.json()

    # Update AI settings
    post_ai = client.post("/api/settings/ai", json={"gemini_api_key": "test_dummy_key", "ai_enabled": True})
    assert post_ai.status_code == 200
    assert post_ai.json()["gemini_api_key"] == "test_dummy_key"
    assert post_ai.json()["ai_enabled"] is True

    # Run AI analysis on a protocol (mocked for offline test suite)
    protos_resp = client.get("/api/protocols")
    p_id = protos_resp.json()[0]["id"]
    from unittest.mock import patch, AsyncMock
    from app.models import AIAnalysisResult, AIDeductionSuggestion, AIAnnotationSuggestion
    mock_res = AIAnalysisResult(
        protocol_id=p_id,
        scores={"vysledky": 3.0, "diskuze": 2.5, "format": 2.0, "chyby": 1.5},
        deductions=[AIDeductionSuggestion(proposal_id="p1", category="diskuze", pts=-0.5, reason="Chybí diskuze neistot", page=1)],
        annotations=[AIAnnotationSuggestion(proposal_id="a1", page=1, type="highlight", comment="Doplnit jednotky")],
        summary="Analýza dokončena",
        model_used="gemini-3.5-flash"
    )
    with patch("app.main.analyze_protocol", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_res
        ai_resp = client.post(f"/api/protocols/{p_id}/ai-analyze")
        assert ai_resp.status_code == 200
        ai_data = ai_resp.json()
        assert "deductions" in ai_data
        assert "annotations" in ai_data
        assert "summary" in ai_data
        assert len(ai_data["deductions"]) > 0

    # Clean up key to keep default
    client.post("/api/settings/ai", json={"gemini_api_key": "", "ai_enabled": True})

def test_changelog_endpoint():
    resp = client.get("/api/changelog")
    assert resp.status_code == 200
    data = resp.json()
    assert "content" in data
    assert "2.3.0" in data["content"]
    assert "2.2.0" in data["content"]
    assert "FPRA1" in data["content"]

def test_storage_folder_naming():
    from app.storage import format_semester_folder, format_slot_folder
    assert format_semester_folder("2026ZS") == "FPRA1_2026ZS"
    assert format_semester_folder("2026LS") == "FPRA2_2026LS"
    assert format_semester_folder("2026LS", "ZFM") == "ZFM2_2026LS"

    assert format_slot_folder("Pondělí", "08:00", "12:00", "F3") == "Pondeli_8h_F3"
    assert format_slot_folder("Středa", "14:00", "18:00", "") == "Streda_14h"

def test_autosave_endpoint():
    protos_resp = client.get("/api/protocols")
    p_id = protos_resp.json()[0]["id"]

    autosave_payload = {
        "evaluation": {
            "vysledky_score": 2.75,
            "diskuze_score": 2.5,
            "format_score": 1.75,
            "chyby_score": 2.0,
            "total_points": 9.0,
            "grade": "A",
            "deductions": [
                {"category": "vysledky", "pts": 0.25, "reason": "Drobné zaokrouhlení"}
            ],
            "raw_output_1": "Výsledky: 2.75 / 3, Diskuze: 2.5 / 3, Formát: 1.75 / 2, Chyby: 2 / 2, Celkem bodů: 9.00 / 10, Známka: A",
            "raw_output_2": "Vysledky: 2.75 b / 3 b\nDiskuze: 2.5 b / 3 b\nFormat: 1.75 b / 2 b\nChyby: 2.0 b / 2 b\nCelkem: 9.0 b / 10 b\nZnamka: A"
        },
        "annotations": [
            {
                "page": 1,
                "type": "highlight",
                "rect": [50, 100, 200, 120],
                "rects": [{"x": 50, "y": 100, "width": 150, "height": 20}],
                "content": "Autosaved highlight",
                "color": "#ffeb3b"
            }
        ]
    }
    resp = client.post(f"/api/protocols/{p_id}/autosave", json=autosave_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "saved_at" in data

    # Verify retrieval
    detail_resp = client.get(f"/api/protocols/{p_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["annotations"]) == 1
    assert detail["annotations"][0]["content"] == "Autosaved highlight"
    assert detail["evaluation"]["total_points"] == 9.0

def test_ai_settings_model_and_auto_analyze():
    # Update AI settings to gemini-2.5-flash with auto-analyze enabled
    set_resp = client.post("/api/settings/ai", json={
        "ai_enabled": True,
        "gemini_api_key": "dummy-test-key",
        "model_name": "gemini-2.5-flash",
        "auto_analyze_on_upload": True
    })
    assert set_resp.status_code == 200

    get_resp = client.get("/api/settings/ai")
    assert get_resp.status_code == 200
    ai_settings = get_resp.json()
    assert ai_settings["model_name"] == "gemini-2.5-flash"
    assert ai_settings["auto_analyze_on_upload"] is True

    # Test custom model
    set_custom = client.post("/api/settings/ai", json={
        "ai_enabled": True,
        "gemini_api_key": "dummy-test-key",
        "model_name": "custom-special-model",
        "auto_analyze_on_upload": False
    })
    assert set_custom.status_code == 200
    get_custom = client.get("/api/settings/ai")
    assert get_custom.json()["model_name"] == "custom-special-model"
    assert get_custom.json()["auto_analyze_on_upload"] is False

    # Reset
    client.post("/api/settings/ai", json={
        "ai_enabled": True,
        "gemini_api_key": "",
        "model_name": "gemini-2.5-flash",
        "auto_analyze_on_upload": True
    })

def test_upload_with_native_annotations_extraction():
    # Upload FPRA1_Boril_uloha1_opravene.pdf
    pdf_path = "FPRA1_Boril_uloha1_opravene.pdf"
    if not os.path.exists(pdf_path):
        return

    # Fetch slot, semester, measurement
    slots_resp = client.get("/api/slots")
    slots = slots_resp.json()
    assert len(slots) > 0
    slot = slots[0]
    slot_id = slot["id"]
    sem_id = slot["semester_id"]
    meas_resp = client.get("/api/measurements?semester_type=ZS")
    meas_id = meas_resp.json()[0]["id"]

    with open(pdf_path, "rb") as f:
        files = {"file": ("FPRA1_Boril_uloha1_opravene.pdf", f, "application/pdf")}
        data = {
            "semester_id": sem_id,
            "slot_id": slot_id,
            "measurement_id": meas_id,
            "student_name": "Test Acrobat Student"
        }
        up_resp = client.post("/api/protocols/upload", data=data, files=files)
        assert up_resp.status_code == 200
        up_data = up_resp.json()
        assert up_data["extracted_annotations_count"] > 20
        new_p_id = up_data["id"]

    # Verify detail returns extracted Acrobat annotations
    detail_resp = client.get(f"/api/protocols/{new_p_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["annotations"]) > 20
    # Clean up test protocol
    client.delete(f"/api/protocols/{new_p_id}")

if __name__ == "__main__":
    tests = [obj for name, obj in list(globals().items()) if name.startswith("test_") and callable(obj)]
    print(f"Running {len(tests)} tests...")
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

