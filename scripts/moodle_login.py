#!/usr/bin/env python3
"""
Interactive Playwright Login Helper for ČVUT Moodle (course 16880)
Launches Chromium on your desktop, lets you sign in via Microsoft Entra ID / SSO,
captures the MoodleSession cookie, and stores it in the Praktika database.
"""

import sys
import time
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import init_db, save_moodle_setting, log_event

def run_interactive_login(moodle_url: str = "https://moodle-vyuka.cvut.cz", course_id: str = "16880"):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=" * 65)
    print("🎓 Praktika - Interaktivní přihlášení do ČVUT Moodle")
    print(f"URL Moodle: {moodle_url}")
    print(f"Cílový kurz: {course_id}")
    print("=" * 65)
    print("\n1. Otevírám okno prohlížeče...")
    print("2. Přihlaste se svým ČVUT účtem (Microsoft SSO / 2FA).")
    print("3. Jakmile budete přihlášeni a uvidíte Moodle, skript automaticky zachytí relaci.\n")

    init_db()

    with sync_playwright() as p:
        # Launch visible browser for interactive SSO
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        login_url = f"{moodle_url.rstrip('/')}/login/index.php"
        target_course_url = f"{moodle_url.rstrip('/')}/course/view.php?id={course_id}"

        page.goto(login_url)

        moodle_session_value = None
        max_wait_seconds = 300 # 5 minutes max wait
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            time.sleep(1.5)
            cookies = context.cookies()
            for c in cookies:
                if c.get("name") == "MoodleSession" and c.get("value"):
                    # Check if we have arrived at moodle domain
                    current_url = page.url
                    if moodle_url.replace("https://", "").replace("http://", "") in current_url and "login" not in current_url:
                        moodle_session_value = c["value"]
                        break

            if moodle_session_value:
                break

        if not moodle_session_value:
            print("\n❌ Časový limit pro přihlášení vypršel nebo nebyla cookie MoodleSession nalezena.")
            browser.close()
            sys.exit(1)

        print("\n✅ Úspěšně zachycena cookie MoodleSession!")
        print(f"Hodnota: {moodle_session_value[:8]}...{moodle_session_value[-6:]}")

        # Save to database
        save_moodle_setting("moodle_url", moodle_url)
        save_moodle_setting("moodle_course_id", course_id)
        save_moodle_setting("moodle_session_cookie", moodle_session_value)

        # Save to local json file as well
        session_file = PROJECT_ROOT / "data" / "moodle_session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text(json.dumps({
            "moodle_url": moodle_url,
            "course_id": course_id,
            "moodle_session": moodle_session_value,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }, indent=2), encoding="utf-8")

        print("💾 Cookie byla bezpečně uložena do SQLite databáze i do data/moodle_session.json.")
        
        # Test navigation to course 16880
        print(f"\n🔍 Ověřuji přístup ke kurzu {course_id}...")
        page.goto(target_course_url)
        time.sleep(2)
        course_title = page.title()
        print(f"📖 Název kurzu: {course_title}")
        print("\n🎉 Hotovo! Nyní můžete v Praktika automaticky stahovat i nahrávat protokoly.")

        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://moodle-vyuka.cvut.cz"
    cid = sys.argv[2] if len(sys.argv) > 2 else "16880"
    run_interactive_login(url, cid)

