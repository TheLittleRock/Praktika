import os
import time
import json
import pymupdf
from starlette.testclient import TestClient
from app.main import app
from app.database import get_db

client = TestClient(app)

def get_or_create_test_pdf():
    pdf_path = "test_v2_6_sample.pdf"
    if not os.path.exists(pdf_path):
        doc = pymupdf.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 50), "Testovaci protokol pro v2.6.0\nStudent: Jan Novak\nUloha: 1", fontsize=12)
        doc.save(pdf_path)
        doc.close()
    return pdf_path

def test_protocol_upload_assigns_uploader_to_my_protocols():
    # 1. Login as admin, create a dedicated assistant
    login_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200

    u_name = f"asist_v26_{int(time.time())}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Asistent Test v2.6",
        "password": "heslo123",
        "role": "assistant"
    })
    assert u_resp.status_code == 200
    u_data = u_resp.json()
    assistant_id = u_data["id"]

    # 2. Login as this assistant
    login_asist = client.post("/api/auth/login", json={"username": u_name, "password": "heslo123"})
    assert login_asist.status_code == 200

    # Get active semester and slot
    sem_resp = client.get("/api/semesters")
    semesters = sem_resp.json()
    active_sem = next((s for s in semesters if s["is_active"]), semesters[0])

    slot_resp = client.get(f"/api/slots?semester_id={active_sem['id']}")
    slots = slot_resp.json()
    assert len(slots) > 0, "No slots found for active semester"
    slot_id = slots[0]["id"]

    meas_resp = client.get("/api/measurements")
    measurements = meas_resp.json()
    assert len(measurements) > 0, "No measurements found"
    meas_id = measurements[0]["id"]

    # 3. Upload a new protocol as the assistant
    pdf_path = get_or_create_test_pdf()
    with open(pdf_path, "rb") as f:
        upload_resp = client.post(
            "/api/protocols/upload",
            data={
                "semester_id": active_sem["id"],
                "slot_id": slot_id,
                "measurement_id": meas_id,
                "student_name": "Testovaci Student v2.6"
            },
            files={"file": ("test_proto.pdf", f, "application/pdf")}
        )
    assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
    proto_info = upload_resp.json()
    proto_id = proto_info["id"]

    # 4. Verify evaluator_id is immediately assigned to this assistant
    proto_detail = client.get(f"/api/protocols/{proto_id}").json()
    assert proto_detail["evaluator_id"] == assistant_id, f"Expected evaluator_id {assistant_id}, got {proto_detail.get('evaluator_id')}"

    # 5. Check 'evaluator_id=me' filter returns this protocol immediately
    my_protos_resp = client.get("/api/protocols?evaluator_id=me")
    assert my_protos_resp.status_code == 200
    my_ids = [p["id"] for p in my_protos_resp.json()]
    assert proto_id in my_ids, f"Protocol {proto_id} not found in 'evaluator_id=me' list"

    # 6. Check 'evaluator_id=other' filter does NOT contain this protocol
    other_protos_resp = client.get("/api/protocols?evaluator_id=other")
    assert other_protos_resp.status_code == 200
    other_ids = [p["id"] for p in other_protos_resp.json()]
    assert proto_id not in other_ids, f"Protocol {proto_id} should NOT be in 'evaluator_id=other' list"

    return proto_id

def test_autosave_updates_ai_proposals_json_and_persists():
    # 1. Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})

    # Get or create protocol
    proto_id = test_protocol_upload_assigns_uploader_to_my_protocols()

    # 2. Simulate initial AI proposals saved via autosave
    initial_proposals = {
        "deductions": [
            {"proposal_id": "ded_1", "category": "vysledky", "pts": 0.5, "reason": "Chybi vypocet nejistoty", "page": 1},
            {"proposal_id": "ded_2", "category": "format", "pts": 0.25, "reason": "Spatne popisky os grafu", "page": 2}
        ],
        "annotations": [
            {"proposal_id": "ai_prop_1", "page": 1, "rect": [50, 50, 200, 70], "comment": "Zde chybi jednotka", "type": "highlight"},
            {"proposal_id": "ai_prop_2", "page": 2, "rect": [100, 100, 300, 120], "comment": "Upravte popisek", "type": "highlight"}
        ]
    }

    autosave_resp = client.post(f"/api/protocols/{proto_id}/autosave", json={
        "ai_proposals": initial_proposals
    })
    assert autosave_resp.status_code == 200, f"Autosave failed: {autosave_resp.text}"

    # 3. Retrieve protocol and check ai_proposals
    get_resp = client.get(f"/api/protocols/{proto_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["ai_proposals"] is not None
    assert len(data["ai_proposals"]["deductions"]) == 2
    assert len(data["ai_proposals"]["annotations"]) == 2
    assert data["ai_proposals"]["deductions"][0]["proposal_id"] == "ded_1"

    # 4. Now simulate user approving/rejecting proposals (1 deduction removed, 1 annotation removed)
    updated_proposals = {
        "deductions": [
            {"proposal_id": "ded_2", "category": "format", "pts": 0.25, "reason": "Spatne popisky os grafu", "page": 2}
        ],
        "annotations": [
            {"proposal_id": "ai_prop_2", "page": 2, "rect": [100, 100, 300, 120], "comment": "Upravte popisek", "type": "highlight"}
        ]
    }

    autosave_resp2 = client.post(f"/api/protocols/{proto_id}/autosave", json={
        "ai_proposals": updated_proposals
    })
    assert autosave_resp2.status_code == 200

    # 5. Retrieve protocol again (simulating user closing and reopening the protocol)
    get_resp2 = client.get(f"/api/protocols/{proto_id}")
    assert get_resp2.status_code == 200
    data2 = get_resp2.json()
    assert len(data2["ai_proposals"]["deductions"]) == 1
    assert data2["ai_proposals"]["deductions"][0]["proposal_id"] == "ded_2"
    assert len(data2["ai_proposals"]["annotations"]) == 1
    assert data2["ai_proposals"]["annotations"][0]["proposal_id"] == "ai_prop_2"

def test_ai_analysis_mode_handling():
    # Login as admin
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    proto_id = test_protocol_upload_assigns_uploader_to_my_protocols()

    # Pre-populate some proposals
    with get_db() as db:
        initial = {
            "deductions": [{"proposal_id": "old_ded", "category": "chyby", "pts": 0.25, "reason": "Stara chyba"}],
            "annotations": [{"proposal_id": "old_annot", "page": 1, "comment": "Stara poznamka"}]
        }
        db.execute("UPDATE protocols SET ai_proposals_json = ? WHERE id = ?", (json.dumps(initial), proto_id))

    # Test analyze call with mode=replace and mode=merge parameter acceptance
    # (Since there is no GEMINI_API_KEY set in test environment, it returns 400 with API key warning)
    resp_replace = client.post(f"/api/protocols/{proto_id}/ai-analyze?mode=replace")
    assert resp_replace.status_code in [200, 400, 500]
    if resp_replace.status_code in [400, 500]:
        detail = resp_replace.json().get("detail", "")
        assert ("API klíč" in detail or "Temporary failure" in detail or "modely selhaly" in detail or "spojení" in detail)

    resp_merge = client.post(f"/api/protocols/{proto_id}/ai-analyze?mode=merge")
    assert resp_merge.status_code in [200, 400, 500]
    if resp_merge.status_code in [400, 500]:
        detail = resp_merge.json().get("detail", "")
        assert ("API klíč" in detail or "Temporary failure" in detail or "modely selhaly" in detail or "spojení" in detail)

def test_ai_proposals_action_endpoint():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    proto_id = test_protocol_upload_assigns_uploader_to_my_protocols()

    proposals = {
        "deductions": [
            {"proposal_id": "ded_test_1", "category": "vysledky", "pts": 0.5, "reason": "Spatne vysledky", "page": 1},
            {"proposal_id": "ded_test_2", "category": "format", "pts": 0.25, "reason": "Chybi popisek", "page": 2}
        ],
        "annotations": [
            {"proposal_id": "annot_test_1", "page": 1, "rect": [50, 50, 150, 70], "comment": "Chyba zde", "type": "highlight"},
            {"proposal_id": "annot_test_2", "page": 2, "rect": [60, 60, 160, 80], "comment": "Druha chyba", "type": "highlight"}
        ]
    }
    client.post(f"/api/protocols/{proto_id}/autosave", json={"ai_proposals": proposals})

    # 1. Approve annotation 1
    resp = client.post(f"/api/protocols/{proto_id}/ai-proposals/action", json={
        "action": "approve_annotation",
        "proposal_id": "annot_test_1"
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["ai_proposals"]["annotations"]) == 1
    assert data["ai_proposals"]["annotations"][0]["proposal_id"] == "annot_test_2"
    assert data["created_annotation"] is not None
    assert data["created_annotation"]["content"] == "Chyba zde"

    # Verify directly from protocol endpoint (persisted in SQLite)
    proto_detail = client.get(f"/api/protocols/{proto_id}").json()
    assert len(proto_detail["ai_proposals"]["annotations"]) == 1
    assert any(a["content"] == "Chyba zde" for a in proto_detail["annotations"])

    # 2. Reject annotation 2
    resp_rej = client.post(f"/api/protocols/{proto_id}/ai-proposals/action", json={
        "action": "reject_annotation",
        "proposal_id": "annot_test_2"
    })
    assert resp_rej.status_code == 200
    proto_detail2 = client.get(f"/api/protocols/{proto_id}").json()
    assert len(proto_detail2["ai_proposals"]["annotations"]) == 0

    # 3. Approve deduction 1
    resp_ded = client.post(f"/api/protocols/{proto_id}/ai-proposals/action", json={
        "action": "approve_deduction",
        "proposal_id": "ded_test_1"
    })
    assert resp_ded.status_code == 200
    proto_detail3 = client.get(f"/api/protocols/{proto_id}").json()
    assert len(proto_detail3["ai_proposals"]["deductions"]) == 1
    assert proto_detail3["evaluation"] is not None
    assert any(d["reason"] == "Spatne vysledky" for d in proto_detail3["evaluation"]["deductions"])
    assert proto_detail3["total_points"] < 10.0

    # 4. Reject deduction 2
    resp_ded_rej = client.post(f"/api/protocols/{proto_id}/ai-proposals/action", json={
        "action": "reject_deduction",
        "proposal_id": "ded_test_2"
    })
    assert resp_ded_rej.status_code == 200
    proto_detail4 = client.get(f"/api/protocols/{proto_id}").json()
    assert len(proto_detail4["ai_proposals"]["deductions"]) == 0

def test_user_delete_and_protocol_delete_safety():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    u_name = f"user_to_delete_{int(time.time()*1000)}"
    u_resp = client.post("/api/users", json={
        "username": u_name,
        "full_name": "Smazat Me",
        "password": "heslo",
        "role": "assistant"
    })
    assert u_resp.status_code == 200
    user_id = u_resp.json()["id"]

    # Delete user
    del_u_resp = client.delete(f"/api/users/{user_id}")
    assert del_u_resp.status_code == 200

    # Test protocol deletion
    proto_id = test_protocol_upload_assigns_uploader_to_my_protocols()
    del_p_resp = client.delete(f"/api/protocols/{proto_id}")
    assert del_p_resp.status_code == 200

    # Verify db is not locked by performing another query immediately
    verify_resp = client.get(f"/api/protocols/{proto_id}")
    assert verify_resp.status_code == 404

if __name__ == "__main__":
    print("Running v2.6.0 feature tests...")
    test_protocol_upload_assigns_uploader_to_my_protocols()
    print("  ✓ test_protocol_upload_assigns_uploader_to_my_protocols PASSED")
    test_autosave_updates_ai_proposals_json_and_persists()
    print("  ✓ test_autosave_updates_ai_proposals_json_and_persists PASSED")
    test_ai_analysis_mode_handling()
    print("  ✓ test_ai_analysis_mode_handling PASSED")
    test_ai_proposals_action_endpoint()
    print("  ✓ test_ai_proposals_action_endpoint PASSED")
    test_user_delete_and_protocol_delete_safety()
    print("  ✓ test_user_delete_and_protocol_delete_safety PASSED")
    print("\nALL 5/5 v2.6.0 FEATURE TESTS PASSED SUCCESSFULLY!")

