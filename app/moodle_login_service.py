"""
Praktika Evaluation Studio - Moodle Interactive & Credential Login Service
Manages automated, credential-based, and interactive Playwright logins for ČVUT Moodle.
Supports Microsoft Entra ID SSO with 2FA Authenticator number matching, push notifications, and TOTP/SMS codes.
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
            "status": "idle",  # idle, starting, authenticating, awaiting_2fa_number, awaiting_2fa_push, awaiting_2fa_code, success, error, cancelled
            "message": "Připraveno k přihlášení.",
            "cookie_preview": None,
            "started_at": None,
            "finished_at": None,
            "error_detail": None,
            "course_title": None,
            "two_factor_type": None,
            "two_factor_number": None
        }
        self._thread: Optional[threading.Thread] = None
        self._cancel_flag = threading.Event()
        self._code_event = threading.Event()
        self._submitted_code: Optional[str] = None
        self._active_context = None

    @classmethod
    def get_instance(cls) -> "MoodleInteractiveLoginManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            # Return shallow copy, state never holds password
            return dict(self.state)

    def cancel(self) -> Dict[str, Any]:
        with self._lock:
            if self.state["status"] in ("starting", "authenticating", "awaiting_2fa_number", "awaiting_2fa_push", "awaiting_2fa_code", "awaiting_user", "silent_checking"):
                self._cancel_flag.set()
                self._code_event.set()
                self.state["status"] = "cancelled"
                self.state["message"] = "Přihlašování bylo zrušeno uživatelem."
                self.state["finished_at"] = time.time()
                try:
                    if self._active_context:
                        self._active_context.close()
                except Exception:
                    pass
                return {"status": "cancelled", "message": "Proces přihlašování byl zrušen."}
            return {"status": self.state["status"], "message": "Žádný proces přihlašování právě neběží."}

    def start_credential_login(self, username: str, password: str, moodle_url: Optional[str] = None, course_id: Optional[str] = None) -> Dict[str, Any]:
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
            self._code_event.clear()
            self._submitted_code = None
            self._active_context = None

            clean_user = username.strip()
            if clean_user and "@" not in clean_user:
                clean_user = f"{clean_user}@cvut.cz"

            self.state = {
                "status": "authenticating",
                "message": "Ověřuji přihlašovací údaje na ČVUT Microsoft SSO...",
                "cookie_preview": None,
                "started_at": time.time(),
                "finished_at": None,
                "error_detail": None,
                "course_title": None,
                "two_factor_type": None,
                "two_factor_number": None,
                "moodle_url": target_url,
                "course_id": target_course
            }

            self._thread = threading.Thread(
                target=self._run_credential_pipeline,
                args=(clean_user, password, target_url, target_course),
                daemon=True,
                name="MoodleCredentialLoginThread"
            )
            self._thread.start()

            return {
                "already_running": False,
                "status": "authenticating",
                "message": "Přihlašování bylo zahájeno."
            }

    def submit_2fa_code(self, code: str) -> Dict[str, Any]:
        with self._lock:
            if self.state["status"] != "awaiting_2fa_code":
                return {"status": "error", "message": "Aplikace právě nečeká na zadání 2FA kódu."}
            self._submitted_code = code.strip()
            self._code_event.set()
            self.state["message"] = "Ověřuji zadaný 2FA kód..."
            return {"status": "ok", "message": "Kód byl předán k ověření."}

    def start_login(self, moodle_url: Optional[str] = None, course_id: Optional[str] = None) -> Dict[str, Any]:
        """Legacy / headless silent check trigger."""
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
            self._code_event.clear()
            self._submitted_code = None
            self._active_context = None

            self.state = {
                "status": "starting",
                "message": "Kontroluji uloženou relaci na pozadí...",
                "cookie_preview": None,
                "started_at": time.time(),
                "finished_at": None,
                "error_detail": None,
                "course_title": None,
                "two_factor_type": None,
                "two_factor_number": None,
                "moodle_url": target_url,
                "course_id": target_course
            }

            self._thread = threading.Thread(
                target=self._run_silent_check_pipeline,
                args=(target_url, target_course),
                daemon=True,
                name="MoodleSilentLoginThread"
            )
            self._thread.start()

            return {
                "already_running": False,
                "status": "starting",
                "message": "Kontrola spuštěna."
            }

    def _ensure_display_env(self):
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            os.environ["DISPLAY"] = ":0"

    def _run_credential_pipeline(self, username: str, password: str, moodle_url: str, course_id: str):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            with self._lock:
                self.state["status"] = "error"
                self.state["message"] = "V prostředí serveru chybí balíček playwright."
                self.state["error_detail"] = "V kontejneru/serveru spusťte: pip install playwright && playwright install chromium"
                self.state["finished_at"] = time.time()
            return

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        login_url = f"{moodle_url}/login/index.php"
        moodle_host = moodle_url.replace("https://", "").replace("http://", "").split("/")[0]

        cookie_found = None
        try:
            with sync_playwright() as p:
                if self._cancel_flag.is_set():
                    return

                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._active_context = ctx
                page = ctx.new_page()

                # 1. Navigate to Moodle login
                try:
                    page.goto(login_url, timeout=25000)
                except Exception as ex:
                    raise RuntimeError(f"Nepodařilo se načíst přihlašovací stránku: {str(ex)}")

                # Check if already signed in via persistent context
                time.sleep(1.5)
                for c in ctx.cookies():
                    if c.get("name") == "MoodleSession" and c.get("value"):
                        c_domain = c.get("domain", "")
                        if moodle_host in c_domain or c_domain in moodle_host:
                            if "login" not in page.url and "microsoft" not in page.url:
                                cookie_found = c["value"]
                                break

                if not cookie_found and not self._cancel_flag.is_set():
                    # 2. Enter Email / Username or select existing Account Tile
                    user_short = username.split("@")[0].lower()
                    tile = page.locator(f'#tilesHolder .tile-container, div[data-test-id*="{user_short}"], div.table-row:has-text("{user_short}"), small:has-text("{user_short}")').first
                    other_tile = page.locator('#otherTile, div:has-text("Use another account"), div:has-text("Použít jiný účet")').first

                    try:
                        if tile.is_visible():
                            tile.click()
                            time.sleep(2.0)
                        elif other_tile.is_visible():
                            other_tile.click()
                            time.sleep(1.5)
                    except Exception:
                        pass

                    # If still on username screen, fill email
                    email_input = None
                    try:
                        email_input = page.wait_for_selector('input[type="email"], #i0116, input[name="loginfmt"], #userNameInput', timeout=6000)
                    except Exception:
                        email_input = None

                    if email_input:
                        try:
                            if email_input.is_visible():
                                email_input.fill(username)
                                submit_btn = page.locator('#idSIButton9, input[type="submit"]').first
                                if submit_btn.is_visible():
                                    submit_btn.click()
                                time.sleep(2.5)
                        except Exception:
                            pass

                        # Check for username error
                        user_err = page.locator('#usernameError').first
                        if user_err.is_visible():
                            err_txt = user_err.inner_text().strip()
                            raise RuntimeError(f"Chyba uživatelského jména: {err_txt}")

                    # 3. Enter Password (supports ČVUT ADFS logon.ms.cvut.cz and Microsoft SSO)
                    try:
                        pwd_input = page.wait_for_selector('#passwordInput, input[type="password"], #i0118, input[name="passwd"]', timeout=15000)
                    except Exception:
                        pwd_input = None

                    if pwd_input:
                        # If on ADFS and username is empty, fill it as well
                        adfs_user = page.locator('#userNameInput').first
                        if adfs_user.is_visible() and not adfs_user.input_value().strip():
                            adfs_user.fill(username)

                        pwd_input.fill(password)
                        password = ""  # Immediate memory erase
                        submit_pwd = page.locator('#submitButton, #idSIButton9, input[type="submit"], button[type="submit"]').first
                        if submit_pwd.is_visible():
                            submit_pwd.click()
                        time.sleep(3.0)

                        # Check for password error across ADFS and Microsoft
                        for err_sel in ['#passwordError', '#errorText', '#errorMessage', '.error']:
                            pwd_err = page.locator(err_sel).first
                            if pwd_err.is_visible():
                                err_txt = pwd_err.inner_text().strip()
                                if err_txt:
                                    raise RuntimeError(f"Neplatné heslo: {err_txt}")

                    # Memory hygiene
                    password = ""

                    # 4. Monitor for 2FA, KMSI (Stay signed in), or completion
                    start_wait = time.time()
                    max_2fa_wait = 180  # 3 minutes for 2FA confirmation

                    while time.time() - start_wait < max_2fa_wait:
                        if self._cancel_flag.is_set():
                            break

                        curr_url = page.url

                        # Check for MoodleSession
                        for c in ctx.cookies():
                            if c.get("name") == "MoodleSession" and c.get("value"):
                                c_domain = c.get("domain", "")
                                if moodle_host in c_domain or c_domain in moodle_host:
                                    if "login" not in curr_url and "microsoft" not in curr_url and "adfs" not in curr_url:
                                        cookie_found = c["value"]
                                        break
                        if cookie_found:
                            break

                        # Check for "Stay signed in?" screen
                        kmsi_btn = page.locator('#idSIButton9, #acceptButton').first
                        if kmsi_btn.is_visible() and ("kmsi" in curr_url.lower() or "stay" in curr_url.lower() or "stay signed in" in page.content().lower() or "zůstat přihlášeni" in page.content().lower()):
                            try:
                                kmsi_btn.click()
                                time.sleep(1.5)
                            except Exception:
                                pass

                        # If user submitted a 2FA code but OTC input is not visible yet, switch method
                        if self._submitted_code:
                            alt_method_btn = page.locator('#signInAnotherWay, :text("Use a verification code"), :text("Použít ověřovací kód"), :text("I can\'t use my Outlook mobile app right now")').first
                            try:
                                if alt_method_btn.is_visible():
                                    alt_method_btn.click()
                                    time.sleep(1.5)
                            except Exception:
                                pass

                        # Check for 2FA method choice screen (e.g. CompanionAppsNotification)
                        approve_choice = page.locator('div:has-text("Approve a request on my Outlook mobile app"), div:has-text("Schválit žádost v aplikaci Outlook"), div:has-text("Approve a request in Microsoft Authenticator"), div:has-text("Approve a request")').last
                        try:
                            if approve_choice.is_visible() and not self._submitted_code:
                                approve_choice.click()
                                time.sleep(2.0)
                        except Exception:
                            pass

                        # Check for 2FA Number Matching
                        rich_challenge = page.locator('#idRichContext_DisplaySign, #richChallange, #displaySign, .displaySign').first
                        is_number_challenge = False
                        try:
                            is_number_challenge = rich_challenge.is_visible()
                        except Exception:
                            is_number_challenge = False

                        if is_number_challenge:
                            num_val = rich_challenge.inner_text().strip()
                            with self._lock:
                                self.state["status"] = "awaiting_2fa_number"
                                self.state["two_factor_type"] = "number"
                                self.state["two_factor_number"] = num_val
                                self.state["message"] = f"Zadejte v aplikaci Microsoft Authenticator / Outlook číslo: {num_val}"

                        # Check for 2FA Push notification
                        else:
                            is_push = False
                            try:
                                push_loc = page.locator('#idDiv_SAOTCAS_Title, :text("Schvalte žádost o přihlášení"), :text("Approve sign in request"), :text("Approve a request")').first
                                is_push = push_loc.is_visible()
                            except Exception:
                                is_push = False

                            if is_push:
                                with self._lock:
                                    self.state["status"] = "awaiting_2fa_push"
                                    self.state["two_factor_type"] = "push"
                                    self.state["message"] = "Odesláno oznámení do aplikace Microsoft Authenticator / Outlook. Potvrďte jej prosím na telefonu."

                        # Check for 2FA Code input (SMS / TOTP)
                        otc_input = page.locator('#idTxtBx_SAOTCC_OTC, input[name="otc"]').first
                        if otc_input.is_visible():
                            with self._lock:
                                self.state["status"] = "awaiting_2fa_code"
                                self.state["two_factor_type"] = "code"
                                self.state["message"] = "Zadejte ověřovací kód z SMS nebo Authenticatoru:"

                            self._code_event.wait(timeout=1.5)
                            if self._submitted_code:
                                otc_input.fill(self._submitted_code)
                                self._submitted_code = None
                                self._code_event.clear()
                                cont_btn = page.locator('#idSubmit_SAOTCC_Continue, #idSIButton9, input[type="submit"], #submitButton').first
                                if cont_btn.is_visible():
                                    cont_btn.click()
                                time.sleep(2.0)

                        time.sleep(1.2)

                try:
                    ctx.close()
                except Exception:
                    pass
                self._active_context = None

        except Exception as e_proc:
            with self._lock:
                self.state["status"] = "error"
                self.state["message"] = f"Chyba při přihlašování: {str(e_proc)}"
                self.state["error_detail"] = str(e_proc)
                self.state["finished_at"] = time.time()
            return

        if cookie_found:
            self._finalize_success(cookie_found, moodle_url, course_id)
        else:
            with self._lock:
                if not self._cancel_flag.is_set():
                    self.state["status"] = "error"
                    self.state["message"] = "Časový limit pro schválení přihlášení (3 minuty) vypršel, nebo nebyla cookie zachycena."
                    self.state["error_detail"] = "Nebyla nalezena cookie MoodleSession."
                    self.state["finished_at"] = time.time()

    def _run_silent_check_pipeline(self, moodle_url: str, course_id: str):
        """Silently checks if persistent SSO profile already can log in."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            with self._lock:
                self.state["status"] = "error"
                self.state["message"] = "Playwright není nainstalován v prostředí serveru."
                self.state["error_detail"] = "Spusťte: pip install playwright && playwright install chromium"
                self.state["finished_at"] = time.time()
            return

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        login_url = f"{moodle_url}/login/index.php"
        moodle_host = moodle_url.replace("https://", "").replace("http://", "").split("/")[0]

        cookie_found = None
        try:
            with sync_playwright() as p:
                if self._cancel_flag.is_set():
                    return
                ctx = p.chromium.launch_persistent_context(
                    user_data_dir=str(PROFILE_DIR),
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                self._active_context = ctx
                page = ctx.new_page()
                page.goto(login_url, timeout=12000)

                start_silent = time.time()
                while time.time() - start_silent < 6.0:
                    if self._cancel_flag.is_set():
                        break
                    time.sleep(0.8)
                    for c in ctx.cookies():
                        if c.get("name") == "MoodleSession" and c.get("value"):
                            c_domain = c.get("domain", "")
                            if moodle_host in c_domain or c_domain in moodle_host:
                                if "login" not in page.url and "microsoft" not in page.url:
                                    cookie_found = c["value"]
                                    break
                    if cookie_found:
                        break

                ctx.close()
                self._active_context = None
        except Exception:
            pass

        if cookie_found:
            self._finalize_success(cookie_found, moodle_url, course_id)
        else:
            with self._lock:
                if not self._cancel_flag.is_set():
                    self.state["status"] = "idle"
                    self.state["message"] = "Relace není uložena. Zadejte prosím své přihlašovací údaje."

    _run_login_pipeline = _run_silent_check_pipeline

    def _finalize_success(self, cookie_val: str, moodle_url: str, course_id: str):
        save_moodle_setting("moodle_url", moodle_url)
        save_moodle_setting("moodle_course_id", course_id)
        save_moodle_setting("moodle_session_cookie", cookie_val)

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
            self.state["message"] = "MoodleSession byla úspěšně získána a uložena!"
            self.state["cookie_preview"] = preview
            self.state["two_factor_number"] = None
            self.state["two_factor_type"] = None
            self.state["finished_at"] = time.time()

        try:
            log_event(level="INFO", category="moodle", action="interactive_login_success", details=f"MoodleSession updated ({preview}) for course {course_id}")
        except Exception:
            pass
