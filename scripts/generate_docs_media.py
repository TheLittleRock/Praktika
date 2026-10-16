#!/usr/bin/env python3
"""
Automated media generation script for Praktika Evaluation Studio v2.10.0.
Captures real, sharp application screenshots and generates smooth animated walkthroughs (WebP & GIF)
using Playwright and ffmpeg directly against the running application.
"""

import os
import sys
import time
import shutil
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
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

def compile_frames_to_animation(frame_dir: Path, out_webp: Path, out_gif: Path, fps: int = 8, width: int = 1200):
    print(f"Compiling frames to animated WebP: {out_webp}...")
    # 1. High quality WebP
    cmd_webp = [
        "ffmpeg", "-y", "-r", str(fps),
        "-i", str(frame_dir / "frame_%04d.png"),
        "-vf", f"scale={width}:-1:flags=lanczos",
        "-vcodec", "libwebp", "-lossless", "0", "-qscale", "85",
        "-preset", "picture", "-loop", "0",
        str(out_webp)
    ]
    subprocess.run(cmd_webp, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"WebP animation generated ({out_webp.stat().st_size // 1024} KB)")

    # 2. Optimized GIF with two-pass palettegen
    print(f"Compiling frames to palette-optimized GIF: {out_gif}...")
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
        "-lavfi", f"scale={width}:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5",
        str(out_gif)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"GIF animation generated ({out_gif.stat().st_size // 1024} KB)")

def run_media_generation():
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

            # Check if login form is present
            if page.locator("#login-username").is_visible():
                page.fill("#login-username", "admin")
                page.fill("#login-password", "admin123")
                page.click("#login-modal button[type='submit']")
                page.wait_for_selector("#login-modal", state="hidden")
                page.wait_for_timeout(1000)

            # Ensure default theme is active
            page.evaluate("App.applyTheme('light')")
            page.wait_for_timeout(500)

            # Capture 1: Dashboard Overview
            print("Capturing 1: Dashboard Overview...")
            dashboard_img = DOCS_ASSETS_DIR / "dashboard_overview.png"
            page.screenshot(path=str(dashboard_img), full_page=False)
            shutil.copy(dashboard_img, DOCS_IMAGES_DIR / "dashboard_overview.png")

            # Capture 2: Upload Modal
            print("Capturing 2: Upload Modal...")
            page.evaluate("App.openUploadModal()")
            page.wait_for_selector("#upload-modal.active", state="visible", timeout=4000)
            page.wait_for_timeout(400)
            upload_img = DOCS_ASSETS_DIR / "upload_modal.png"
            page.screenshot(path=str(upload_img))
            shutil.copy(upload_img, DOCS_IMAGES_DIR / "upload_modal.png")
            page.evaluate("App.closeUploadModal()")
            page.wait_for_timeout(300)

            # Capture 3: Admin Settings - Database
            print("Capturing 3: Admin Settings - Database & Backups...")
            page.evaluate("App.openSettingsModal()")
            page.wait_for_selector("#settings-modal.active", state="visible")
            page.evaluate("App.showSettingsTab('database')")
            page.wait_for_timeout(1500) # wait for stats to load
            db_img = DOCS_ASSETS_DIR / "admin_settings_database.png"
            page.screenshot(path=str(db_img))
            shutil.copy(db_img, DOCS_IMAGES_DIR / "admin_settings_database.png")

            # Capture 4: Admin Settings - AI Configuration
            print("Capturing 4: Admin Settings - AI Assistant...")
            page.evaluate("App.showSettingsTab('ai')")
            page.wait_for_timeout(500)
            ai_img = DOCS_ASSETS_DIR / "admin_settings_ai.png"
            page.screenshot(path=str(ai_img))
            shutil.copy(ai_img, DOCS_IMAGES_DIR / "admin_settings_ai.png")

            # Capture 5: Admin Settings - Lab Tasks Rubrics
            print("Capturing 5: Admin Settings - Lab Tasks...")
            page.evaluate("App.showSettingsTab('tasks')")
            page.wait_for_timeout(500)
            tasks_img = DOCS_ASSETS_DIR / "admin_settings_tasks.png"
            page.screenshot(path=str(tasks_img))
            shutil.copy(tasks_img, DOCS_IMAGES_DIR / "admin_settings_tasks.png")
            page.evaluate("App.closeSettingsModal()")
            page.wait_for_timeout(400)

            # Capture 6: PDF Studio Overview
            print("Opening Protocol 107 in PDF Studio...")
            page.evaluate("App.openStudio(107)")
            page.wait_for_selector("#view-studio", state="visible")
            page.wait_for_selector("#pdf-render-pane canvas", timeout=15000)
            page.wait_for_timeout(2500) # wait for render and annotations

            print("Capturing 6: PDF Studio Overview...")
            studio_img = DOCS_ASSETS_DIR / "studio_overview.png"
            page.screenshot(path=str(studio_img))
            shutil.copy(studio_img, DOCS_IMAGES_DIR / "studio_overview.png")

            # Capture 7: AI Assistant Drawer
            print("Opening AI Assistant Drawer...")
            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_selector("#studio-ai-drawer", state="visible")
            page.wait_for_timeout(800)
            ai_drawer_img = DOCS_ASSETS_DIR / "studio_ai_drawer.png"
            page.screenshot(path=str(ai_drawer_img))
            shutil.copy(ai_drawer_img, DOCS_IMAGES_DIR / "studio_ai_drawer.png")

            # Close AI drawer before interactive sequence
            page.evaluate("App.toggleAIDrawer()")
            page.wait_for_timeout(400)

            # Capture 8: Recording Real Interactive Studio Walkthrough (WebP & GIF)
            print("Recording interactive frames for animated walkthrough...")
            with tempfile.TemporaryDirectory() as temp_dir:
                frame_dir = Path(temp_dir)
                frame_idx = 0

                def capture_frame(repeat=1):
                    nonlocal frame_idx
                    for _ in range(repeat):
                        page.screenshot(path=str(frame_dir / f"frame_{frame_idx:04d}.png"))
                        frame_idx += 1

                # Frame 0-5: Viewing protocol
                capture_frame(5)

                # Frame 6-12: Select Rectangle tool and draw on page
                print(" -> Drawing rectangle on PDF...")
                page.evaluate("PDFStudio.setTool('rect')")
                capture_frame(3)

                # Simulate drawing rectangle on canvas
                canvas_box = page.locator("#pdf-render-pane canvas").first.bounding_box()
                if canvas_box:
                    start_x = canvas_box["x"] + 180
                    start_y = canvas_box["y"] + 240
                    page.mouse.move(start_x, start_y)
                    page.mouse.down()
                    for step in range(1, 6):
                        page.mouse.move(start_x + (step * 38), start_y + (step * 22))
                        capture_frame(1)
                    page.mouse.up()
                    capture_frame(5)

                # Frame 13-18: Switch to Pan tool, select shape, show handles & trash button
                print(" -> Selecting shape with selection box and trash button...")
                page.evaluate("PDFStudio.setTool('pan')")
                capture_frame(2)
                if canvas_box:
                    page.mouse.click(canvas_box["x"] + 240, canvas_box["y"] + 280)
                    capture_frame(6)

                # Frame 19-28: Open AI Drawer and browse proposals
                print(" -> Interacting with AI drawer proposals...")
                page.evaluate("App.toggleAIDrawer()")
                capture_frame(4)

                # Scroll inside AI drawer
                page.evaluate("document.querySelector('.ai-drawer-body')?.scrollBy({top: 160, behavior: 'smooth'})")
                capture_frame(5)

                # Click approve on proposal in drawer
                print(" -> Approving proposal...")
                approve_btn = page.locator("button:has-text('✓ Aplikovat do PDF')").first
                if approve_btn.is_visible():
                    approve_btn.click()
                    capture_frame(6)

                # Frame 29-38: Grading Dock and Scoring
                print(" -> Opening grading dock and adding deductions...")
                page.evaluate("App.toggleGradingDock()")
                capture_frame(5)

                # Scroll down in grading dock
                page.evaluate("document.querySelector('.grading-dock-body')?.scrollBy({top: 140, behavior: 'smooth'})")
                capture_frame(4)

                # Hover over finish export button
                finish_btn = page.locator(".btn-finish-action").first
                if finish_btn.is_visible():
                    finish_btn.hover()
                    capture_frame(6)

                # Compile full animation
                print(f"Captured {frame_idx} real frames. Compiling studio workflow animation...")
                compile_frames_to_animation(
                    frame_dir,
                    DOCS_ASSETS_DIR / "studio_workflow.webp",
                    DOCS_ASSETS_DIR / "studio_workflow.gif",
                    fps=8,
                    width=1180
                )
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.webp", DOCS_IMAGES_DIR / "studio_workflow.webp")
                shutil.copy(DOCS_ASSETS_DIR / "studio_workflow.gif", DOCS_IMAGES_DIR / "studio_workflow.gif")

            print("\nAll media generated successfully!")
            browser.close()

    finally:
        if server_proc:
            print("Stopping uvicorn server...")
            server_proc.terminate()
            server_proc.wait()

if __name__ == "__main__":
    run_media_generation()
