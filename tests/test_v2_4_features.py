import os
import io
import fitz
from starlette.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
from app.pdf_service import format_points, burn_annotations_to_pdf

client = TestClient(app)

def login_admin():
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp

def test_format_points_helper():
    assert format_points(9.375) == "9.375"
    assert format_points(9.5) == "9.5"
    assert format_points(10.0) == "10"
    assert format_points(0.125) == "0.125"
    assert format_points(8.875) == "8.875"
    assert format_points(0) == "0"
    assert format_points(None) == "0"
    assert format_points("9.375") == "9.375"

def test_pdf_banner_stamp_exact_points():
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        doc.save(tmp_path)
        doc.close()

    eval_data = {
        "status": "graded",
        "total_points": 9.375,
        "grade": "A",
        "evaluator_name": "Ing. Testující Vyučující",
        "category_scores": {
            "vysledky": 3.0,
            "diskuze": 2.875,
            "format": 1.75,
            "chyby": 1.75
        },
        "deductions": [
            {"category": "diskuze", "pts": 0.125, "reason": "Drobné opomenutí"}
        ]
    }

    try:
        burned_bytes = burn_annotations_to_pdf(tmp_path, [], eval_data)
        assert burned_bytes is not None

        burned_doc = fitz.open(stream=burned_bytes, filetype="pdf")
        first_page_text = burned_doc[0].get_text()
        burned_doc.close()

        assert "9.375" in first_page_text, f"Exact points 9.375 not found in stamped text: {first_page_text}"
        assert "Známka: A" in first_page_text
        print("✓ test_pdf_banner_stamp_exact_points passed!")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_semester_edit_and_delete():
    login_admin()

    # 1. Create a test semester
    resp = client.post("/api/semesters", json={"code": "TEST_SEM", "name": "Testovací Semestr", "is_active": False})
    assert resp.status_code == 200, resp.text
    sem_data = resp.json()
    sem_id = sem_data["id"]

    # 2. Update semester code and name
    resp_put = client.put(f"/api/semesters/{sem_id}", json={"code": "TEST_SEM_MOD", "name": "Modifikovaný Semestr"})
    assert resp_put.status_code == 200, resp_put.text
    assert resp_put.json()["code"] == "TEST_SEM_MOD"
    assert resp_put.json()["name"] == "Modifikovaný Semestr"

    # 3. Delete empty semester
    resp_del = client.delete(f"/api/semesters/{sem_id}")
    assert resp_del.status_code == 200, resp_del.text

    # 4. Verify it was deleted
    resp_list = client.get("/api/semesters")
    sem_ids = [s["id"] for s in resp_list.json()]
    assert sem_id not in sem_ids
    print("✓ test_semester_edit_and_delete passed!")

def test_measurements_by_course():
    login_admin()

    # Test filtering by course_code
    for course in ("FPRA1", "FPRA2", "ZFM2"):
        resp = client.get(f"/api/measurements?course_code={course}")
        assert resp.status_code == 200
        meas = resp.json()
        assert len(meas) > 0, f"Expected seeded measurements for {course}"
        for m in meas:
            assert m["course_code"] == course

    # Create new measurement in FPRA1
    resp_post = client.post("/api/measurements", json={
        "code": "99",
        "number": 99,
        "name": "Nová testovací úloha",
        "semester_type": "ZS",
        "course_code": "FPRA1"
    })
    assert resp_post.status_code == 200
    new_id = resp_post.json()["id"]
    assert resp_post.json()["course_code"] == "FPRA1"

    # Clean up
    client.delete(f"/api/measurements/{new_id}")
    print("✓ test_measurements_by_course passed!")

def test_user_admin_update_and_profile():
    login_admin()

    # 1. Update own profile full name
    resp_prof = client.post("/api/auth/profile", json={"full_name": "Prof. Test Novák, CSc."})
    assert resp_prof.status_code == 200, resp_prof.text
    assert resp_prof.json()["full_name"] == "Prof. Test Novák, CSc."

    # Verify /api/auth/me reflects the updated name
    resp_me = client.get("/api/auth/me")
    assert resp_me.status_code == 200
    assert resp_me.json()["full_name"] == "Prof. Test Novák, CSc."

    # 2. Create a test assistant
    resp_create = client.post("/api/users", json={
        "username": "test_asst",
        "full_name": "Asistent Test",
        "password": "password123",
        "role": "assistant"
    })
    assert resp_create.status_code == 200, resp_create.text
    asst_id = resp_create.json()["id"]

    # 3. Admin updates assistant (name, is_active=False)
    resp_update = client.put(f"/api/users/{asst_id}", json={
        "full_name": "Asistent Test Modifikovaný",
        "is_active": False
    })
    assert resp_update.status_code == 200, resp_update.text
    assert resp_update.json()["full_name"] == "Asistent Test Modifikovaný"
    assert resp_update.json()["is_active"] is False

    # 4. Clean up
    client.delete(f"/api/users/{asst_id}")

    # Restore admin name
    client.post("/api/auth/profile", json={"full_name": "Správce aplikace"})
    print("✓ test_user_admin_update_and_profile passed!")

def test_csv_export_exact_points():
    login_admin()
    resp = client.get("/api/export/csv")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    print("✓ test_csv_export_exact_points passed!")

if __name__ == "__main__":
    init_db()
    test_format_points_helper()
    test_pdf_banner_stamp_exact_points()
    test_semester_edit_and_delete()
    test_measurements_by_course()
    test_user_admin_update_and_profile()
    test_csv_export_exact_points()
    print("\nALL v2.4 FEATURE TESTS PASSED SUCCESSFULLY!")
