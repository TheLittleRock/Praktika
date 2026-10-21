#!/usr/bin/env python3
"""
CLI Test Script to verify Moodle connection to ČVUT Course 16880
Can be run directly from terminal:
./venv/bin/python scripts/test_moodle_connection.py [--cookie <MoodleSession_value>]
"""

import sys
import asyncio
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.database import init_db, save_moodle_setting
from app.moodle_service import (
    get_moodle_config, 
    check_moodle_session_validity, 
    fetch_course_structure
)

async def main():
    parser = argparse.ArgumentParser(description="Test Moodle connection for course 16880")
    parser.add_argument("--cookie", type=str, default="", help="MoodleSession cookie value")
    parser.add_argument("--course", type=str, default="16880", help="Course ID")
    parser.add_argument("--url", type=str, default="https://moodle-vyuka.cvut.cz", help="Moodle base URL")
    args = parser.parse_args()

    init_db()
    cfg = get_moodle_config()

    moodle_url = (args.url or cfg["moodle_url"]).rstrip("/")
    course_id = (args.course or cfg["course_id"]).strip()
    session_cookie = (args.cookie or cfg["moodle_session"]).strip()

    print("=" * 65)
    print("🧪 Test spojení s Moodle ČVUT")
    print(f"Moodle URL: {moodle_url}")
    print(f"ID kurzu:   {course_id}")
    if session_cookie:
        print(f"Cookie:     {session_cookie[:8]}...{session_cookie[-6:]} (délka: {len(session_cookie)} znaků)")
    else:
        print("Cookie:     [NENÍ NASTAVENA]")
    print("=" * 65)

    if not session_cookie:
        print("\n⚠️ Chybí cookie MoodleSession!")
        print("Můžete ji získat buď:")
        print("1. Spuštěním: ./venv/bin/python scripts/moodle_login.py")
        print("2. Zkopírováním z prohlížeče (F12 -> Cookies -> MoodleSession) a spuštěním:")
        print("   ./venv/bin/python scripts/test_moodle_connection.py --cookie 'VASE_COOKIE'")
        print("3. Vložením do webového rozhraní Praktika v Nastavení -> Moodle integrace.")
        sys.exit(1)

    if args.cookie:
        save_moodle_setting("moodle_session_cookie", args.cookie)
        save_moodle_setting("moodle_url", moodle_url)
        save_moodle_setting("moodle_course_id", course_id)
        print("💾 Zadaná cookie byla uložena do SQLite databáze.")

    print("\n🔍 1. Ověřuji platnost session...")
    is_valid, msg = await check_moodle_session_validity(moodle_url, course_id, session_cookie)
    if not is_valid:
        print(f"❌ Chyba spojení: {msg}")
        sys.exit(1)

    print(f"✅ Spojení úspěšné! Kurz ověřen: \"{msg}\"")

    print("\n🔍 2. Načítám strukturu kurzu (úlohy a skupiny)...")
    try:
        structure = await fetch_course_structure(moodle_url, course_id, session_cookie)
        assignments = structure.get("assignments", [])
        groups = structure.get("groups", [])

        print(f"📚 Nalezeno úloh (Assignmentů): {len(assignments)}")
        for i, a in enumerate(assignments, 1):
            print(f"   {i:2d}. [cmid={a['cmid']}] {a['title']}")

        print(f"\n👥 Nalezeno skupin (termínů): {len(groups)}")
        for g in groups:
            print(f"   • [id={g['id']}] {g['name']}")

        print("\n🎉 Vše funguje perfektně! Praktika je plně připravena k automatickému stahování a nahrávání.")
    except Exception as ex:
        print(f"❌ Chyba při parsování struktury kurzu: {ex}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
