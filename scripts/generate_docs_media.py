#!/usr/bin/env python3
"""
Automated media generation script for Praktika Evaluation Studio v2.12.0.
Captures real application screenshots and generates smooth animated walkthroughs (WebP & GIF)
using Playwright and ffmpeg directly against the running application.
Strictly uses test protocols of Štěpán Skalka (Protokoly testovaci/Kalorimetrie.pdf).
"""

import os
import sys
import time
import json
import shutil
import secrets
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
DOCS_ASSETS_DIR = BASE_DIR / "docs" / "assets" / "images"
DOCS_IMAGES_DIR = BASE_DIR / "docs" / "images"
DOCS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

SERVER_PORT = 8000
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"

def is_server_running() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER_URL}/api/version", timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_server():
    if is_server_running():
        print(f"Server is already running on {SERVER_URL}")
        return None
    print(f"Starting uvicorn server on {SERVER_URL}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(SERVER_PORT), "--host", "127.0.0.1"],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    for _ in range(30):
        time.sleep(0.5)
        if is_server_running():
            print("Server successfully started and healthy!")
            return proc
    raise RuntimeError("Failed to start uvicorn server within timeout")

def compile_frames_to_animation(frame_dir: Path, out_webp: Path, out_gif: Path, fps: int = 8, width: int = 1080):
    print(f"Compiling frames to animated WebP: {out_webp.name}...")
    # 1. High quality WebP
    cmd_webp = [
        "ffmpeg", "-y", "-r", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-vf", f"scale={width}:-1:flags=lanczos",
        "-vcodec", "libwebp", "-lossless", "0", "-qscale", "75",
        "-preset", "picture", "-loop", "0",
        str(out_webp)
    ]
    subprocess.run(cmd_webp, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"WebP generated: {out_webp.name} ({out_webp.stat().st_size // 1024} KB)")

    # 2. Optimized GIF with two-pass palettegen
    print(f"Compiling frames to palette-optimized GIF: {out_gif.name}...")
    palette = frame_dir / "palette.png"
    subprocess.run([
        "ffmpeg", "-y", "-r", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-vf", f"scale={width}:-1:flags=lanczos,palettegen=stats_mode=diff",
        str(palette)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    subprocess.run([
        "ffmpeg", "-y", "-r", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-i", str(palette),
        "-lavfi", f"scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=4",
        str(out_gif)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"GIF generated: {out_gif.name} ({out_gif.stat().st_size // 1024} KB)")

def seed_database_with_test_protocols():
    print("Seeding database with Štěpán Skalka test protocols...")
    from app.database import init_db
    init_db()
    from app.config import DATA_DIR, DB_PATH
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DELETE FROM evaluations")
    cur.execute("DELETE FROM annotations")
    cur.execute("DELETE FROM protocols")

    test_dir = BASE_DIR / "Protokoly testovaci"
    pdf_files = [
        ("Kalorimetrie.pdf", 6, "06"),
        ("Harmonicke oscilace Skalka.pdf", 5, "05"),
        ("Mereni pruznosti.pdf", 3, "03"),
        ("Vzduchova draha.pdf", 1, "01")
    ]

    now = datetime.now().isoformat()
    primary_proto_id = None
    primary_share_tok = None

    for filename, meas_id, meas_code in pdf_files:
        src_file = test_dir / filename
        if not src_file.exists():
            continue

        dest_dir = DATA_DIR / "protocols" / "FPRA1_2026ZS" / "Streda_8h" / meas_code / "stepan_skalka" / "source"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / filename
        shutil.copy(src_file, dest_file)

        tok = secrets.token_urlsafe(16)

        ai_proposals = None
        if meas_code == "06":
            ai_proposals = {
                "summary": "Protokol je po formální i obsahové stránce na vysoké úrovni. Naměřené hodnoty tepelné kapacity kalorimetru odpovídají očekávání.",
                "deductions": [
                    {"proposal_id": "p_ded_1", "category": "diskuze", "pts": 0.25, "reason": "Diskuze: Chybí detailnější rozbor tepelných ztrát do okolí během měření tepelné kapacity.", "page": 2},
                    {"proposal_id": "p_ded_2", "category": "format", "pts": 0.125, "reason": "Formát: V rovnici (3) chybí čárka mezi vzorcem a navazujícím textem \", kde\".", "page": 1}
                ],
                "annotations": [
                    {"proposal_id": "p_ann_1", "page": 1, "type": "highlight", "search_text": "tepelná kapacita", "comment": "Uveďte přesné jednotky u specifické tepelné kapacity [J/(kg.K)].", "rect": [120, 260, 480, 276]},
                    {"proposal_id": "p_ann_2", "page": 1, "type": "highlight", "search_text": "rovnice", "comment": "Chybějící čárka za vzorcem před \", kde\".", "rect": [150, 410, 440, 426]},
                    {"proposal_id": "p_ann_3", "page": 2, "type": "note", "point": [480, 310], "comment": "Graf chladnutí kalorimetru je zpracován velmi přehledně včetně fitování."}
                ]
            }

        cur.execute("""
        INSERT INTO protocols (
            semester_id, slot_id, measurement_id, student_name,
            status, source_filename, source_path, evaluator_id,
            total_points, grade, share_token, ai_proposals_json, ai_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            1, 52, meas_id, "Štěpán Skalka",
            "in_progress", filename, str(dest_file), 1,
            9.5, "A", tok, json.dumps(ai_proposals, ensure_ascii=False) if ai_proposals else None, "analyzed",
            now, now
        ))
        p_id = cur.lastrowid
        if meas_code == "06":
            primary_proto_id = p_id
            primary_share_tok = tok

            # Pre-seed realistic annotations and evaluation for Kalorimetrie
            sample_annots = [
                {
                    "type": "highlight",
                    "page": 1,
                    "rect": [120, 260, 480, 276],
                    "color": "#ef4444",
                    "comment": "Uveďte přesné jednotky u specifické tepelné kapacity [J/(kg.K)].",
                    "author": "Asistent"
                },
                {
                    "type": "note",
                    "page": 2,
                    "point": [470, 290],
                    "color": "#3b82f6",
                    "comment": "Graf chladnutí kalorimetru je zpracován velmi přehledně včetně fitování.",
                    "author": "Asistent"
                }
            ]
            cur.execute("""
            INSERT INTO annotations (protocol_id, annotations_json, updated_at)
            VALUES (?, ?, ?)
            """, (p_id, json.dumps(sample_annots, ensure_ascii=False), now))

            cur.execute("""
            INSERT INTO evaluations (
                protocol_id, vysledky_score, diskuze_score, format_score, chyby_score,
                total_points, grade, deductions_json, general_comment,
                raw_output_1, raw_output_2, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, 2.75, 2.75, 1.875, 2.0,
                9.375, "A",
                json.dumps([
                    {"category": "diskuze", "pts": 0.25, "reason": "Diskuze: Chybí detailnější rozbor tepelných ztrát do okolí během měření tepelné kapacity."},
                    {"category": "format", "pts": 0.125, "reason": "Formát: V rovnici (3) chybí čárka mezi vzorcem a navazujícím textem \", kde\"."}
                ], ensure_ascii=False),
                "Velmi pěkně a přehledně zpracovaný protokol. Grafy chladnutí jsou vzorné, drobná výtka pouze k chybějící čárce za vzorcem (3).",
                "Výsledky: 2.75 / 3, Diskuze: 2.75 / 3, Formát: 1.875 / 2, Chyby: 2.0 / 2, Celkem: 9.375 / 10, Známka: A",
                "Výsledky: 2.75 / 3\n-0.25b Diskuze: Chybí detailnější rozbor tepelných ztrát...\n\nCelkem bodů: 9.375 / 10, Známka: A\n\nSlovní hodnocení protokolu:\nVelmi pěkně a přehledně zpracovaný protokol.",
                now
            ))

    conn.commit()
    conn.close()
    return primary_proto_id, primary_share_tok

def run_media_generation():
    primary_proto_id, primary_share_tok = seed_database_with_test_protocols()
    server_proc = start_server()

    try:
        with sync_playwright() as p:
            print("Launching headless Chromium browser (1440x920 @ 1.25x scale)...")
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 920},
                device_scale_factor=1.25
            )
            page = context.new_page()

            # 1. Login flow
            print("Navigating to application and logging in as admin...")
            page.goto(SERVER_URL)
            page.wait_for_load_state("networkidle")

            if page.locator("#login-username").is_visible():
                page.fill("#login-username", "admin")
                page.fill("#login-password", "admin123")
                page.click("#login-modal button[type='submit']")
                page.wait_for_selector("#login-modal", state="hidden")
                page.wait_for_timeout(1000)

            page.evaluate("App.applyTheme('light')")
            page.wait_for_timeout(600)

            # Capture 1: Dashboard Overview
            print("Capturing 1: Dashboard Overview...")
            dashboard_img = DOCS_ASSETS_DIR / "dashboard_overview.png"
            page.screenshot(path=str(dashboard_img))
            shutil.copy(dashboard_img, DOCS_IMAGES_DIR / "dashboard_overview.png")

            # Capture 2: Upload Modal
            print("Capturing 2: Upload Modal...")
            page.evaluate("App.openUploadModal()")
            page.wait_for_selector("#upload-modal.active", state="visible")
            page.wait_for_timeout(500)
            upload_img = DOCS_ASSETS_DIR / "upload_modal.png"
            page.screenshot(path=str(upload_img))
            shutil.copy(upload_img, DOCS_IMAGES_DIR / "upload_modal.png")

            # Clip 1: Import Workflow Animation
            print("Recording Clip 1: Import flow...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap(4) # showing modal
                page.evaluate("document.getElementById('upload-student-name').value = 'Štěpán Skalka'")
                page.evaluate("document.getElementById('upload-measurement-select').value = '6'")
                page.evaluate("document.getElementById('autodetect-status-box').style.display = 'block'")
                page.evaluate("document.getElementById('autodetect-status-text').textContent = '✨ Autodetekováno: Štěpán Skalka, Úloha 6: Kalorimetrie'")
                cap(5)
                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_import.webp", DOCS_ASSETS_DIR / "clip_import.gif", fps=6, width=960)
                shutil.copy(DOCS_ASSETS_DIR / "clip_import.webp", DOCS_IMAGES_DIR / "clip_import.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_import.gif", DOCS_IMAGES_DIR / "clip_import.gif")

            page.evaluate("App.closeUploadModal()")
            page.wait_for_timeout(400)

            # Capture 3: Admin Settings - Database
            print("Capturing 3: Admin Settings - Database...")
            page.evaluate("App.openSettingsModal()")
            page.wait_for_selector("#settings-modal.active", state="visible")
            page.evaluate("App.showSettingsTab('database')")
            page.wait_for_timeout(1500)
            db_img = DOCS_ASSETS_DIR / "admin_settings_database.png"
            page.screenshot(path=str(db_img))
            shutil.copy(db_img, DOCS_IMAGES_DIR / "admin_settings_database.png")

            # Capture 4: Admin Settings - AI
            print("Capturing 4: Admin Settings - AI...")
            page.evaluate("App.showSettingsTab('ai')")
            page.wait_for_timeout(500)
            ai_img = DOCS_ASSETS_DIR / "admin_settings_ai.png"
            page.screenshot(path=str(ai_img))
            shutil.copy(ai_img, DOCS_IMAGES_DIR / "admin_settings_ai.png")

            # Capture 5: Admin Settings - Tasks
            print("Capturing 5: Admin Settings - Tasks...")
            page.evaluate("App.showSettingsTab('tasks')")
            page.wait_for_timeout(500)
            tasks_img = DOCS_ASSETS_DIR / "admin_settings_tasks.png"
            page.screenshot(path=str(tasks_img))
            shutil.copy(tasks_img, DOCS_IMAGES_DIR / "admin_settings_tasks.png")
            page.evaluate("App.closeSettingsModal()")
            page.wait_for_timeout(400)

            # Capture 6: PDF Studio Overview with Kalorimetrie.pdf
            print(f"Opening Protocol {primary_proto_id} (Štěpán Skalka - Kalorimetrie) in Studio...")
            page.evaluate(f"App.openStudio({primary_proto_id})")
            page.wait_for_selector("#view-studio", state="visible")
            page.wait_for_selector("#pdf-render-pane canvas", timeout=15000)
            page.wait_for_timeout(2500)

            print("Capturing 6: Studio Overview...")
            studio_img = DOCS_ASSETS_DIR / "studio_overview.png"
            page.screenshot(path=str(studio_img))
            shutil.copy(studio_img, DOCS_IMAGES_DIR / "studio_overview.png")

            # Capture 7: Studio AI Drawer
            print("Opening AI Assistant Drawer...")
            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_selector("#studio-ai-drawer", state="visible")
            page.wait_for_timeout(800)
            ai_drawer_img = DOCS_ASSETS_DIR / "studio_ai_drawer.png"
            page.screenshot(path=str(ai_drawer_img))
            shutil.copy(ai_drawer_img, DOCS_IMAGES_DIR / "studio_ai_drawer.png")

            # Clip 2: AI Assistant Proposal Approval Animation
            print("Recording Clip 2: AI Assistant flow...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap2(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap2(4)
                page.evaluate("document.querySelector('.ai-drawer-body')?.scrollBy({top: 100, behavior: 'smooth'})")
                cap2(4)
                appr_btn = page.locator("button:has-text('✓ Aplikovat do PDF')").first
                if appr_btn.is_visible():
                    appr_btn.hover()
                    cap2(3)
                    appr_btn.click()
                    cap2(6)
                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_ai_assistant.webp", DOCS_ASSETS_DIR / "clip_ai_assistant.gif", fps=7, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_ai_assistant.webp", DOCS_IMAGES_DIR / "clip_ai_assistant.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_ai_assistant.gif", DOCS_IMAGES_DIR / "clip_ai_assistant.gif")

            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_timeout(400)

            # Clip 3: Annotations Drawing (Pen & Rectangle)
            print("Recording Clip 3: Annotations flow...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap3(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap3(3)
                page.evaluate("PDFStudio.setTool('rect')")
                cap3(2)

                canvas_box = page.locator("#pdf-render-pane canvas").first.bounding_box()
                if canvas_box:
                    sx = canvas_box["x"] + 160
                    sy = canvas_box["y"] + 320
                    page.mouse.move(sx, sy)
                    page.mouse.down()
                    for step in range(1, 6):
                        page.mouse.move(sx + (step * 35), sy + (step * 18))
                        cap3(1)
                    page.mouse.up()
                    cap3(4)

                page.evaluate("PDFStudio.setTool('pan')")
                cap3(2)
                if canvas_box:
                    page.mouse.click(canvas_box["x"] + 220, canvas_box["y"] + 350)
                    cap3(5) # show handles & delete action

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_annotations.webp", DOCS_ASSETS_DIR / "clip_annotations.gif", fps=7, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_annotations.webp", DOCS_IMAGES_DIR / "clip_annotations.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_annotations.gif", DOCS_IMAGES_DIR / "clip_annotations.gif")

            # Clip 4: Grading Dock & General Comment
            print("Recording Clip 4: Grading dock and general comment...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap4(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                page.evaluate("App.toggleGradingDock()")
                cap4(4)
                page.evaluate("document.querySelector('.grading-dock-body')?.scrollBy({top: 140, behavior: 'smooth'})")
                cap4(3)

                # Focus general comment and add text
                g_input = page.locator("#general-comment-input")
                if g_input.is_visible():
                    g_input.click()
                    cap4(2)
                    g_input.fill("Výborně zpracovaný protokol. Grafy chladnutí jsou vzorné, drobná výtka pouze k chybějící čárce za vzorcem.")
                    cap4(5)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_grading.webp", DOCS_ASSETS_DIR / "clip_grading.gif", fps=7, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_grading.webp", DOCS_IMAGES_DIR / "clip_grading.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_grading.gif", DOCS_IMAGES_DIR / "clip_grading.gif")

            # Clip 5: Save, Dokončit & Student View
            print("Recording Clip 5: Save & Student View flow...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap5(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                fin_btn = page.locator(".btn-finish-action")
                if fin_btn.is_visible():
                    fin_btn.hover()
                    cap5(3)
                    fin_btn.click()
                    cap5(5)

                # Navigate to student view
                student_url = f"{SERVER_URL}/v/{primary_share_tok}"
                print(f"Opening Student View at {student_url}...")
                page.goto(student_url)
                page.wait_for_selector("#pdf-scroll-container canvas", timeout=15000)
                page.wait_for_timeout(2000)
                cap5(6)

                # Scroll down feedback notes
                page.evaluate("document.querySelector('.sidebar-scroll')?.scrollBy({top: 150, behavior: 'smooth'})")
                cap5(4)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_export.webp", DOCS_ASSETS_DIR / "clip_export.gif", fps=7, width=1050)
                shutil.copy(DOCS_ASSETS_DIR / "clip_export.webp", DOCS_IMAGES_DIR / "clip_export.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_export.gif", DOCS_IMAGES_DIR / "clip_export.gif")

            # Capture Student View screenshot
            print("Capturing Student View static screenshot...")
            student_view_img = DOCS_ASSETS_DIR / "student_view.png"
            page.screenshot(path=str(student_view_img))
            shutil.copy(student_view_img, DOCS_IMAGES_DIR / "student_view.png")

            # Generate full studio_workflow.webp and studio_workflow.gif
            print("Recording comprehensive Studio Workflow walkthrough...")
            page.goto(f"{SERVER_URL}")
            page.wait_for_selector("#nav-btn-studio", state="visible")
            page.evaluate(f"App.openStudio({primary_proto_id})")
            page.wait_for_selector("#pdf-render-pane canvas", timeout=15000)
            page.wait_for_timeout(1500)

            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap_all(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                # 1. Inspecting protocol
                cap_all(4)

                # 2. Draw shape
                page.evaluate("PDFStudio.setTool('rect')")
                cap_all(2)
                c_box = page.locator("#pdf-render-pane canvas").first.bounding_box()
                if c_box:
                    px = c_box["x"] + 150
                    py = c_box["y"] + 280
                    page.mouse.move(px, py)
                    page.mouse.down()
                    for step in range(1, 5):
                        page.mouse.move(px + (step * 40), py + (step * 20))
                        cap_all(1)
                    page.mouse.up()
                    cap_all(4)

                # 3. AI Drawer
                page.evaluate("App.toggleAIDrawer()")
                cap_all(4)
                page.evaluate("document.querySelector('.ai-drawer-body')?.scrollBy({top: 90, behavior: 'smooth'})")
                cap_all(3)
                ab = page.locator("button:has-text('✓ Aplikovat do PDF')").first
                if ab.is_visible():
                    ab.click()
                    cap_all(5)
                page.evaluate("App.toggleAIDrawer()")
                cap_all(3)

                # 4. Grading Dock
                page.evaluate("App.toggleGradingDock()")
                cap_all(4)
                page.evaluate("document.querySelector('.grading-dock-body')?.scrollBy({top: 130, behavior: 'smooth'})")
                cap_all(3)

                # 5. Finish
                fb = page.locator(".btn-finish-action")
                if fb.is_visible():
                    fb.hover()
                    cap_all(2)
                    fb.click()
                    cap_all(5)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "studio_workflow.webp", DOCS_ASSETS_DIR / "studio_workflow.gif", fps=8, width=1080)
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.webp", DOCS_IMAGES_DIR / "studio_workflow.webp")
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.gif", DOCS_IMAGES_DIR / "studio_workflow.gif")

            print("\nSuccessfully generated all documentation media and clips!")
            browser.close()

    finally:
        if server_proc:
            print("Stopping uvicorn server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    run_media_generation()
