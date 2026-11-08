# Praktika Evaluation Studio – AI Agent Architecture & Context Guide (`AGENT_GUIDE.md`)

Tento dokument slouží jako **kompletní kontext a architektonický průvodce pro AI agenty** (i lidské vývojáře) pracující na projektu **Praktika Evaluation Studio**.

---

## 1. 🎯 O projektu (Executive Summary)

**Praktika Evaluation Studio** je webová aplikace vyvinutá pro pedagogy a asistenty fyzikálních praktik na **ČVUT v Praze (FJFI)**. Slouží k efektivní, férové a poloautomatizované opravě odevzdaných studentských laboratorních protokolů ve formátu PDF s přímou integrací na univerzitní **ČVUT Moodle** a s asistencí **AI modelů** (Google Gemini & OpenAI-kompatibilní modely jako Groq Llama 3.3 70B).

### Klíčové principy a doménová pravidla:
1. **Diskrétní bodování po 0.125 b**: Bodové srážky a hodnocení se počítají striktně v násobcích `0.125 b` (osminy bodu).
2. **ČVUT Moodle integrace**: Přímé stahování odevzdaných protokolů a nahrávání opravených PDF včetně známek a komentářů do kurzu (např. kurz `16880`) bez nutnosti administrátorského API klíče. Autentizace probíhá přes bezpečnostní cookie `MoodleSession`.
3. **Serverové SSO přihlašování s 2FA**: Webový formulář předá přihlašovací údaje do headless Playwright prohlížeče na serveru, který projde ČVUT Microsoft Entra ID i interní ADFS (`logon.ms.cvut.cz`) a zprostředkuje 2FA výzvu (Outlook / Authenticator číselná shoda či SMS/TOTP kód).
4. **Striktní bezpečnost (Zero Password Persistence)**: Uživatelské ČVUT heslo se **nikdy neukládá** do databáze ani na disk; v paměti procesu se okamžitě přepíše prázdným řetězcem.
5. **Keep-Alive Heartbeat**: Na pozadí serveru běží každých 15 minut asynchronní ping na Moodle, který udržuje relaci stále aktivní a brání vypršení session kvůli nečinnosti.

---

## 2. 🧱 Technologický stack

* **Backend**: Python 3.10+, FastAPI, Starlette, Uvicorn, SQLite3 (v režimu WAL pro vysokou souběžnost), Pydantic v2.
* **Prohlížečová automatizace**: Playwright (Chromium headless) pro serverové získávání MoodleSession přes SSO a ADFS.
* **PDF Engine**: PyMuPDF (`pymupdf`, dříve `fitz`) pro vykreslování, extrakci textu a vkládání razítek, komentářů a srážek do opravených PDF.
* **Frontend**: Vanilla JavaScript (ES6+ bez těžkých frameworků, čistý modulární návrh), Jinja2 šablony, CSS3 Custom Properties (plná podpora Dark / Light mode), PDF.js (Mozilla) pro vykreslování na plátno.
* **AI Providers**: Google Gemini API (`google-genai` SDK) a univerzální OpenAI-kompatibilní provider (`httpx` klient pro Groq, OpenRouter, Cerebras, Ollama, DeepSeek).
* **Dokumentace & Testy**: Material for MkDocs, `unittest`, Starlette `TestClient`.

---

## 3. 📂 Kde co hledat (Struktura projektu)

```text
Praktika/
├── app/
│   ├── main.py                 # FastAPI aplikace, routy, lifespan úlohy (keepalive), REST API
│   ├── config.py               # Cesty k datům (DATA_DIR, DB_PATH), systémové konstanty, úlohy U01–U12
│   ├── database.py             # SQLite inicializace, migrace, CRUD (protokoly, uživatelé, audity, zálohy)
│   ├── models.py               # Pydantic schémata požadavků a odpovědí
│   ├── moodle_service.py       # Moodle scraping (synchronizace prací, upload známek, keepalive ping)
│   ├── moodle_login_service.py # Headless Playwright přihlašování (Microsoft SSO + ČVUT ADFS + 2FA)
│   ├── ai_service.py           # Multi-provider AI analýza protokolů (Gemini, Groq, OpenAI API)
│   ├── pdf_engine.py           # Práce s PDF pomocí PyMuPDF (anotace, razítka, export)
│   ├── auth.py                 # JWT autentizace, bcrypt hashování hesel, cookie správa
│   ├── version.py              # Aktuální verze systému (např. "2.23.0")
│   ├── templates/
│   │   ├── index.html          # Hlavní SPA šablona s modálními okny, lištami a nastavením
│   │   └── student_view.html   # Samostatné zobrazení pro studenty
│   └── static/
│       ├── js/
│       │   ├── app.js          # Hlavní stav aplikace, Moodle dialog, nastavení, správa uživatelů
│       │   ├── grading.js      # Workspace opravování, rubriky, srážky po 0.125 b, presety chyb
│       │   └── pdf_viewer.js   # Vykreslování PDF, kreslicí plátno, vkládání poznámek
│       └── css/
│           └── app.css         # Styly, rozvržení oken, animace, témata
├── data/                       # Perzistentní data (SQLite DB, protokoly, zálohy) - ignorováno v git
├── docs/                       # Dokumentace projektu pro MkDocs (architektura, návody, changelog)
├── tests/                      # Sady automatických integračních a jednotkových testů (test_v2_*.py)
├── Dockerfile                  # Produkční Docker image (instaluje Python závislosti + Chromium)
├── docker-compose.yml          # Konfigurace pro nasazení kontejneru
├── requirements.txt            # Python balíčky
├── CHANGELOG.md                # Kompletní historie verzí projektu dle Keep a Changelog
└── AGENT_GUIDE.md              # Tento dokument
```

---

## 4. 🔍 Důležité komponenty a toky dat

### A. Moodle SSO přihlašování (`app/moodle_login_service.py`):
1. Uživatel zadá přihlašovací údaje ve webovém okně (`index.html` -> `App.submitMoodleCredentials()`).
2. Server spustí headless Chromium v persistentním profilu `data/moodle_browser_profile`.
3. Navštíví `https://moodle-vyuka.cvut.cz/login/index.php`, vyplní `#i0116` a klikne na Další.
4. Microsoft detekuje federaci a přesměruje na `https://logon.ms.cvut.cz/adfs/ls/...`.
5. Na ČVUT ADFS skript vyplní `#passwordInput` a klikne na `<span id="submitButton">Sign in</span>` (okamžitě vymaže heslo z paměti).
6. Microsoft zobrazí volbu 2FA ověření -> skript vybere `Approve a request on my Outlook mobile app`.
7. Skript zachytí 2místné číslo v `#idRichContext_DisplaySign` a nastaví stav `awaiting_2fa_number`.
8. Webový frontend v poll smyčce (`pollInteractiveMoodleLogin()`) ihned zobrazí číslo uživateli.
9. Po schválení na telefonu skript zachytí cookie `MoodleSession`, uloží ji do SQLite a souboru `data/moodle_session.json` a nastaví stav `success`.

### B. Moodle Keep-Alive Heartbeat (`app/moodle_service.py` & `app/main.py`):
* Funkce `_moodle_keepalive_loop()` běží jako asynchronní úloha ve FastAPI lifespanu.
* Každých 15 minut odesílá lehký HTTP GET dotaz s cookie `MoodleSession` na `moodle-vyuka.cvut.cz`.
* Tím udržuje session živou a zabraňuje timeoutu nečinnosti na straně PHP Moodle.

### C. AI Asistent (`app/ai_service.py`):
* Podporuje dva režimy:
  1. **Google Gemini**: Oficiální modely generace 3.x (`gemini-3.8-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`). Má 90s timeout a automatický fallback při HTTP 429.
  2. **Univerzální OpenAI-kompatibilní provider**: Libovolné Base URL (např. `https://api.groq.com/openai/v1`). Výchozí doporučený model je `llama-3.3-70b-versatile` na Groq (zdarma, extrémně rychlý).

---

## 5. 🛠️ Vývoj, testování a nasazení

### Spuštění testů:
Každá nová funkcionalita má svůj testovací soubor v adresáři `tests/`. Před commitem musí projít všechny testy:
```bash
./venv/bin/python -m unittest discover -s tests -p "test_*.py"
# nebo jednotlivě:
./venv/bin/python tests/test_v2_23_0.py
```

### Kontrola dokumentace:
Dokumentace se generuje pomocí MkDocs v přísném režimu (žádné neplatné odkazy):
```bash
./venv/bin/mkdocs build --strict
```

### Správa verzí a Git:
1. Verze se zvyšuje v [`app/version.py`](file:///home/ubuntu_laptop/Python/Praktika/app/version.py).
2. Záznam se přidá na začátek [`CHANGELOG.md`](file:///home/ubuntu_laptop/Python/Praktika/CHANGELOG.md) a [`docs/changelog.md`](file:///home/ubuntu_laptop/Python/Praktika/docs/changelog.md).
3. Vývoj probíhá na větvi `dev`, po otestování se merguje do `main` a obě větve se pushují na GitHub.

---

## 6. 🤖 Instrukce pro nového AI agenta (Prompt Template)

Při zakládání nového chatu s AI asistentem stačí vložit následující zadání:

```markdown
Pracujeme na projektu **Praktika Evaluation Studio** (webová aplikace pro hodnocení laboratorních protokolů z fyzikálních praktik na ČVUT).
Než začneš cokoliv dělat, detailně si přečti soubor `AGENT_GUIDE.md` v kořenu projektu, kde najdeš přehled architektury, použité technologie, strukturu souborů a doménová pravidla (např. srážky po 0.125 b, Moodle SSO přihlašování, Keep-Alive atd.).
Všechny změny prováděj na větvi `dev`, udržuj testy zelené (`tests/test_*.py`) a dodržuj bezpečnostní zásady (zero storage pro hesla).
```
