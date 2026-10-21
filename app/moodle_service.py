"""
Praktika Moodle Integration Service
Handles web-based interaction with Moodle (specifically ČVUT https://moodle-vyuka.cvut.cz)
without requiring official REST API tokens:
1. Course structure scraping (assignments from /mod/assign/index.php and groups from /user/index.php)
2. Discovery of unrated submitted protocols with task & term auto-matching
3. Direct download and importing into Praktika
4. Uploading feedback PDFs and submitting grades (A-F ČVUT scale) & comments via Moodle AJAX service
"""

import re
import io
import json
import zipfile
import shutil
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import httpx

from app.database import get_db, log_event

class MoodleAuthError(Exception):
    """Raised when MoodleSession cookie is missing, invalid or expired."""
    pass

class MoodleServiceError(Exception):
    """General Moodle service error."""
    pass


def get_moodle_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row and row[0] is not None:
        return str(row[0]).strip()
    return default


def save_moodle_setting(key: str, value: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value).strip())
    )
    conn.commit()
    conn.close()


def get_moodle_config() -> Dict[str, str]:
    return {
        "moodle_url": get_moodle_setting("moodle_url", "https://moodle-vyuka.cvut.cz").rstrip("/"),
        "course_id": get_moodle_setting("moodle_course_id", "16880").strip(),
        "moodle_session": get_moodle_setting("moodle_session_cookie", "").strip(),
    }


def clean_html_text(html: str) -> str:
    """Strip HTML tags and unescape entities."""
    import html as html_lib
    text = re.sub(r'<[^>]+>', ' ', html)
    text = html_lib.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def normalize_student_name(name: str) -> str:
    """Normalize student name for cross-system matching (remove prefixes like AJ, lowercase, sort tokens)."""
    # Remove 2-letter initials prefix often found in Moodle, e.g. "AJ Adam Jaroslav"
    clean = re.sub(r'^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]{2}\s+', '', name).strip()
    return clean


def calculate_cvut_grade(points: float, max_points: float) -> Tuple[str, int]:
    """
    Standard ČVUT ECTS grading scale:
    A: >= 90% (Moodle scale value 6)
    B: >= 80% (Moodle scale value 5)
    C: >= 70% (Moodle scale value 4)
    D: >= 60% (Moodle scale value 3)
    E: >= 50% (Moodle scale value 2)
    F: < 50%  (Moodle scale value 1)
    """
    if max_points <= 0:
        return ("A", 6)
    
    pct = (points / max_points) * 100.0
    if pct >= 89.99:
        return ("A", 6)
    elif pct >= 79.99:
        return ("B", 5)
    elif pct >= 69.99:
        return ("C", 4)
    elif pct >= 59.99:
        return ("D", 3)
    elif pct >= 49.99:
        return ("E", 2)
    else:
        return ("F", 1)


def moodle_grade_to_scale_id(grade_letter: str) -> int:
    mapping = {
        "A": 6,
        "B": 5,
        "C": 4,
        "D": 3,
        "E": 2,
        "F": 1
    }
    return mapping.get(grade_letter.strip().upper(), -1)


async def check_moodle_session_validity(moodle_url: str, course_id: str, session_cookie: str) -> Tuple[bool, str]:
    """
    Checks whether the session cookie can access the course.
    Returns (is_valid, course_title_or_error_message).
    """
    if not session_cookie:
        return False, "Není nastavena žádná cookie MoodleSession."

    target_url = f"{moodle_url.rstrip('/')}/course/view.php?id={course_id}"
    cookies = {"MoodleSession": session_cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs,en;q=0.9"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, cookies=cookies) as client:
            resp = await client.get(target_url, headers=headers)
            final_url = str(resp.url)

            if "login.microsoftonline.com" in final_url or "login/index.php" in final_url or "shibboleth" in final_url.lower():
                return False, "Relace MoodleSession vypršela nebo je neplatná (přesměrováno na přihlášení ČVUT)."

            if resp.status_code != 200:
                return False, f"Moodle vrátil HTTP kód {resp.status_code}."

            html = resp.text
            title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.I)
            raw_title = title_match.group(1) if title_match else f"Kurz #{course_id}"
            title = clean_html_text(raw_title)
            title = re.sub(r'\s*\|\s*Moodle.*$', '', title).strip()

            return True, title
    except Exception as ex:
        return False, f"Chyba při komunikaci s Moodle: {str(ex)}"


async def fetch_course_structure(
    moodle_url: Optional[str] = None, 
    course_id: Optional[str] = None, 
    session_cookie: Optional[str] = None
) -> Dict[str, Any]:
    """
    Scrapes the course structure:
    1. Assignments list from /mod/assign/index.php?id={course_id}
    2. Available groups and students from /user/index.php?id={course_id}&perpage=500
    """
    cfg = get_moodle_config()
    m_url = (moodle_url or cfg["moodle_url"]).rstrip("/")
    c_id = (course_id or cfg["course_id"]).strip()
    s_cookie = (session_cookie or cfg["moodle_session"]).strip()

    if not s_cookie:
        raise MoodleAuthError("Chybí cookie MoodleSession. Zadejte ji prosím v Nastavení nebo se přihlaste.")

    cookies = {"MoodleSession": s_cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, cookies=cookies) as client:
        # 1. Fetch Assignments Index
        assign_index_url = f"{m_url}/mod/assign/index.php?id={c_id}"
        resp_assign = await client.get(assign_index_url, headers=headers)
        if "login.microsoftonline.com" in str(resp_assign.url) or "login/index.php" in str(resp_assign.url):
            raise MoodleAuthError("Relace MoodleSession vypršela nebo je neplatná. Přihlaste se prosím znovu.")

        html_assign = resp_assign.text

        # Extract sesskey if present
        sesskey_match = re.search(r'["\']sesskey["\']\s*:\s*["\']([a-zA-Z0-9]+)["\']', html_assign)
        if not sesskey_match:
            sesskey_match = re.search(r'sesskey=([a-zA-Z0-9]+)', html_assign)
        sesskey = sesskey_match.group(1) if sesskey_match else ""

        # Parse course title
        title_match = re.search(r'<title>(.*?)</title>', html_assign, re.I)
        course_title = clean_html_text(title_match.group(1)) if title_match else f"Kurz {c_id}"
        course_title = re.sub(r'\s*\|\s*Moodle.*$', '', course_title).strip()

        # Parse assignments table rows
        assignments = []
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_assign, re.DOTALL)
        current_section = ""

        for r in rows:
            cells = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c)).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.DOTALL)]
            link_m = re.search(r'href="[^"]*?/mod/assign/view\.php\?id=(\d+)"[^>]*>(.*?)</a>', r, re.DOTALL)
            if len(cells) >= 4 and link_m:
                cmid = link_m.group(1)
                raw_name = clean_html_text(link_m.group(2))
                if cells[0]:
                    current_section = cells[0]
                
                submitted_str = cells[3] if len(cells) > 3 else "0"
                grading_str = cells[4] if len(cells) > 4 else ""

                submitted_count = int(re.search(r'\d+', submitted_str).group(0)) if re.search(r'\d+', submitted_str) else 0
                needs_grading = int(re.search(r'\d+', grading_str).group(0)) if re.search(r'\d+', grading_str) else 0

                # Extract task number (e.g. "P1" -> 1, or from section "01 - Vzduchová dráha" -> 1)
                num_m = re.search(r'^P(\d+)', raw_name, re.I)
                task_number = int(num_m.group(1)) if num_m else None
                if task_number is None and current_section:
                    sec_num_m = re.search(r'^(\d+)', current_section)
                    if sec_num_m:
                        task_number = int(sec_num_m.group(1))

                # Display label: e.g. "P1: 01 - Vzduchová dráha - ZZE..." or "P1 (Úloha 1)"
                if current_section and current_section.lower() not in raw_name.lower():
                    display_label = f"{raw_name} – {current_section}"
                else:
                    display_label = raw_name

                assignments.append({
                    "cmid": cmid,
                    "title": display_label,
                    "short_name": raw_name,
                    "section": current_section,
                    "task_number": task_number,
                    "submitted_count": submitted_count,
                    "needs_grading_count": needs_grading,
                    "is_protocol": bool(raw_name.upper().startswith("P") and not raw_name.upper().startswith("PŘEHLED"))
                })

        # 2. Fetch Participants to extract Groups
        groups_list = [{"id": "all", "name": "Všechny skupiny", "count": 0}]
        group_counts: Dict[str, int] = {}

        try:
            user_index_url = f"{m_url}/user/index.php?id={c_id}&perpage=500"
            resp_users = await client.get(user_index_url, headers=headers)
            html_users = resp_users.text

            table_m = re.search(r'<table[^>]*id="participants"[^>]*>(.*?)</table>', html_users, re.DOTALL)
            if not table_m:
                table_m = re.search(r'<table[^>]*class="[^"]*generaltable[^"]*"[^>]*>(.*?)</table>', html_users, re.DOTALL)

            if table_m:
                trs = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.DOTALL)
                for tr in trs[1:]:
                    tds = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', td)).strip() for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.DOTALL)]
                    if len(tds) >= 6:
                        group_str = tds[5]
                        user_groups = [g.strip() for g in group_str.split(",") if g.strip() and g.strip() != "Žádné skupiny"]
                        for g in user_groups:
                            group_counts[g] = group_counts.get(g, 0) + 1
        except Exception as e:
            print("Warning: could not fetch groups from user index:", e)

        for gname in sorted(group_counts.keys()):
            groups_list.append({
                "id": gname,
                "name": gname,
                "count": group_counts[gname]
            })

        return {
            "course_id": c_id,
            "course_title": course_title,
            "sesskey": sesskey,
            "assignments": assignments,
            "groups": groups_list
        }


async def fetch_course_user_groups_map(
    moodle_url: str, 
    course_id: str, 
    session_cookie: str
) -> Dict[str, Any]:
    """
    Builds maps of student names and user IDs to groups and emails from /user/index.php.
    """
    cookies = {"MoodleSession": session_cookie}
    headers = {"User-Agent": "Mozilla/5.0"}
    user_map = {} # normalized_name -> { moodle_user_id, group, email, raw_name }
    id_map = {}   # moodle_user_id -> { moodle_user_id, group, email, raw_name }

    try:
        url = f"{moodle_url}/user/index.php?id={course_id}&perpage=500"
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, cookies=cookies) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

            table_m = re.search(r'<table[^>]*id="participants"[^>]*>(.*?)</table>', html, re.DOTALL)
            if not table_m:
                table_m = re.search(r'<table[^>]*class="[^"]*generaltable[^"]*"[^>]*>(.*?)</table>', html, re.DOTALL)

            if table_m:
                trs = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.DOTALL)
                for tr in trs[1:]:
                    tds = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', td)).strip() for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.DOTALL)]
                    if len(tds) >= 6:
                        name_raw = normalize_student_name(tds[1])
                        email = tds[3]
                        group_str = tds[5]
                        first_group = group_str.split(",")[0].strip() if group_str and group_str != "Žádné skupiny" else ""

                        # Extract user ID from user profile link
                        uid_match = re.search(r'/user/view\.php\?id=(\d+)', tr)
                        uid = int(uid_match.group(1)) if uid_match else None

                        info = {
                            "moodle_user_id": uid,
                            "raw_name": name_raw,
                            "group": first_group,
                            "email": email
                        }

                        norm_key = name_raw.lower()
                        user_map[norm_key] = info
                        # Also add without diacritics or tokens
                        tokens = sorted(norm_key.split())
                        user_map[" ".join(tokens)] = info

                        if uid:
                            id_map[str(uid)] = info
    except Exception as e:
        print("Error fetching user groups map:", e)

    return {"by_name": user_map, "by_id": id_map}


async def fetch_pending_submissions(
    cmid: Optional[str] = None,
    group: Optional[str] = None,
    moodle_url: Optional[str] = None,
    course_id: Optional[str] = None,
    session_cookie: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Finds all submitted protocols that do NOT have a grade yet.
    Matches with student group and auto-matches local measurement and slot.
    """
    cfg = get_moodle_config()
    m_url = (moodle_url or cfg["moodle_url"]).rstrip("/")
    c_id = (course_id or cfg["course_id"]).strip()
    s_cookie = (session_cookie or cfg["moodle_session"]).strip()

    if not s_cookie:
        raise MoodleAuthError("Chybí cookie MoodleSession.")

    # 1. Load course structure to know which assignments to check
    structure = await fetch_course_structure(m_url, c_id, s_cookie)
    user_maps = await fetch_course_user_groups_map(m_url, c_id, s_cookie)
    by_name = user_maps["by_name"]
    by_id = user_maps["by_id"]

    assignments_to_check = []
    if cmid and cmid != "all":
        assignments_to_check = [a for a in structure["assignments"] if str(a["cmid"]) == str(cmid)]
    else:
        # Check all protocol assignments that have submissions or needs_grading > 0
        assignments_to_check = [a for a in structure["assignments"] if a.get("is_protocol") and a.get("needs_grading_count", 0) > 0]
        if not assignments_to_check:
            # Fallback: check all protocol assignments
            assignments_to_check = [a for a in structure["assignments"] if a.get("is_protocol")][:12]

    cookies = {"MoodleSession": s_cookie}
    headers = {"User-Agent": "Mozilla/5.0"}

    # Load local measurements and slots for auto-matching
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, number, name, code FROM measurements")
    local_measurements = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT id, name, semester_id FROM slots")
    local_slots = [dict(r) for r in cur.fetchall()]

    cur.execute("SELECT id, name, code FROM semesters WHERE is_active = 1 LIMIT 1")
    active_sem_row = cur.fetchone()
    active_semester = dict(active_sem_row) if active_sem_row else None

    # Load existing protocols for duplicate check
    cur.execute("SELECT student_name, measurement_id FROM protocols")
    existing_protocols = set((r[0].strip().lower(), r[1]) for r in cur.fetchall() if r[0] and r[1])
    conn.close()

    pending_items = []

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, cookies=cookies) as client:
        for assign in assignments_to_check:
            assign_cmid = assign["cmid"]
            assign_title = assign["title"]
            assign_task_num = assign.get("task_number")

            grading_url = f"{m_url}/mod/assign/view.php?id={assign_cmid}&action=grading&perpage=100"
            resp = await client.get(grading_url, headers=headers)
            html = resp.text

            table_m = re.search(r'<table[^>]*class="flexible table[^>]*>(.*?)</table>', html, re.DOTALL)
            if not table_m:
                continue

            trs = re.findall(r'<tr[^>]*>(.*?)</tr>', table_m.group(1), re.DOTALL)
            for tr in trs[1:]:
                tds = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', td)).strip() for td in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.DOTALL)]
                if len(tds) < 8:
                    continue

                student_name_raw = normalize_student_name(tds[1])
                status_text = tds[4]
                grade_text = tds[5]
                files_text = tds[7]

                # Check if there is an uploaded file
                file_link_match = re.search(r'href="([^"]*?/pluginfile\.php/[^"]*?/assignsubmission_file/[^"]*?)"[^>]*>(.*?)</a>', tr, re.DOTALL)
                if not file_link_match:
                    continue

                file_url = file_link_match.group(1).replace("&amp;", "&")
                filename = clean_html_text(file_link_match.group(2))

                # Check if already graded: if "Udělena známka" is present or grade is not "-"
                has_grade = ("udělena známka" in status_text.lower() or 
                             (grade_text != "-" and grade_text != "" and not grade_text.startswith("-")))
                if has_grade:
                    continue

                # Extract Moodle User ID
                uid_match = re.search(r'/user/view\.php\?id=(\d+)', tr)
                moodle_uid = int(uid_match.group(1)) if uid_match else None

                # Find student's group
                student_group = ""
                if moodle_uid and str(moodle_uid) in by_id:
                    student_group = by_id[str(moodle_uid)].get("group", "")
                if not student_group:
                    norm_key = student_name_raw.lower()
                    if norm_key in by_name:
                        student_group = by_name[norm_key].get("group", "")
                    else:
                        tokens_key = " ".join(sorted(norm_key.split()))
                        if tokens_key in by_name:
                            student_group = by_name[tokens_key].get("group", "")

                # If group filter active and mismatch, skip
                if group and group != "all" and student_group != group:
                    continue

                # Auto-match local measurement
                matched_task = None
                if assign_task_num:
                    matched_task = next((m for m in local_measurements if m.get("number") == assign_task_num), None)
                if not matched_task and assign.get("section"):
                    sec_clean = assign["section"].lower()
                    matched_task = next((m for m in local_measurements if m["name"].lower() in sec_clean or sec_clean in m["name"].lower()), None)

                # Auto-match local slot
                matched_slot = None
                if student_group:
                    matched_slot = next((s for s in local_slots if s["name"].strip().lower() == student_group.strip().lower()), None)

                # Check if duplicate in DB
                is_duplicate = False
                if matched_task:
                    norm_student = student_name_raw.strip().lower()
                    is_duplicate = (norm_student, matched_task["id"]) in existing_protocols

                pending_items.append({
                    "cmid": assign_cmid,
                    "task_title": assign_title,
                    "student_name": student_name_raw,
                    "moodle_user_id": moodle_uid,
                    "student_group": student_group,
                    "filename": filename,
                    "file_url": file_url,
                    "status_text": status_text,
                    "matched_task_id": matched_task["id"] if matched_task else None,
                    "matched_task_name": matched_task["name"] if matched_task else "",
                    "matched_slot_id": matched_slot["id"] if matched_slot else None,
                    "matched_slot_name": matched_slot["name"] if matched_slot else "",
                    "can_auto_create_slot": bool(student_group and not matched_slot),
                    "already_in_db": is_duplicate
                })

    return pending_items


async def submit_moodle_grade(
    cmid: str,
    userid: int,
    grade_letter: str,
    comment_text: str,
    send_notifications: bool = False,
    moodle_url: Optional[str] = None,
    session_cookie: Optional[str] = None
) -> Dict[str, Any]:
    """
    Submits student grade and feedback comment using Moodle's internal AJAX service:
    /lib/ajax/service.php calling method 'mod_assign_submit_grading_form'.
    """
    cfg = get_moodle_config()
    m_url = (moodle_url or cfg["moodle_url"]).rstrip("/")
    s_cookie = (session_cookie or cfg["moodle_session"]).strip()

    if not s_cookie:
        raise MoodleAuthError("Chybí cookie MoodleSession.")

    cookies = {"MoodleSession": s_cookie}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/json"
    }

    # 1. Get grader page to retrieve contextid and assignmentid and sesskey
    grader_url = f"{m_url}/mod/assign/view.php?id={cmid}&action=grader&userid={userid}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, cookies=cookies) as client:
        g_resp = await client.get(grader_url)
        g_html = g_resp.text

        sesskey_m = re.search(r'["\']sesskey["\']\s*:\s*["\']([a-zA-Z0-9]+)["\']', g_html)
        if not sesskey_m:
            sesskey_m = re.search(r'sesskey=([a-zA-Z0-9]+)', g_html)
        sesskey = sesskey_m.group(1) if sesskey_m else ""

        assign_id_m = re.search(r'data-assignmentid="(\d+)"', g_html)
        if not assign_id_m:
            assign_id_m = re.search(r'["\']assignmentid["\']\s*:\s*(\d+)', g_html)
        assignment_id = int(assign_id_m.group(1)) if assign_id_m else None

        if not assignment_id or not sesskey:
            raise MoodleServiceError(f"Nepodařilo se zjistit interní ID úlohy nebo sesskey z Moodle (cmid={cmid}).")

        # 2. Map letter grade to scale option
        scale_val = moodle_grade_to_scale_id(grade_letter)

        # 3. Build urlencoded form data matching Moodle grading form
        form_params = {
            "grade": str(scale_val),
            "assignfeedbackcomments_editor[text]": comment_text,
            "assignfeedbackcomments_editor[format]": "1",
            "sendstudentnotifications": "1" if send_notifications else "0",
            "sesskey": sesskey,
            "action": "submitgrade",
            "userid": str(userid),
            "_qf__mod_assign_grade_form_" + str(userid): "1"
        }
        urlencoded_form = urllib.parse.urlencode(form_params)

        # 4. Call AJAX web service mod_assign_submit_grading_form
        service_url = f"{m_url}/lib/ajax/service.php?sesskey={sesskey}&info=mod_assign_submit_grading_form"
        payload = [
            {
                "index": 0,
                "methodname": "mod_assign_submit_grading_form",
                "args": {
                    "assignmentid": assignment_id,
                    "userid": userid,
                    "jsonformdata": json.dumps(urlencoded_form)
                }
            }
        ]

        post_resp = await client.post(service_url, json=payload, headers=headers)
        result = post_resp.json()

        if isinstance(result, list) and len(result) > 0:
            item = result[0]
            if item.get("error"):
                exc = item.get("exception", {})
                err_msg = exc.get("message", "Neznámá chyba z Moodle AJAX.")
                raise MoodleServiceError(f"Chyba při ukládání známky: {err_msg}")

        return {
            "success": True,
            "cmid": cmid,
            "userid": userid,
            "grade_letter": grade_letter,
            "scale_val": scale_val
        }


def parse_moodle_submission_filename(filename: str) -> Dict[str, str]:
    """
    Parses student name and user ID from Moodle filenames.
    """
    clean_name = filename.replace("\\", "/").strip()
    parts = clean_name.split("/")
    folder_part = parts[0] if len(parts) > 1 else ""
    file_part = parts[-1]

    match = re.search(r'^([^_]+(?:_[^_]+)*?)_(\d+)_assignsubmission_', folder_part or file_part)
    if match:
        student_raw = match.group(1).replace("_", " ").strip()
        moodle_user_id = match.group(2)
        return {
            "student_name": student_raw,
            "moodle_user_id": moodle_user_id,
            "raw_filename": file_part
        }

    match2 = re.search(r'^([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+(?:\s+[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][a-záčďéěíňóřšťúůýž]+)+)_(\d+)', folder_part or file_part)
    if match2:
        return {
            "student_name": match2.group(1).strip(),
            "moodle_user_id": match2.group(2),
            "raw_filename": file_part
        }

    return {
        "student_name": "",
        "moodle_user_id": "",
        "raw_filename": file_part
    }


async def download_moodle_assignment_zip(
    cmid: str, 
    group_id: str = "0",
    moodle_url: Optional[str] = None,
    session_cookie: Optional[str] = None
) -> bytes:
    """
    Downloads the entire submissions ZIP file for the given assignment and group filter.
    """
    cfg = get_moodle_config()
    m_url = (moodle_url or cfg["moodle_url"]).rstrip("/")
    s_cookie = (session_cookie or cfg["moodle_session"]).strip()

    if not s_cookie:
        raise MoodleAuthError("Chybí cookie MoodleSession.")

    download_url = f"{m_url}/mod/assign/view.php?id={cmid}&action=downloadall"
    if group_id and group_id != "0":
        download_url += f"&group={group_id}"

    cookies = {"MoodleSession": s_cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }

    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True, cookies=cookies) as client:
        resp = await client.get(download_url, headers=headers)
        if "login.microsoftonline.com" in str(resp.url) or "login/index.php" in str(resp.url):
            raise MoodleAuthError("Relace MoodleSession vypršela nebo je neplatná.")

        if resp.status_code != 200:
            raise MoodleServiceError(f"Moodle vrátil chybu při stahování: HTTP {resp.status_code}")

        content = resp.content
        if len(content) < 4 or content[:4] != b'PK\x03\x04':
            html_text = resp.text
            if "Žádné odevzdané úkoly" in html_text or "No submissions found" in html_text or "nic nebylo odevzdáno" in html_text.lower():
                raise MoodleServiceError("Pro tuto úlohu a vybranou skupinu nebyly v Moodle nalezeny žádné odevzdané úkoly.")
            raise MoodleServiceError("Moodle nevrátil platný ZIP soubor s protokoly. Zkontrolujte, zda jsou v Moodle odevzdány nějaké práce.")

        return content


def extract_submissions_from_zip(zip_bytes: bytes) -> List[Dict[str, Any]]:
    """
    Extracts PDF submissions from downloaded Moodle ZIP bytes.
    Returns list of items: { student_name, moodle_user_id, filename, file_bytes }
    """
    submissions = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as z:
        for zinfo in z.infolist():
            if zinfo.is_dir():
                continue
            fname = zinfo.filename
            if not fname.lower().endswith(".pdf"):
                continue

            file_bytes = z.read(zinfo)
            parsed_meta = parse_moodle_submission_filename(fname)

            submissions.append({
                "student_name": parsed_meta["student_name"],
                "moodle_user_id": parsed_meta["moodle_user_id"],
                "original_zip_path": fname,
                "clean_filename": Path(fname).name,
                "file_bytes": file_bytes
            })

    return submissions


def build_moodle_feedback_zip(protocols: List[Dict[str, Any]]) -> bytes:
    """
    Builds a feedback ZIP compatible with Moodle's 'uploadfeedbackzip' feature.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in protocols:
            pdf_bytes = p.get("pdf_bytes")
            if not pdf_bytes:
                continue

            student_name = p.get("student_name", "Student")
            moodle_user_id = p.get("moodle_user_id") or ""
            filename = p.get("filename") or f"{student_name}_opraveno.pdf"

            if moodle_user_id:
                entry_name = f"{student_name}_{moodle_user_id}_assignsubmission_file_{filename}"
            else:
                entry_name = f"{student_name}_assignsubmission_file_{filename}"

            z.writestr(entry_name, pdf_bytes)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
