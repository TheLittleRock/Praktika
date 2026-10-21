"""
Praktika Moodle Integration Service
Handles web-based interaction with Moodle (specifically ČVUT https://moodle-vyuka.cvut.cz)
without requiring official REST API tokens:
1. Course structure scraping (assignments and groups)
2. Submissions ZIP downloading and parsing
3. Feedback ZIP uploading and Gradebook worksheet updating
"""

import re
import io
import zipfile
import shutil
import tempfile
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

            # Check if redirected to login / SSO
            if "login.microsoftonline.com" in final_url or "login/index.php" in final_url or "shibboleth" in final_url.lower():
                return False, "Relace MoodleSession vypršela nebo je neplatná (přesměrováno na přihlášení ČVUT)."

            if resp.status_code != 200:
                return False, f"Moodle vrátil HTTP kód {resp.status_code}."

            # Find course title
            html = resp.text
            title_match = re.search(r'<h1[^>]*class="[^"]*page-header-headings[^"]*"[^>]*>(.*?)</h1>', html, re.DOTALL | re.I)
            if not title_match:
                title_match = re.search(r'<title>(.*?)</title>', html, re.DOTALL | re.I)
            
            raw_title = title_match.group(1) if title_match else f"Kurz #{course_id}"
            title = clean_html_text(raw_title)
            # Remove generic suffix like '| Moodle ČVUT'
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
    Scrapes the course page to extract all assignments and available groups.
    """
    cfg = get_moodle_config()
    m_url = (moodle_url or cfg["moodle_url"]).rstrip("/")
    c_id = (course_id or cfg["course_id"]).strip()
    s_cookie = (session_cookie or cfg["moodle_session"]).strip()

    if not s_cookie:
        raise MoodleAuthError("Chybí cookie MoodleSession. Zadejte ji prosím v Nastavení nebo se přihlaste.")

    target_url = f"{m_url}/course/view.php?id={c_id}"
    cookies = {"MoodleSession": s_cookie}
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, cookies=cookies) as client:
        resp = await client.get(target_url, headers=headers)
        if "login.microsoftonline.com" in str(resp.url) or "login/index.php" in str(resp.url):
            raise MoodleAuthError("Relace MoodleSession vypršela nebo je neplatná. Přihlaste se prosím znovu.")

        html = resp.text

        # 1. Parse course title
        title_match = re.search(r'<title>(.*?)</title>', html, re.I)
        course_title = clean_html_text(title_match.group(1)) if title_match else f"Kurz {c_id}"
        course_title = re.sub(r'\s*\|\s*Moodle.*$', '', course_title).strip()

        # 2. Parse assignments
        # In Moodle: <a class="aalink" href="https://moodle-vyuka.cvut.cz/mod/assign/view.php?id=12345">...<span class="instancename">Úloha 1...</span></a>
        assignments = []
        assign_regex = re.compile(
            r'href="[^"]*?/mod/assign/view\.php\?id=(\d+)"[^>]*>(?:(?!</a>).)*?<span[^>]*class="instancename"[^>]*>(.*?)</span>',
            re.DOTALL | re.I
        )
        for match in assign_regex.finditer(html):
            cmid = match.group(1)
            raw_name = clean_html_text(match.group(2))
            # Clean common trailing text like "Úkol" or "Assignment" that Moodle appends
            raw_name = re.sub(r'\s*(?:Úkol|Assignment)\s*$', '', raw_name, flags=re.I).strip()
            if not any(a["cmid"] == cmid for a in assignments):
                assignments.append({
                    "cmid": cmid,
                    "title": raw_name,
                    "section": ""
                })

        # Fallback if instancename span not matched: find all assign links
        if not assignments:
            fallback_regex = re.compile(r'href="[^"]*?/mod/assign/view\.php\?id=(\d+)"[^>]*>(.*?)</a>', re.DOTALL | re.I)
            for match in fallback_regex.finditer(html):
                cmid = match.group(1)
                text = clean_html_text(match.group(2))
                if text and not any(a["cmid"] == cmid for a in assignments):
                    assignments.append({
                        "cmid": cmid,
                        "title": text,
                        "section": ""
                    })

        # 3. Parse groups from the first assignment's grading table
        groups = [{"id": "0", "name": "Všichni účastníci (bez filtrování skupiny)"}]
        if assignments:
            first_cmid = assignments[0]["cmid"]
            grading_url = f"{m_url}/mod/assign/view.php?id={first_cmid}&action=grading"
            try:
                g_resp = await client.get(grading_url, headers=headers)
                g_html = g_resp.text
                # Find group selector: <select name="group" ...> ... <option value="123">Pondělí 14:00</option> ... </select>
                select_match = re.search(r'<select[^>]*name=["\']group["\'][^>]*>(.*?)</select>', g_html, re.DOTALL | re.I)
                if select_match:
                    opt_regex = re.compile(r'<option[^>]*value=["\'](\d+)["\'][^>]*>(.*?)</option>', re.DOTALL | re.I)
                    for opt in opt_regex.finditer(select_match.group(1)):
                        gid = opt.group(1)
                        gname = clean_html_text(opt.group(2))
                        if gid != "0" and not any(g["id"] == gid for g in groups):
                            groups.append({"id": gid, "name": gname})
            except Exception as e:
                print("Could not scrape groups from assignment grading page:", e)

        return {
            "course_id": c_id,
            "course_title": course_title,
            "assignments": assignments,
            "groups": groups
        }


def parse_moodle_submission_filename(filename: str) -> Dict[str, str]:
    """
    Parses a single file or directory name from a Moodle submission ZIP.
    Standard Moodle ZIP file naming conventions:
    1. 'Jakub Petržílek_123456_assignsubmission_file_protokol_6.pdf'
    2. 'Jakub Petržílek_123456_assignsubmission_file_/protokol_6.pdf'
    3. 'Petrzilek_Jakub_123456_file.pdf'
    """
    clean_name = filename.replace("\\", "/").strip()
    parts = clean_name.split("/")
    
    # If file is nested in student's directory: 'Jakub Petržílek_123456_assignsubmission_file_/protokol.pdf'
    folder_part = parts[0] if len(parts) > 1 else ""
    file_part = parts[-1]

    # Try matching on folder part or file part
    match = re.search(r'^([^_]+(?:_[^_]+)*?)_(\d+)_assignsubmission_', folder_part or file_part)
    if match:
        student_raw = match.group(1).replace("_", " ").strip()
        moodle_user_id = match.group(2)
        return {
            "student_name": student_raw,
            "moodle_user_id": moodle_user_id,
            "raw_filename": file_part
        }

    # Fallback pattern: '{First} {Last}_{ID}_...'
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

    # In Moodle: mod/assign/view.php?id={cmid}&action=downloadall&group={group_id}
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
        # Check if received content is a valid ZIP
        if len(content) < 4 or content[:4] != b'PK\x03\x04':
            # Check if Moodle returned an HTML page saying no submissions exist
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
    Each file in the ZIP must follow the student's submission prefix, e.g.:
    '{Student Name}_{moodle_id}_assignsubmission_file_{filename}.pdf'
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
