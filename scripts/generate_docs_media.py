#!/usr/bin/env python3
"""
Automated media generation script for Praktika Evaluation Studio v2.13.0.
Captures real application screenshots and generates buttery smooth animated walkthroughs (WebP & GIF)
at 18 FPS with a high-contrast enlarged virtual mouse pointer and click-ripple animations.
Uses Playwright and ffmpeg directly against the running application.
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

def find_free_port() -> int:
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

SERVER_PORT = find_free_port()
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}"

# Global cursor tracking
cursor_state = {"x": 500, "y": 400}

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
        cwd=str(BASE_DIR)
    )
    for _ in range(30):
        time.sleep(0.5)
        if proc.poll() is not None:
            raise RuntimeError(f"Uvicorn server exited prematurely with code {proc.returncode}")
        if is_server_running():
            print("Server successfully started and healthy!")
            return proc
    raise RuntimeError("Failed to start uvicorn server within timeout")

def compile_frames_to_animation(frame_dir: Path, out_webp: Path, out_gif: Path, fps: int = 18, width: int = 1080):
    print(f"Compiling frames to animated WebP: {out_webp.name} @ {fps} fps...")
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
    print(f"Compiling frames to palette-optimized GIF: {out_gif.name} @ {fps} fps...")
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
        "-lavfi", f"scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3",
        str(out_gif)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"GIF generated: {out_gif.name} ({out_gif.stat().st_size // 1024} KB)")

def inject_virtual_cursor(page):
    page.evaluate(f"""
      if (!document.getElementById('virtual-mouse-cursor')) {{
        const c = document.createElement('div');
        c.id = 'virtual-mouse-cursor';
        c.style.position = 'fixed';
        c.style.top = '{cursor_state["y"]}px';
        c.style.left = '{cursor_state["x"]}px';
        c.style.width = '32px';
        c.style.height = '32px';
        c.style.zIndex = '999999';
        c.style.pointerEvents = 'none';
        c.style.transform = 'translate(0px, 0px)';
        c.innerHTML = `
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" style="filter: drop-shadow(0 2px 5px rgba(0,0,0,0.45));">
            <path d="M4 3L11 20L14 13L21 10L4 3Z" fill="#ffffff" stroke="#0f172a" stroke-width="2" stroke-linejoin="round"/>
          </svg>
          <div id="virtual-cursor-ripple" style="
            position: absolute;
            top: -4px;
            left: -4px;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: 3px solid #2563eb;
            background: rgba(37, 99, 235, 0.4);
            opacity: 0;
            transform: scale(0.3);
            pointer-events: none;
          "></div>
        `;
        document.body.appendChild(c);
      }}
    """)

def move_mouse_smooth(page, target_x: float, target_y: float, steps: int = 6, capture_fn = None):
    inject_virtual_cursor(page)
    start_x = cursor_state["x"]
    start_y = cursor_state["y"]

    for i in range(1, steps + 1):
        cur_x = start_x + (target_x - start_x) * (i / steps)
        cur_y = start_y + (target_y - start_y) * (i / steps)
        cursor_state["x"] = cur_x
        cursor_state["y"] = cur_y

        page.evaluate(f"""
          const c = document.getElementById('virtual-mouse-cursor');
          if (c) {{
            c.style.left = '{cur_x}px';
            c.style.top = '{cur_y}px';
          }}
        """)
        page.mouse.move(cur_x, cur_y)
        if capture_fn:
            capture_fn(1)

def click_mouse(page, x: float = None, y: float = None, capture_fn = None):
    inject_virtual_cursor(page)
    if x is not None and y is not None:
        move_mouse_smooth(page, x, y, steps=6, capture_fn=capture_fn)

    # Click ripple animation
    page.evaluate("""
      const rip = document.getElementById('virtual-cursor-ripple');
      if (rip) {
        rip.style.transition = 'none';
        rip.style.opacity = '1';
        rip.style.transform = 'scale(0.3)';
        setTimeout(() => {
          rip.style.transition = 'transform 0.22s ease-out, opacity 0.22s ease-out';
          rip.style.transform = 'scale(2.2)';
          rip.style.opacity = '0';
        }, 10);
      }
    """)
    if capture_fn:
        capture_fn(2)

    page.mouse.down()
    if capture_fn:
        capture_fn(2)
    page.mouse.up()
    if capture_fn:
        capture_fn(3)

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
            inject_virtual_cursor(page)

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

            # ----------------------------------------------------
            # Clip 1: Import Workflow Animation (18 FPS)
            # ----------------------------------------------------
            print("Recording Clip 1: Import flow (18 FPS with visible cursor)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap1(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap1(6)
                # Move to student input
                move_mouse_smooth(page, 720, 360, steps=8, capture_fn=cap1)
                click_mouse(page, 720, 360, capture_fn=cap1)
                page.evaluate("document.getElementById('upload-student-name').value = 'Štěpán Skalka'")
                cap1(6)

                # Move to task select
                move_mouse_smooth(page, 720, 440, steps=8, capture_fn=cap1)
                click_mouse(page, 720, 440, capture_fn=cap1)
                page.evaluate("document.getElementById('upload-measurement-select').value = '6'")
                page.evaluate("document.getElementById('autodetect-status-box').style.display = 'block'")
                page.evaluate("document.getElementById('autodetect-status-text').textContent = '✨ Autodetekováno: Štěpán Skalka, Úloha 6: Kalorimetrie'")
                cap1(10)

                # Move to confirm button
                move_mouse_smooth(page, 790, 580, steps=8, capture_fn=cap1)
                click_mouse(page, 790, 580, capture_fn=cap1)
                cap1(8)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_import.webp", DOCS_ASSETS_DIR / "clip_import.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_import.webp", DOCS_IMAGES_DIR / "clip_import.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_import.gif", DOCS_IMAGES_DIR / "clip_import.gif")

            page.evaluate("App.closeUploadModal()")
            page.wait_for_timeout(400)

            # ----------------------------------------------------
            # Clip 2: Batch Operations & Multi-Select (18 FPS) - NEW
            # ----------------------------------------------------
            print("Recording Clip 2: Batch operations flow (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap2(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap2(6)
                # Check bulk checkboxes
                checkboxes = page.locator("input.protocol-checkbox")
                c_count = checkboxes.count()
                if c_count > 0:
                    box1 = checkboxes.nth(0).bounding_box()
                    if box1:
                        move_mouse_smooth(page, box1["x"] + 8, box1["y"] + 8, steps=8, capture_fn=cap2)
                        click_mouse(page, box1["x"] + 8, box1["y"] + 8, capture_fn=cap2)
                        checkboxes.nth(0).check()
                        page.evaluate("App.handleProtocolCheckboxChange()")
                        cap2(6)

                    if c_count > 1:
                        box2 = checkboxes.nth(1).bounding_box()
                        if box2:
                            move_mouse_smooth(page, box2["x"] + 8, box2["y"] + 8, steps=8, capture_fn=cap2)
                            click_mouse(page, box2["x"] + 8, box2["y"] + 8, capture_fn=cap2)
                            checkboxes.nth(1).check()
                            page.evaluate("App.handleProtocolCheckboxChange()")
                            cap2(8)

                # Move to batch edit button
                batch_btn = page.locator("button:has-text('✎ Upravit vybrané')")
                if batch_btn.is_visible():
                    bbox = batch_btn.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, steps=8, capture_fn=cap2)
                        click_mouse(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, capture_fn=cap2)
                        cap2(14)

                page.evaluate("App.closeBulkEditModal()")
                page.evaluate("App.clearProtocolSelection()")
                cap2(4)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_batch_ops.webp", DOCS_ASSETS_DIR / "clip_batch_ops.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_batch_ops.webp", DOCS_IMAGES_DIR / "clip_batch_ops.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_batch_ops.gif", DOCS_IMAGES_DIR / "clip_batch_ops.gif")

            # ----------------------------------------------------
            # Admin Settings Captures & Clip (Tasks, AI, Database)
            # ----------------------------------------------------
            print("Capturing Admin Settings (Database, AI, Tasks)...")
            page.evaluate("App.openSettingsModal()")
            page.wait_for_selector("#settings-modal.active", state="visible")

            page.evaluate("App.showSettingsTab('tasks')")
            page.wait_for_timeout(600)
            tasks_img = DOCS_ASSETS_DIR / "admin_settings_tasks.png"
            page.screenshot(path=str(tasks_img))
            shutil.copy(tasks_img, DOCS_IMAGES_DIR / "admin_settings_tasks.png")

            page.evaluate("App.showSettingsTab('ai')")
            page.wait_for_timeout(600)
            ai_img = DOCS_ASSETS_DIR / "admin_settings_ai.png"
            page.screenshot(path=str(ai_img))
            shutil.copy(ai_img, DOCS_IMAGES_DIR / "admin_settings_ai.png")

            page.evaluate("App.showSettingsTab('database')")
            page.wait_for_timeout(1500)
            db_img = DOCS_ASSETS_DIR / "admin_settings_database.png"
            page.screenshot(path=str(db_img))
            shutil.copy(db_img, DOCS_IMAGES_DIR / "admin_settings_database.png")

            # Clip 8: Admin Settings Walkthrough - NEW
            print("Recording Clip 8: Admin Settings flow (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap8(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap8(6)
                # Switch to Tasks tab
                move_mouse_smooth(page, 400, 220, steps=8, capture_fn=cap8)
                click_mouse(page, 400, 220, capture_fn=cap8)
                page.evaluate("App.showSettingsTab('tasks')")
                cap8(10)

                # Switch to AI tab
                move_mouse_smooth(page, 490, 220, steps=8, capture_fn=cap8)
                click_mouse(page, 490, 220, capture_fn=cap8)
                page.evaluate("App.showSettingsTab('ai')")
                cap8(10)

                # Switch to Database tab
                move_mouse_smooth(page, 660, 220, steps=8, capture_fn=cap8)
                click_mouse(page, 660, 220, capture_fn=cap8)
                page.evaluate("App.showSettingsTab('database')")
                cap8(10)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_admin_settings.webp", DOCS_ASSETS_DIR / "clip_admin_settings.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_admin_settings.webp", DOCS_IMAGES_DIR / "clip_admin_settings.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_admin_settings.gif", DOCS_IMAGES_DIR / "clip_admin_settings.gif")

            page.evaluate("App.closeSettingsModal()")
            page.wait_for_timeout(400)

            # ----------------------------------------------------
            # Open Studio with Štěpán Skalka - Kalorimetrie
            # ----------------------------------------------------
            print(f"Opening Protocol {primary_proto_id} (Štěpán Skalka - Kalorimetrie) in Studio...")
            page.evaluate(f"App.openStudio({primary_proto_id})")
            page.wait_for_selector("#view-studio", state="visible")
            page.wait_for_selector("#pdf-render-pane canvas", timeout=15000)
            page.wait_for_timeout(2500)
            inject_virtual_cursor(page)

            print("Capturing Studio Overview...")
            studio_img = DOCS_ASSETS_DIR / "studio_overview.png"
            page.screenshot(path=str(studio_img))
            shutil.copy(studio_img, DOCS_IMAGES_DIR / "studio_overview.png")

            # Open AI Assistant Drawer
            print("Opening AI Assistant Drawer...")
            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_selector("#studio-ai-drawer", state="visible")
            page.wait_for_timeout(800)
            inject_virtual_cursor(page)

            ai_drawer_img = DOCS_ASSETS_DIR / "studio_ai_drawer.png"
            page.screenshot(path=str(ai_drawer_img))
            shutil.copy(ai_drawer_img, DOCS_IMAGES_DIR / "studio_ai_drawer.png")

            # ----------------------------------------------------
            # Clip 3: AI Assistant Proposal Approval (18 FPS)
            # ----------------------------------------------------
            print("Recording Clip 3: AI Assistant flow (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap3(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap3(6)
                # Scroll in AI findings
                page.evaluate("document.querySelector('.ai-drawer-body')?.scrollBy({top: 120, behavior: 'smooth'})")
                cap3(8)

                # Move cursor to proposal button
                appr_btn = page.locator("button:has-text('✓ Aplikovat do PDF')").first
                if appr_btn.is_visible():
                    bbox = appr_btn.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, steps=8, capture_fn=cap3)
                        click_mouse(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, capture_fn=cap3)
                        cap3(12)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_ai_assistant.webp", DOCS_ASSETS_DIR / "clip_ai_assistant.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_ai_assistant.webp", DOCS_IMAGES_DIR / "clip_ai_assistant.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_ai_assistant.gif", DOCS_IMAGES_DIR / "clip_ai_assistant.gif")

            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_timeout(400)

            # ----------------------------------------------------
            # Clip 4: Annotations & Real Corrections (18 FPS)
            # Realistic: Highlight missing comma in formula + Arrow to table
            # ----------------------------------------------------
            print("Recording Clip 4: Realistic Annotations flow (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap4(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap4(6)
                # Move to Highlight tool
                hl_btn = page.locator("#tool-highlight")
                if hl_btn.is_visible():
                    bbox = hl_btn.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, steps=8, capture_fn=cap4)
                        click_mouse(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, capture_fn=cap4)
                        page.evaluate("PDFStudio.setTool('highlight')")
                        cap4(6)

                # Highlight on equation text
                canvas_box = page.locator("#pdf-render-pane canvas").first.bounding_box()
                if canvas_box:
                    hx = canvas_box["x"] + 240
                    hy = canvas_box["y"] + 280
                    move_mouse_smooth(page, hx, hy, steps=8, capture_fn=cap4)
                    page.mouse.down()
                    for step in range(1, 8):
                        page.mouse.move(hx + (step * 25), hy)
                        cursor_state["x"] = hx + (step * 25)
                        cursor_state["y"] = hy
                        page.evaluate(f"const c = document.getElementById('virtual-mouse-cursor'); if(c) {{ c.style.left='{cursor_state['x']}px'; c.style.top='{cursor_state['y']}px'; }}")
                        cap4(1)
                    page.mouse.up()
                    cap4(8)

                # Move to Arrow tool
                arrow_btn = page.locator("#tool-arrow")
                if arrow_btn.is_visible():
                    abox = arrow_btn.bounding_box()
                    if abox:
                        move_mouse_smooth(page, abox["x"] + abox["width"]/2, abox["y"] + abox["height"]/2, steps=8, capture_fn=cap4)
                        click_mouse(page, abox["x"] + abox["width"]/2, abox["y"] + abox["height"]/2, capture_fn=cap4)
                        page.evaluate("PDFStudio.setTool('arrow')")
                        cap4(6)

                # Draw directional arrow pointing to table
                if canvas_box:
                    ax1 = canvas_box["x"] + 180
                    ay1 = canvas_box["y"] + 360
                    ax2 = canvas_box["x"] + 260
                    ay2 = canvas_box["y"] + 410
                    move_mouse_smooth(page, ax1, ay1, steps=6, capture_fn=cap4)
                    page.mouse.down()
                    for step in range(1, 6):
                        cx = ax1 + ((ax2 - ax1) * (step / 5))
                        cy = ay1 + ((ay2 - ay1) * (step / 5))
                        cursor_state["x"] = cx
                        cursor_state["y"] = cy
                        page.evaluate(f"const c = document.getElementById('virtual-mouse-cursor'); if(c) {{ c.style.left='{cx}px'; c.style.top='{cy}px'; }}")
                        page.mouse.move(cx, cy)
                        cap4(1)
                    page.mouse.up()
                    cap4(10)

                # Switch back to Pan tool
                page.evaluate("PDFStudio.setTool('pan')")
                cap4(4)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_annotations.webp", DOCS_ASSETS_DIR / "clip_annotations.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_annotations.webp", DOCS_IMAGES_DIR / "clip_annotations.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_annotations.gif", DOCS_IMAGES_DIR / "clip_annotations.gif")

            # ----------------------------------------------------
            # Clip 5: Grading Dock & General Comment (18 FPS)
            # ----------------------------------------------------
            print("Recording Clip 5: Grading dock & General comment (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap5(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                page.evaluate("App.toggleGradingDock()")
                cap5(6)

                # Scroll in grading dock
                page.evaluate("document.querySelector('.grading-dock-body')?.scrollBy({top: 130, behavior: 'smooth'})")
                cap5(8)

                # Move to reason input for diskuze
                reason_input = page.locator("#reason-input-diskuze")
                if reason_input.is_visible():
                    rbox = reason_input.bounding_box()
                    if rbox:
                        move_mouse_smooth(page, rbox["x"] + 50, rbox["y"] + 15, steps=8, capture_fn=cap5)
                        click_mouse(page, rbox["x"] + 50, rbox["y"] + 15, capture_fn=cap5)
                        reason_input.fill("Chybí detailnější rozbor tepelných ztrát do okolí během měření.")
                        cap5(8)
                        add_btn = page.locator("button:has-text('+ Odečíst')").first
                        if add_btn.is_visible():
                            abox = add_btn.bounding_box()
                            if abox:
                                move_mouse_smooth(page, abox["x"] + abox["width"]/2, abox["y"] + abox["height"]/2, steps=6, capture_fn=cap5)
                                click_mouse(page, abox["x"] + abox["width"]/2, abox["y"] + abox["height"]/2, capture_fn=cap5)
                                cap5(8)

                # Move to general comment input
                g_input = page.locator("#general-comment-input")
                if g_input.is_visible():
                    gbox = g_input.bounding_box()
                    if gbox:
                        move_mouse_smooth(page, gbox["x"] + 40, gbox["y"] + 25, steps=8, capture_fn=cap5)
                        click_mouse(page, gbox["x"] + 40, gbox["y"] + 25, capture_fn=cap5)
                        g_input.fill("Velmi pěkně a přehledně zpracovaný protokol. Grafy chladnutí jsou vzorné, drobná výtka pouze k chybějící čárce za vzorcem (3).")
                        cap5(12)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_grading.webp", DOCS_ASSETS_DIR / "clip_grading.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_grading.webp", DOCS_IMAGES_DIR / "clip_grading.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_grading.gif", DOCS_IMAGES_DIR / "clip_grading.gif")

            # ----------------------------------------------------
            # Clip 6: Save & Dokončit with Indicator (18 FPS)
            # ----------------------------------------------------
            print("Recording Clip 6: Save and Finish action (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap6(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap6(6)
                # Click finish button
                fin_btn = page.locator(".btn-finish-action")
                if fin_btn.is_visible():
                    bbox = fin_btn.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, steps=8, capture_fn=cap6)
                        click_mouse(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, capture_fn=cap6)
                        cap6(10)

                # Show save indicator lighting up in bottom-left
                page.evaluate("App.updateAutosaveIndicator('saved', '10:45')")
                cap6(8)

                # Click copy for Moodle
                moodle_btn = page.locator("button:has-text('📋 Kopírovat pro Moodle')")
                if moodle_btn.is_visible():
                    mbox = moodle_btn.bounding_box()
                    if mbox:
                        move_mouse_smooth(page, mbox["x"] + mbox["width"]/2, mbox["y"] + mbox["height"]/2, steps=8, capture_fn=cap6)
                        click_mouse(page, mbox["x"] + mbox["width"]/2, mbox["y"] + mbox["height"]/2, capture_fn=cap6)
                        cap6(10)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_export.webp", DOCS_ASSETS_DIR / "clip_export.gif", fps=18, width=1000)
                shutil.copy(DOCS_ASSETS_DIR / "clip_export.webp", DOCS_IMAGES_DIR / "clip_export.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_export.gif", DOCS_IMAGES_DIR / "clip_export.gif")

            # ----------------------------------------------------
            # Clip 7: Interactive Student View & Dark Mode (18 FPS) - NEW
            # ----------------------------------------------------
            student_url = f"{SERVER_URL}/v/{primary_share_tok}"
            print(f"Navigating to Student View: {student_url}...")
            page.goto(student_url)
            page.wait_for_selector("#pdf-scroll-container canvas", timeout=15000)
            page.wait_for_timeout(2000)
            inject_virtual_cursor(page)

            # Static screenshot of student view
            student_img = DOCS_ASSETS_DIR / "student_view.png"
            page.screenshot(path=str(student_img))
            shutil.copy(student_img, DOCS_IMAGES_DIR / "student_view.png")

            print("Recording Clip 7: Student View & Dark Mode (18 FPS)...")
            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def cap7(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                cap7(6)
                # Hover over first highlight overlay to display floating tooltip
                hl_overlay = page.locator(".acrobat-highlight-overlay").first
                if hl_overlay.is_visible():
                    bbox = hl_overlay.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + 40, bbox["y"] + 8, steps=8, capture_fn=cap7)
                        cap7(10) # showing tooltip

                # Click on note in sidebar
                note_card = page.locator(".note-card").first
                if note_card.is_visible():
                    nbox = note_card.bounding_box()
                    if nbox:
                        move_mouse_smooth(page, nbox["x"] + 50, nbox["y"] + 20, steps=8, capture_fn=cap7)
                        click_mouse(page, nbox["x"] + 50, nbox["y"] + 20, capture_fn=cap7)
                        cap7(10) # scrolled & pulsed

                # Move cursor to Dark Mode toggle button in header
                theme_btn = page.locator("#theme-toggle")
                if theme_btn.is_visible():
                    tbox = theme_btn.bounding_box()
                    if tbox:
                        move_mouse_smooth(page, tbox["x"] + tbox["width"]/2, tbox["y"] + tbox["height"]/2, steps=8, capture_fn=cap7)
                        click_mouse(page, tbox["x"] + tbox["width"]/2, tbox["y"] + tbox["height"]/2, capture_fn=cap7)
                        page.evaluate("toggleTheme()")
                        cap7(14) # showing dark mode in action!

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "clip_student_view.webp", DOCS_ASSETS_DIR / "clip_student_view.gif", fps=18, width=1050)
                shutil.copy(DOCS_ASSETS_DIR / "clip_student_view.webp", DOCS_IMAGES_DIR / "clip_student_view.webp")
                shutil.copy(DOCS_ASSETS_DIR / "clip_student_view.gif", DOCS_IMAGES_DIR / "clip_student_view.gif")

            # ----------------------------------------------------
            # Studio Workflow Animation (Combined Showcase @ 18 FPS)
            # ----------------------------------------------------
            print("Compiling Studio Workflow showcase (18 FPS)...")
            # Navigate back to Studio
            page.goto(f"{SERVER_URL}")
            page.wait_for_load_state("networkidle")
            page.evaluate(f"App.openStudio({primary_proto_id})")
            page.wait_for_selector("#pdf-render-pane canvas", timeout=15000)
            page.wait_for_timeout(1500)
            inject_virtual_cursor(page)

            with tempfile.TemporaryDirectory() as temp_dir:
                fdir = Path(temp_dir)
                fidx = 0
                def capw(rep=1):
                    nonlocal fidx
                    for _ in range(rep):
                        page.screenshot(path=str(fdir / f"frame_{fidx:04d}.png"))
                        fidx += 1

                capw(6)
                # Open AI Drawer
                page.evaluate("App.toggleAIDrawer()")
                capw(8)
                page.evaluate("document.querySelector('.ai-drawer-body')?.scrollBy({top: 80, behavior: 'smooth'})")
                capw(6)
                page.evaluate("App.toggleAIDrawer()")
                capw(4)

                # Open Grading Dock
                page.evaluate("App.toggleGradingDock()")
                capw(8)
                page.evaluate("document.querySelector('.grading-dock-body')?.scrollBy({top: 100, behavior: 'smooth'})")
                capw(8)

                # Finish button click
                fin_btn = page.locator(".btn-finish-action")
                if fin_btn.is_visible():
                    bbox = fin_btn.bounding_box()
                    if bbox:
                        move_mouse_smooth(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, steps=6, capture_fn=capw)
                        click_mouse(page, bbox["x"] + bbox["width"]/2, bbox["y"] + bbox["height"]/2, capture_fn=capw)
                        capw(8)

                compile_frames_to_animation(fdir, DOCS_ASSETS_DIR / "studio_workflow.webp", DOCS_ASSETS_DIR / "studio_workflow.gif", fps=18, width=1050)
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.webp", DOCS_IMAGES_DIR / "studio_workflow.webp")
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.gif", DOCS_IMAGES_DIR / "studio_workflow.gif")

            browser.close()
            print("\nAll media generation completed successfully at 18 FPS!")

    finally:
        if server_proc:
            print("Terminating background uvicorn server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    run_media_generation()
