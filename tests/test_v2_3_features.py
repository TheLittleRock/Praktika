import os
import json
from starlette.testclient import TestClient
from app.main import app
from app.ai_service import get_candidate_models, analyze_protocol
from app.pdf_service import _parse_to_fitz_rect, extract_pdf_annotations, burn_annotations_to_pdf
import fitz

client = TestClient(app)

def test_login_admin():
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["role"] == "admin"
    print("✓ Login admin passed")

def test_measurement_instructions_crud():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    
    # 1. Fetch measurement 1
    get_resp = client.get("/api/measurements")
    assert get_resp.status_code == 200
    measurements = get_resp.json()
    assert len(measurements) > 0
    m1 = measurements[0]
    m1_id = m1["id"]
    
    # 2. Update instructions
    test_instructions = "1. Měření doby průletu vozíku fotozavorou.\n2. Lineární regrese s = v*t.\n3. Výpočet chyby rychlosti."
    put_resp = client.put(f"/api/measurements/{m1_id}", json={
        "instructions_text": test_instructions
    })
    assert put_resp.status_code == 200, put_resp.text
    
    # 3. Verify retrieval
    get_updated = client.get("/api/measurements")
    updated_m1 = next(m for m in get_updated.json() if m["id"] == m1_id)
    assert updated_m1["instructions_text"] == test_instructions
    print("✓ Measurement instructions CRUD passed")

def test_ai_candidate_models_and_fallbacks():
    # Test default candidate models
    default_candidates = get_candidate_models(None)
    assert "gemini-3.5-flash-lite" in default_candidates
    assert "gemini-3.8-flash" in default_candidates
    assert "gemini-3.1-flash-lite" in default_candidates
    assert "gemini-flash-latest" in default_candidates

    # Test when user picks gemini-3.8-flash
    custom_candidates = get_candidate_models("gemini-3.8-flash")
    assert custom_candidates[0] == "gemini-3.8-flash"
    assert "gemini-3.5-flash-lite" in custom_candidates

    # Test when user picks custom model
    user_custom = get_candidate_models("my-fine-tuned-gemini")
    assert user_custom[0] == "my-fine-tuned-gemini"
    assert "gemini-3.5-flash-lite" in user_custom
    print("✓ AI candidate models & fallback chains passed")

def test_ai_settings_endpoint_models():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    
    # Set model to gemini-3.8-flash
    resp = client.post("/api/settings/ai", json={
        "gemini_api_key": "test_dummy_gemini_api_key_12345",
        "model_name": "gemini-3.8-flash",
        "auto_analyze_on_upload": True,
        "ai_enabled": True
    })
    assert resp.status_code == 200, resp.text
    
    get_resp = client.get("/api/settings/ai")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["model_name"] == "gemini-3.8-flash"
    assert data["auto_analyze_on_upload"] is True
    
    # Reset back to recommended gemini-3.5-flash
    client.post("/api/settings/ai", json={"model_name": "gemini-3.5-flash"})
    get_resp2 = client.get("/api/settings/ai")
    assert get_resp2.json()["model_name"] == "gemini-3.5-flash"
    print("✓ AI settings model selection endpoint passed")

def test_rect_normalization_and_acrobat_compatibility():
    # 1. 4-tuple format [x0, y0, x1, y1]
    rect1 = _parse_to_fitz_rect([50, 100, 200, 150])
    assert isinstance(rect1, fitz.Rect)
    assert rect1.x0 == 50 and rect1.y0 == 100 and rect1.x1 == 200 and rect1.y1 == 150

    # 2. Dictionary format {"x": 50, "y": 100, "width": 150, "height": 50}
    rect2 = _parse_to_fitz_rect({"x": 50, "y": 100, "width": 150, "height": 50})
    assert isinstance(rect2, fitz.Rect)
    assert rect2.x0 == 50 and rect2.y0 == 100 and rect2.x1 == 200 and rect2.y1 == 150

    # 3. None or invalid format returns None gracefully without throwing
    rect3 = _parse_to_fitz_rect(None)
    assert rect3 is None
    print("✓ Rect normalization & Acrobat compatibility passed")

def test_protocol_5_acrobat_loading():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    protos_resp = client.get("/api/protocols")
    assert protos_resp.status_code == 200
    protos = protos_resp.json()
    
    # Find protocol 5 or first available protocol
    proto = next((p for p in protos if p["id"] == 5), protos[0])
    proto_id = proto["id"]
    
    detail_resp = client.get(f"/api/protocols/{proto_id}")
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    
    annotations = detail.get("annotations", [])
    for a in annotations:
        # Verify rects are list of 4 numbers, not dicts that crash JS destructuring
        if "rects" in a and a["rects"]:
            for r in a["rects"]:
                assert isinstance(r, list) or isinstance(r, tuple), f"r must be iterable: {r}"
                assert len(r) == 4, f"r must have 4 coordinates: {r}"
    print("✓ Protocol Acrobat annotations structure verified")

def test_measurement_instructions_file_upload():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    get_resp = client.get("/api/measurements")
    m1_id = get_resp.json()[0]["id"]

    # 1. TXT upload
    sample_content = b"Zad\xc3\xa1n\xc3\xad \xc3\xbalohy: 1. Kalibrace silom\xc4\x9bru\n2. Ur\xc4\x8den\xc3\xad modulu pru\xc5\xbenosti"
    files = {"file": ("instructions.txt", sample_content, "text/plain")}
    resp = client.post(f"/api/measurements/{m1_id}/upload-instructions", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "Kalibrace siloměru" in data["instructions_text"]
    assert data["chars_extracted"] > 0

    # 2. PDF upload
    pdf_doc = fitz.open()
    pdf_page = pdf_doc.new_page(width=600, height=800)
    pdf_page.insert_text((50, 50), "Navod k mereni: Kalorimetricke stanoveni mernych tepel", fontsize=12)
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    pdf_files = {"file": ("navod.pdf", pdf_bytes, "application/pdf")}
    resp2 = client.post(f"/api/measurements/{m1_id}/upload-instructions", files=pdf_files)
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    assert "Kalorimetricke" in data2["instructions_text"]
    assert data2["chars_extracted"] > 0
    print("✓ Measurement instructions file upload (TXT & PDF) passed")

def test_semester_activation_endpoint():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    sem_resp = client.get("/api/semesters")
    semesters = sem_resp.json()
    assert len(semesters) >= 2
    orig_active = next(s for s in semesters if s["is_active"])
    other_sem = next(s for s in semesters if not s["is_active"])
    
    act_resp = client.post(f"/api/semesters/{other_sem['id']}/activate")
    assert act_resp.status_code == 200
    
    # Verify other_sem is now active
    sem_resp2 = client.get("/api/semesters")
    active_sem = next(s for s in sem_resp2.json() if s["is_active"])
    assert active_sem["id"] == other_sem["id"]

    # Revert back to original active semester
    client.post(f"/api/semesters/{orig_active['id']}/activate")
    print("✓ Semester activation endpoint passed")

def test_arrow_annotation_burn_to_pdf():
    # Create a dummy 1-page PDF
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((50, 50), "Test PDF for Arrow Annotation", fontsize=14)
    tmp_path = "/tmp/test_arrow_burn.pdf"
    doc.save(tmp_path)
    doc.close()

    annotations = [{
        "page": 1,
        "type": "arrow",
        "p1": [100, 100],
        "p2": [200, 200],
        "color": "#ef4444"
    }]
    out_bytes = burn_annotations_to_pdf(tmp_path, annotations)
    assert len(out_bytes) > 0
    
    # Verify annotation in output PDF
    out_doc = fitz.open(stream=out_bytes, filetype="pdf")
    out_page = out_doc[0]
    annots = list(out_page.annots())
    assert len(annots) >= 1
    assert annots[0].type[0] == fitz.PDF_ANNOT_LINE
    out_doc.close()
    if os.path.exists(tmp_path): os.remove(tmp_path)
    print("✓ Arrow annotation burning with arrowhead passed")

def test_generate_rubric_endpoint():
    client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    m_list = client.get("/api/measurements").json()
    assert len(m_list) > 0
    m_id = m_list[0]["id"]
    
    resp = client.post(f"/api/measurements/{m_id}/generate-rubric", json={
        "instructions_text": "Úloha 1: Měření na vzduchové dráze. Změřte rychlost a zrychlení. Vypočtěte chyby a sestrojte graf."
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "ok"
    assert len(data["instructions_text"]) > 0
    print("✓ AI generate rubric endpoint passed")

if __name__ == "__main__":
    test_login_admin()
    test_measurement_instructions_crud()
    test_ai_candidate_models_and_fallbacks()
    test_ai_settings_endpoint_models()
    test_rect_normalization_and_acrobat_compatibility()
    test_protocol_5_acrobat_loading()
    test_measurement_instructions_file_upload()
    test_semester_activation_endpoint()
    test_arrow_annotation_burn_to_pdf()
    test_generate_rubric_endpoint()
    print("\nALL FEATURE TESTS COMPLETED SUCCESSFULLY!")

