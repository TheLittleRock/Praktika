"""
Praktika Evaluation Studio - Moodle Interactive Login Service
Manages automated and interactive Playwright logins for ČVUT Moodle.
Uses a persistent browser profile to store Microsoft SSO tokens.
Provides thread-safe state management for asynchronous web UI polling.
"""

import os
import sys
import time
import json
import threading
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.database import get_db, log_event
from app.moodle_service import get_moodle_config, save_moodle_setting, check_moodle_session_validity

logger = logging.getLogger("moodle_login")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = PROJECT_ROOT / "data" / "moodle_browser_profile"
SESSION_FILE = PROJECT_ROOT / "data" / "moodle_session.json"


class MoodleInteractiveLoginManager:
    _instance: Optional["MoodleInteractiveLoginManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self.state: Dict[str, Any] = {
            "status": "idle",  # idle, silent_checking, awaiting_user, success, error, cancelled
            "message": "Připraveno k přihlášení.",
            "cookie_preview": None,
            "started_at": None,
            "finished_at": None,
            "error_detail": None,
            "course_title": None
        }
        self._thread: Optional[threading.Thread] = None
        self._cancel_flag = threading.Event()
        self._active_context = None

    @classmethod
    def get_instance(cls) -> "MoodleInteractiveLoginManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self.state)

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            if self.state["status"] in ("silent_checking", "awaiting_user", "starting"):
                self._cancel_flag.set()
                self.state["status"] = "cancelled"
                self.state["message"] = "Přihlašování bylo zrušeno uživatelem."
                self.state["finished_at"] = time.time()
                # If there's an active context, attempt close from another thread or flag
                try:
                    if self._active_context:
                        self._active_context.close()
                except Exception:
                    pass
                return {"status": "cancelled", "message": "Proces přihlašování byl zrušen."}
            return {"status": self.state["status"], "message": "Žádný proces přihlašování právě neběží."}

    def start_login(self, moodle_url: Optional[str] = None, course_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {
                    "already_running": True,
                    "status": self.state["status"],
                    "message": "Proces přihlašování již probíhá."
                }

            cfg = get_moodle_config()
            target_url = (moodle_url or cfg.get("moodle_url") or "https://moodle-vyuka.cvut.cz").rstrip("/")
            target_course = str(course_id or cfg.get("course_id") or "16880").strip()

            self._cancel_flag.clear()
            self._active_context = None
            self.state = {
                "status": "starting",
                "message": "Inicializuji přihlašovací službu...",
                "cookie_preview": None,
                "started_at": time.time(),
                "finished_at": None,
                "error_detail": None,
                "course_title": None,
                "moodle_url": target_url,
                "course_id": target_course
            }

            self._thread = threading.Thread(
                target=self._run_login_pipeline,
                args=(target_url, target_course),
                daemon=True,
                name="MoodleInteractiveLoginThread"
            )
            self._thread.start()

            return {
                "already_running": False,
                "status": "starting",
                "message": "Přihlašování spuštěno."
            }

    def _ensure_display_env(self):
        """Ensures DISPLAY or WAYLAND_DISPLAY is configured for Linux GUI applications."""
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ["DISPLAY"] = ":0"

    def _run_login_pipeline(self, moodle_url: str, course_id: str):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            with self._lock:
                self.state["status"] = "error"
                self.state["message"] = "Playwright není nainstalován v prostředí serveru."
                self.state["error_detail"] = "Chybí balíček playwright (spusťte: pip install playwright && playwright install chromium)."
                self.state["finished_at"] = time.time()
            return

        self._ensure_display_env()
        PROFILE_DIR.mkdir(parents=True, exist_ok=True)

        login_url = f"{moodle_url}/login/index.php"
        course_url = f"{moodle_url}/course/view.php?id={course_id}"
        moodle_host = moodle_url.replace("https://", "").replace("http://", "").split("/")[0]

        # -----------------------------------------------------------------
        # Phase 1: Silent Background Check (Headless with persistent SSO profile)
        # -----------------------------------------------------------------
        with self._lock:
            self.state["status"] = "silent_checking"
            self.state["message"] = "Kontroluji platnost uloženého SSO přihlášení na pozadí..."

        cookie_found = None
        silent_success = False

        try:
            with sync_playwright() as p:
                if self._cancel_flag.is_set():
                    return

                try:
                    ctx = p.chromium.launch_persistent_context(
                        user_data_dir=str(PROFILE_DIR),
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    self._active_context = ctx
                    page = ctx.new_page()
                    page.goto(login_url, timeout=12000)

                    # Poll for up to 6 seconds to see if persistent SSO logs us in automatically
                    start_silent = time.time()
                    while time.time() - start_silent < 6.0:
                        if self._cancel_flag.is_set():
                            ctx.close()
                            return
                        time.sleep(0.8)

                        # Check cookies
                        for c in ctx.cookies():
                            if c.get("name") == "MoodleSession" and c.get("value"):
                                c_domain = c.get("domain", "")
                                if moodle_host in c_domain or c_domain in moodle_host:
                                    curr_url = page.url
                                    if "login" not in curr_url and "microsoft" not in curr_url:
                                        cookie_found = c["value"]
                                        silent_success = True
                                        break
                        if silent_success:
                            break

                    ctx.close()
                    self._active_context = None
                except Exception as e_silent:
                    logger.info("Silent login check did not complete (interactive required): %s", e_silent)
                    try:
                        if self._active_context:
                            self._active_context.close()
                    except Exception:
                        pass
                    self._active_context = None

        except Exception as e:
            logger.warning("Error during silent login attempt: %s", e)

        if silent_success and cookie_found:
            self._finalize_success(cookie_found, moodle_url, course_id)
            return

        if self._cancel_flag.is_set():
            return

        # -----------------------------------------------------------------
        # Phase 2: Headed Interactive Login Window
        # -----------------------------------------------------------------
        with self._lock:
            self.state["status"] = "awaiting_user"
            self.state["message"] = "Otevřeno okno prohlížeče. Dokončete prosím přihlášení přes ČVUT SSO/2FA na obrazovce."

        try:
            with sync_playwright() as p:
                if self._cancel_flag.is_set():
                    return

                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=False,
                    args=["--no-sandbox"],
                    viewport={"width": 1100, "height": 780}
                )
                self._active_context = ctx
                page = ctx.new_page()

                try:
                    page.goto(login_url, timeout=20000)
                except Exception as e_nav:
                    logger.warning("Initial navigation warning: %s", e_nav)

                # Wait up to 300 seconds (5 minutes) for user to sign in
                max_wait = 300
                start_headed = time.time()

                while time.time() - start_headed < max_wait:
                    if self._cancel_flag.is_set():
                        ctx.close()
                        self._active_context = None
                        return

                    time.sleep(1.2)

                    try:
                        cookies = ctx.cookies()
                        for c in cookies:
                            if c.get("name") == "MoodleSession" and c.get("value"):
                                c_domain = c.get("domain", "")
                                if moodle_host in c_domain or c_domain in moodle_host:
                                    curr_url = page.url
                                    # Ensure we have left Microsoft login and login/index.php
                                    if "login" not in curr_url and "microsoft" not in curr_url:
                                        cookie_found = c["value"]
                                        break
                    except Exception as e_poll:
                        # Page or browser might be closing or busy
                        pass

                    if cookie_found:
                        # Try navigating to target course to ensure authorization
                        try:
                            page.goto(course_url, timeout=8000)
                            time.sleep(1.5)
                            ctitle = page.title()
                            with self._lock:
                                self.state["course_title"] = ctitle
                        except Exception:
                            pass
                        break

                try:
                    ctx.close()
                except Exception:
                    pass
                self._active_context = None

        except Exception as e_headed:
            with self._lock:
                self.state["status"] = "error"
                self.state["message"] = f"Chyba při spuštění okna prohlížeče: {str(e_headed)}"
                self.state["error_detail"] = str(e_headed)
                self.state["finished_at"] = time.time()
            return

        if cookie_found:
            self._finalize_success(cookie_found, moodle_url, course_id)
        else:
            with self._lock:
                if not self._cancel_flag.is_set():
                    self.state["status"] = "error"
                    self.state["message"] = "Časový limit pro přihlášení (5 minut) vypršel, nebo nebyla cookie MoodleSession nalezena."
                    self.state["error_detail"] = "Nepodařilo se zachytit MoodleSession před vypršením limitu."
                    self.state["finished_at"] = time.time()

    def _finalize_success(self, cookie_val: str, moodle_url: str, course_id: str):
        # Save to database
        save_moodle_setting("moodle_url", moodle_url)
        save_moodle_setting("moodle_course_id", course_id)
        save_moodle_setting("moodle_session_cookie", cookie_val)

        # Save to data/moodle_session.json backup
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FILE.write_text(json.dumps({
                "moodle_url": moodle_url,
                "course_id": course_id,
                "moodle_session": cookie_val,
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not write session file: %s", e)

        preview = f"{cookie_val[:6]}...{cookie_val[-4:]}" if len(cookie_val) > 10 else "***"
        with self._lock:
            self.state["status"] = "success"
            self.state["message"] = "MoodleSession byla úspěšně zachycena a uložena!"
            self.state["cookie_preview"] = preview
            self.state["finished_at"] = time.time()

        try:
            log_event("moodle", "interactive_login_success", f"MoodleSession updated ({preview}) for course {course_id}")
        except Exception:
            pass
