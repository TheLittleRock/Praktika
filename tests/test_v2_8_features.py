import os
import io
import time
import json
import sqlite3
import pymupdf
from starlette.testclient import TestClient
from app.main import app
from app.pdf_service import burn_annotations_to_pdf, calculate_grade_letter, FONT_DEJAVU, FONT_DEJAVU_BOLD
from app.ai_service import DEFAULT_PHYSICS_GUIDELINES

client = TestClient(app)

def create_sample_pdf_with_text(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), text, fontsize=12)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()

def test_v2_8_bulk_delete_and_update():
    login_admin = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_admin.status_code == 200

    # Get valid semester, slot, measurement
    conn = sqlite3.connect("data/praktika.sqlite3")
    cur = conn.cursor()
    sem_id = cur.execute("SELECT id FROM semesters LIMIT 1").fetchone()[0]
    slot_id = cur.execute("SELECT id FROM slots WHERE semester_id = ? LIMIT 1", (sem_id,)).fetchone()[0]
    meas_ids = [r[0] for r in cur.execute("SELECT id FROM measurements LIMIT 2").fetchall()]
    conn.close()

    # Create 3 test protocols
    pdf_bytes = create_sample_pdf_with_text("Studentský protokol test v2.8\nAutor: Jan Novák")
    p_ids = []
    for i in range(3):
        upload_resp = client.post(
            "/api/protocols/upload",
            data={
                "student_name": f"Student v2.8 #{i+1}",
                "semester_id": sem_id,
                "slot_id": slot_id,
                "measurement_id": meas_ids[0],
            },
            files={"file": (f"mereni_{i+1}.pdf", pdf_bytes, "application/pdf")}
        )
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        p_ids.append(upload_resp.json()["id"])

    assert len(p_ids) == 3

    # Test Bulk Update: change measurement_id to meas_ids[1] for first two protocols
    update_resp = client.post("/api/protocols/bulk-update", json={
        "protocol_ids": p_ids[:2],
        "measurement_id": meas_ids[1]
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["updated_count"] == 2

    # Verify update in DB
    p1 = client.get(f"/api/protocols/{p_ids[0]}").json()
    p2 = client.get(f"/api/protocols/{p_ids[1]}").json()
    p3 = client.get(f"/api/protocols/{p_ids[2]}").json()
    assert p1["measurement_id"] == meas_ids[1]
    assert p2["measurement_id"] == meas_ids[1]
    assert p3["measurement_id"] == meas_ids[0]  # Unchanged

    # Test Bulk Delete: delete all 3 protocols
    del_resp = client.post("/api/protocols/bulk-delete", json={
        "protocol_ids": p_ids
    })
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted_count"] == 3

    # Verify they are gone
    for pid in p_ids:
        assert client.get(f"/api/protocols/{pid}").status_code == 404

def test_v2_8_pdf_export_diacritics_and_stamp():
    # Verify TrueType fonts exist
    assert os.path.exists(FONT_DEJAVU), f"DejaVu font not found at {FONT_DEJAVU}"
    assert os.path.exists(FONT_DEJAVU_BOLD), f"DejaVu Bold font not found at {FONT_DEJAVU_BOLD}"

    # Verify calculate_grade_letter
    assert calculate_grade_letter(9.5) == "A"
    assert calculate_grade_letter(8.5) == "B"
    assert calculate_grade_letter(7.0) == "C"
    assert calculate_grade_letter(5.0) == "D"
    assert calculate_grade_letter(3.0) == "E"
    assert calculate_grade_letter(1.0) == "F"
    assert calculate_grade_letter(8.0, manual_override="A") == "A"
    # Ensure falsy/invalid manual override does not produce '0'
    assert calculate_grade_letter(9.5, manual_override="0") == "A"
    assert calculate_grade_letter(8.5, manual_override="False") == "B"

    # Test burn_annotations_to_pdf with ink strokes, deductions, and diacritics
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), "Ukázkový text laboratorního protokolu", fontsize=12)
    raw_pdf = doc.tobytes()
    doc.close()

    eval_data = {
        "student_name": "Rostislav Krásný",
        "evaluator_name": "Štěpán Skalka",
        "total_points": 8.75,
        "grade": "B",
        "manual_grade_override": None,
        "deductions": [
            {"category": "vysledky", "pts": 0.25, "reason": "Chybějící mezivýpočty"},
            {"category": "format", "pts": 0.25, "reason": "Chybějící čárka před , kde u vzorce (1)"},
            {"category": "chyby", "pts": 0.75, "reason": "Chybný počet platných cifer u nejistoty"}
        ],
        "annotations": [
            {
                "page": 1,
                "type": "ink",
                "strokes": [[[100.0, 150.0], [150.0, 160.0], [200.0, 180.0]]],
                "color": "#ef4444",
                "width": 2
            },
            {
                "page": 1,
                "type": "rect",
                "rect": [100, 200, 300, 250],
                "color": "#ef4444"
            },
            {
                "page": 1,
                "type": "arrow",
                "p1": [100, 300],
                "p2": [250, 320],
                "color": "#3b82f6"
            },
            {
                "page": 1,
                "type": "highlight",
                "rect": [50, 95, 250, 115],
                "rects": [[50, 95, 250, 115]],
                "content": "Pozor na formátování textu",
                "author": "Štěpán Skalka",
                "color": "#fef08a"
            }
        ]
    }

    burned_bytes = burn_annotations_to_pdf(
        raw_pdf,
        eval_data["annotations"],
        evaluation=eval_data,
        evaluator_name=eval_data["evaluator_name"]
    )
    assert len(burned_bytes) > len(raw_pdf)

    # Inspect burned PDF
    burned_doc = pymupdf.open(stream=burned_bytes, filetype="pdf")
    page1 = burned_doc[0]
    page1_text = page1.get_text()

    # Verify diacritics and evaluator name rendered correctly
    assert "Štěpán Skalka" in page1_text
    assert "Celkem bodů:" in page1_text
    assert "Známka:" in page1_text
    assert "Přehled bodových srážek:" in page1_text
    assert "Chybějící mezivýpočty" in page1_text
    assert "Chybějící čárka před , kde" in page1_text

    # Verify annotations presence (ink, rect, arrow, highlight)
    annots = list(page1.annots())
    annot_types = [a.type[1] for a in annots]
    assert "Ink" in annot_types
    assert "Square" in annot_types
    assert "Line" in annot_types
    assert "Highlight" in annot_types
    burned_doc.close()

def test_v2_8_ai_guidelines_and_syntax():
    # Verify guidelines include formula punctuation and ', kde' rules
    assert ", kde" in DEFAULT_PHYSICS_GUIDELINES
    assert "interpunkce" in DEFAULT_PHYSICS_GUIDELINES or "čárka nebo tečka" in DEFAULT_PHYSICS_GUIDELINES
    assert "errorbary" in DEFAULT_PHYSICS_GUIDELINES
    assert "Mezera mezi číslem a jednotkou" in DEFAULT_PHYSICS_GUIDELINES

if __name__ == "__main__":
    print("Running v2.8 tests...")
    test_v2_8_bulk_delete_and_update()
    print("  ✓ test_v2_8_bulk_delete_and_update PASSED")
    test_v2_8_pdf_export_diacritics_and_stamp()
    print("  ✓ test_v2_8_pdf_export_diacritics_and_stamp PASSED")
    test_v2_8_ai_guidelines_and_syntax()
    print("  ✓ test_v2_8_ai_guidelines_and_syntax PASSED")
    print("ALL v2.8 TESTS PASSED SUCCESSFULLY!")
