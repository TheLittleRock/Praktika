import os
import re
import json
import base64
import httpx
import fitz
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.database import get_db
from app.models import AIAnalysisResult, AIDeductionSuggestion, AIAnnotationSuggestion, AIChatMessage, AIChatResponse

DEFAULT_PHYSICS_GUIDELINES = """
ZÁVAZNÁ METODIKA PRO HODNOCENÍ FYZIKÁLNÍCH PROTOKOLŮ (vychází z oficiálních pokynů garantů a prezentace "Nejčastější chyby v protokolech"):

1. OBECNÉ ZÁSADY A STRUKTURA HODNOCENÍ:
- Objektivní, detailní, ale spravedlivé posouzení.
- Typické známky z protokolů bývají B a C (celkem 7.5 až 8.75 b ze 10 b). Cílem je poskytnout studentovi maximálně bohatou zpětnou vazbu k textu (mnoho konkrétních anotací), ale nezničit známku nesmyslným sčítáním drobných srážek!
- Pokud se stejná drobná formální chyba opakuje (např. chybějící mezera před jednotkou nebo chybně uvedené platné cifry na více místech): v textu označ KAŽDÝ výskyt (30 až 50+ anotací), ale v bodování vytvoř JEDNU SOUHRNNOU srážku za danou kategorii (např. -0.125 b nebo -0.25 b celkem), aby student neztratil body za jednu opakující se drobnost.
- Bodové hodnocení (celkem max 10.0 b, srážky VÝHRADNĚ v násobcích 0.125 b: 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0):
  * Výsledky (0.0 až 3.0 b): splnění všech úkolů ze zadání, správný postup, mezivýsledky, parametry fitu s nejistotami.
  * Diskuze (0.0 až 3.0 b): fyzikální rozbor výsledků, porovnání s tabulkou v σ, analýza systematických a náhodných chyb.
  * Formát a styl (0.0 až 2.0 b): pevná osnova, akademický styl, grafy s popisky, citace všech tabulek a grafů v textu.
  * Chyby a nejistoty (0.0 až 2.0 b): nejistoty u všech veličin, errorbary v grafech, správné zaokrouhlení.

2. POVINNÁ STRUKTURA A OSNOVA (pořadí nelze měnit):
- Hlavička → Pracovní úkoly → Použité přístroje (pomůcky) → Teoretický úvod → Postup měření → Vypracování → Diskuze → Závěr → Literatura → Přílohy.
- Pracovní úkoly se opisují ze zadání DOSLOVA (žádné parafrázování ani vymýšlení).
- Použité přístroje: uvedeny pouze skutečně použité pomůcky a přístroje.
- Teoretický úvod: vlastními slovy (max půl strany), vysvětlit fyzikální podstatu jevu (ne jen vzorce fitu). Všechny vzorce mají číslo (1), je na ně v textu odkazováno a jsou součástí věty: za vzorcem MUSÍ být čárka nebo tečka. Pokud po vzorci následuje výčet veličin se slovem "kde", musí být bezprostředně za vzorcem čárka a pokračování malým písmenem ", kde ...". Chybějící čárka před ", kde" nebo velké "Kde" je závažná syntaktická a typografická chyba. Všechny symboly ve vzorcích musí být definovány.
- Postup měření: "kuchařka" v přítomném čase 1. os. mn. č. ("odečítáme polohu", "používáme"), ze které lze měření zopakovat (uvést počet opakování).
- Vypracování a výsledky: dohledatelné rovnice, mezivýsledky a naměřená data.
- Literatura: patří VŽDY PŘED přílohy! Citace dle ČSN ISO 690 (uvedení autorů, názvu, roku, u webu datum citace).
- Přílohy: grafy a rozsáhlé tabulky mohou být v příloze.

3. AKADEMICKÝ STYL, GRAMATIKA A JAZYK (CZ i SK):
- Protokol může být v češtině nebo slovenštině. Jazyk komentářů a hodnocení VŽDY přizpůsob jazyku protokolu!
- Osoba a čas:
  * Teoretický úvod, Vypracování, Diskuze: výhradně 3. osoba, trpný rod (CZ: "hodnota byla určena fitem", SK: "hodnota bola určená fitom").
  * Postup měření: 1. os. mn. č., přítomný čas (CZ: "měříme čas", SK: "meriame čas").
  * Závěr: minulý čas (CZ: "změřili jsme", SK: "zmerali sme").
  * PŘÍSNÝ ZÁKAZ 1. osoby jednotného čísla ("změřil jsem", "vyšlo mi", "bych nedával")!
- ZÁKAZ TYPOGRAFICKÝCH A INDEXOVÝCH HALUCINACÍ VE VZORCÍCH:
  * Surový text extrahovaný z PDF ztrácí formátování LaTeXové sazby (dolní a horní indexy, mikro-mezery u exponentů a fonty). Ve vysázeném PDF jsou tyto vzorce (např. m₂c₂ nebo jednotky K⁻¹) vysázeny korektně!
  * PŘÍSNÝ ZÁKAZ kritizovat dolní či horní indexy ve vzorcích a chemických vzorcích (např. m2c2, t1, t2, K-1, H2O), chybějící mezery bezprostředně navazující na matematické indexy či tečky vzorců a kurzívu písem. Tyto zdánlivé chyby vznikají pouze extrakcí textu.
  * Soustřeď se na FAKTIČNOST A FYZIKU: platnost použitých rovnic, fyzikální odvození, správnost jednotek a řádů veličin.
  * Formát zápisu výsledků: (hodnota ± chyba) · 10ⁿ jednotka (např. (9,36 ± 0,08) · 10⁻³ kg·m²). V českém a slovenském textu se používá desetinná čárka.
  * FORMULACE A SROZUMITELNOST: Pokud věta v textu skutečně nedává smysl, je formulačně zmatená, neúplná nebo gramaticky vadná, označ ji a navrhni srozumitelnou akademickou opravu. Žádné zapomenuté zbytky kódu z LaTeXu / Pythonu ani nepřeložené anglické popisky.

4. ZAOKROUHLOVÁNÍ A CHYBY MĚŘENÍ:
- Chyba/nejistota měření se zaokrouhluje na 1 PLATNOU CIFRU (výjimečně 2, pouze pokud začíná číslicí 1).
- Výsledná hodnota MUSÍ končit na stejném řádovém místě jako její chyba: např. (12,345 ± 0,2) m/s je špatně, správně je (12,3 ± 0,2) m/s.
- Víc cifer neznamená přesnější měření! Zbytečná desetinná místa bez chyby jsou hrubou chybou.
- Každá naměřená i vypočtená hodnota MUSÍ mít svou chybu (včetně vah, barometru, stopek).
- Opakované měření: pod tabulkou uvést aritmetický průměr a jeho chybu, např. ε̄_d = (3,13 ± 0,03) rad·s⁻², a odkázat na vzorec.
- Převody jednotek a řád výsledku: zkontrolovat fyzikální smysl a řád (např. 1000,7 hPa = 100 070 Pa).

5. GRAFY A TABULKY:
- Všechny chybové úsečky v grafech se nazývají ERRORBARY a jsou povinné u všech naměřených bodů.
- Graf má sdělit závislost, ne zdobit:
  * Nadpis nepatří do plochy grafu, ale pod graf jako popisek "Obr. N. ...".
  * Osy musí obsahovat symbol veličiny a jednotku v hranatých závorkách: např. T [s], v [m·s⁻¹].
  * Body nesmí být spojeny lomenou čarou ("spojnice bodů"), ale pouze fyzikálně zdůvodněným fitem.
  * U rovnice fitu musí být uvedeny CHYBY VŠECH PARAMETRŮ FITU (ne surový vzorec z Excelu).
  * Grafy mohou být v příloze.
  * KAŽDÝ graf a tabulka MUSÍ být citována a diskutována v souvislém textu (např. "jak je vidět na Obr. 1", "hodnoty v Tab. 2"). Tabulky i grafy musí mít popisky schopné vysvětlit obsah samostatně.

6. DISKUZE VÝSLEDKŮ:
- Zákaz obecných výmluv: "lidský faktor", "chyba měřidla" nebo "zastaralý přístroj" NENÍ VYSVĚTLENÍ!
- Diskuze musí obsahovat:
  * Kvantitativní porovnání s tabulkovou či referenční hodnotou – spočítat, o kolik σ se výsledek liší (počet směrodatných odchylek) nebo relativní odchylku v %.
  * Pojmenování konkrétních zdrojů chyb (tření, tepelné ztráty, reakční doba aparatury), odhad jejich velikosti a směru.
  * Návrh, jak se chybám příště vyhnout.
  * Porovnání statistických a systematických chyb.
- POVINNÁ SOUHRNNÁ ANOTACE DISKUZE: Na nadpis sekce Diskuze VŽDY umísti anotaci s komplexním rozborem (co v diskuzi chybí, jak ji vylepšit a co je naopak zpracováno dobře).

7. ZÁVĚR:
- Odpovědět na VŠECHNY pracovní úkoly ze zadání v původním pořadí, stručně, v minulém čase, s výsledky i chybami a jednotkami.
- Závěr nesmí tvrdit víc, než ukazují čísla (pokud se hypotéza nepotvrdila, poctivě to přiznat).
"""

def get_ai_setting(key: str, default: str = "") -> str:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row and row[0] is not None:
        return str(row[0]).strip()
    return default

def save_ai_setting(key: str, value: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)")
    cur.execute("INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value).strip()))
    conn.commit()
    conn.close()

def get_gemini_api_key() -> str:
    val = get_ai_setting("gemini_api_key", "")
    if val:
        return val
    return os.environ.get("GEMINI_API_KEY", "").strip()

def save_gemini_api_key(key: str):
    save_ai_setting("gemini_api_key", key)

def get_candidate_models(preferred: Optional[str] = None) -> List[str]:
    pref = (preferred or get_ai_setting("gemini_model") or get_ai_setting("ai_model", "gemini-3.5-flash-lite")).strip()
    candidates = []
    if pref:
        candidates.append(pref)
    for m in ["gemini-3.5-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
        if m not in candidates:
            candidates.append(m)
    return candidates

async def generate_task_rubric(raw_text: str, task_name: str, task_number: int) -> str:
    """Uses Gemini to synthesize an uploaded task manual into a concise, high-value evaluation rubric for AI grading."""
    api_key = get_gemini_api_key()
    if not api_key:
        return raw_text[:20000]

    prompt = f"""Jsi vedoucí fyzikálního praktika na univerzitě.
Dostal jsi oficiální návod / zadání k laboratorní úloze:
Úloha {task_number}: {task_name}

TEXT NÁVODU K ÚLOZE:
{raw_text[:35000]}

TVŮJ ÚKOL:
Z tohoto návodu vytvoř stručný, přehledný, strukturovaný a nekompromisní HODNOTÍCÍ MANUÁL pro asistenta a AI, podle kterého se budou opravovat a bodovat studentské protokoly.

Vygeneruj text v češtině s touto pevnou strukturou:
1. CÍL A PRINCIP ÚLOHY:
   - Co přesně má student změřit, ověřit a stanovit.
2. POVINNÉ VÝSTUPY (TABULKY A GRAFY):
   - Které tabulky naměřených dat musí protokol obsahovat (jaké veličiny a jednotky).
   - Jaké grafy musí student sestrojit (co je na ose x a ose y, jaká křivka se fituje).
3. VÝPOČTY, VZORCE A NEJISTOTY:
   - Klíčové vztahy pro zpracování dat.
   - Jaké nejistoty (statistické typu A, z dělení stupnice typu B) musí být spočteny.
4. KRITICKÉ BODY A ČASTÉ CHYBY (na co se přísně zaměřit při opravování):
   - Pravidla zaokrouhlování (nejistoty na 1-2 platné číslice, shoda řádu výsledku).
   - Co nesmí chybět v diskuzi (srovnání s tabulkovou hodnotou, konkrétní systematické vlivy měřicí aparatury).
   - Typické chyby studentů u této konkrétní úlohy.

Napiš to stručně, jasně, v bodech a odrážkách, bez zbytečné omáčky.
"""
    models_to_try = get_candidate_models()
    for m in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(url, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2}
                })
                if resp.status_code == 200:
                    data = resp.json()
                    rubric = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if rubric:
                        return rubric
        except Exception as e:
            print(f"Error generating rubric with {m}:", e)
            continue
    return raw_text[:20000]

async def run_background_ai_analysis(proto_id: int):
    """Run AI analysis asynchronously in background and store proposals in database."""
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE protocols SET ai_status = 'analyzing' WHERE id = ?", (proto_id,))
        conn.commit()
        conn.close()

        res = await analyze_protocol(proto_id)

        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE protocols SET ai_proposals_json = ?, ai_status = 'ready' WHERE id = ?", (json.dumps(res.dict(), ensure_ascii=False), proto_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Background AI analysis failed for protocol {proto_id}:", e)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE protocols SET ai_status = 'failed' WHERE id = ?", (proto_id,))
        conn.commit()
        conn.close()

async def analyze_protocol(proto_id: int, custom_key: Optional[str] = None, custom_model: Optional[str] = None, language: Optional[str] = None) -> AIAnalysisResult:
    api_key = (custom_key or "").strip() or get_gemini_api_key()

    target_lang = (language or get_ai_setting("ai_language", "cs")).strip().lower()
    if target_lang == "sk":
        lang_directive = "JAZYK VÝSTUPŮ: Veškeré komentáře ('comment'), důvody srážek ('reason') i celkový souhrn ('summary') generuj striktně a výhradně ve SLOVENŠTINĚ."
    elif target_lang == "en":
        lang_directive = "LANGUAGE OF SUGGESTIONS: Generate all comments ('comment'), deduction reasons ('reason'), and the summary ('summary') strictly and exclusively in ENGLISH."
    elif target_lang == "auto":
        lang_directive = "JAZYK VÝSTUPŮ: Jazyk komentářů, srážek i souhrnu přizpůsob jazyku protokolu (čeština nebo slovenština)."
    else:
        lang_directive = "JAZYK VÝSTUPŮ: Veškeré komentáře ('comment'), důvody srážek ('reason') i celkový souhrn ('summary') generuj striktně a výhradně v ČEŠTINĚ."

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, m.name as measurement_name, m.number as measurement_number, m.code as measurement_code, m.instructions_text as measurement_instructions
    FROM protocols p
    JOIN measurements m ON p.measurement_id = m.id
    WHERE p.id = ?
    """, (proto_id,))
    row = cur.fetchone()

    # Load active teacher deduction presets from DB
    preset_rows = []
    try:
        cur.execute("SELECT category, pts, text FROM presets WHERE type = 'deduction' ORDER BY category, pts DESC")
        preset_rows = cur.fetchall()
    except Exception as e:
        print("Error fetching presets:", e)
    conn.close()

    if not row:
        raise ValueError("Protokol nenalezen")

    source_path = row["source_path"]
    if not source_path or not os.path.isfile(source_path):
        raise ValueError("Soubor protokolu nebyl nalezen na disku")

    doc = fitz.open(source_path)
    total_pages = len(doc)

    pdf_b64 = None
    try:
        with open(source_path, "rb") as f:
            pdf_bytes = f.read()
        if len(pdf_bytes) <= 20 * 1024 * 1024:
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    except Exception as e:
        print(f"Error reading PDF bytes for multimodal Gemini input: {e}")

    pages_text = []
    for idx, page in enumerate(doc):
        t = page.get_text()
        pages_text.append(f"--- STRANA {idx + 1} ---\n{t}")
    combined_text = "\n\n".join(pages_text)

    # Ensure Gemini API key is configured
    if not api_key:
        raise ValueError("Není nastaven platný API klíč pro Google Gemini. Zadejte jej prosím v Nastavení -> AI Asistent.")

    instructions = ""
    try:
        instructions = (row["measurement_instructions"] or "").strip()
    except Exception:
        pass
    instructions_block = f"\nMETODICKÉ POKYNY A ZADÁNÍ ÚLOHY:\n{instructions}\n" if instructions else ""

    presets_block = ""
    if preset_rows:
        p_lines = [f"- [{r['category'].upper()}] -{r['pts']} b: {r['text']}" for r in preset_rows]
        presets_block = "\nTYPICKÉ PŘEDVOLBY A ČASTÉ CHYBY NASTAVENÉ VYUČUJÍCÍM (Použij přednostně tyto formulace a přesné bodové sazby, pokud student udělal odpovídající chybu):\n" + "\n".join(p_lines) + "\n"

    # Call Gemini via REST API with candidate models
    prompt = f"""Jsi vedoucí fyzikálního praktika (garant předmětů FPRA1, FPRA2, ZFM2).
Tvým úkolem je detailně, nekompromisně a systematicky projít odevzdaný studentský laboratorní protokol, najít VŠECHNY faktické, konceptuální, formátové, typografické a syntaktické chyby a poskytnout studentovi maximálně bohatou a precizní zpětnou vazbu.

{lang_directive}

DŮLEŽITÉ POKYNY K HODNOCENÍ A VYHLEDÁVÁNÍ CHYB:
1. VYSOKÝ POČET NÁVRHŮ ANOTACÍ (EXHAUSTIVNÍ KONTROLA):
   - Vyhledej a označ v textu CO NEJVÍCE konkrétních chyb a nedostatků (usiluj o nalezení 15 až 40+ konkrétních míst k opravě, pokud jsou v textu nedostatky).
   - Nepřehlížej žádné drobné chyby! Zkontroluj každou větu, vzorec, číslo, jednotku, graf a tabulku.
2. INTERPUNKCE VZORCŮ A ZÁKAZ INDEXOVÝCH HALUCINACÍ (VELMI DŮLEŽITÉ!):
   - PŘÍSNÝ ZÁKAZ VYMEJŠLENÍ CHYB VE VZORCÍCH (INDEXY A MEZERY): Extrakce surového textu z PDF maže formátování indexů (např. m₂c₂ se extrahuje jako m2c2) a mezery u mocnin (např. K⁻¹.Tento). NIKDY nekritizuj chybějící dolní/horní indexy ve vzorcích a chemických značkách, kurzívu písma veličin ani chybějící mezery u matematických zápisů – ve vysázeném PDF jsou tyto prvky v pořádku!
   - INTERPUNKCE U VZORCŮ: Každý vzorec je součástí věty a musí mít odpovídající interpunkci (čárka nebo tečka na konci vzorce).
   - ČÁRKA PŘED ", kde": Pokud po samostatném vzorci následuje výčet veličin se slovem "kde", MUSÍ být za vzorcem čárka a pokračování malým písmenem ", kde ...". Chybějící čárka nebo velké "Kde" je závažná chyba.
   - SROZUMITELNOST A FORMULACE: Pokud je nějaká věta v textu skutečně nesrozumitelná, nedává smysl, má rozpadlý slovosled nebo obsahuje zakázanou 1. osobu jednotného čísla ("vyšlo mi"), označ ji a navrhni jasnou akademickou opravu.
   - DESETINNÁ ČÁRKA: V běžném textu se používá desetinná čárka (např. 3,14), nikoliv desetinná tečka.
3. GRAFY, TABULKY A KŘÍŽOVÉ ODKAZY:
   - Chybové úsečky v grafech se nazývají "errorbary" a jsou povinné u všech experimentálních bodů.
   - Všechny tabulky a grafy MUSÍ být citovány a diskutovány v souvislém textu (např. "jak je vidět na Obr. 1", "hodnoty v Tab. 2"). Tabulky i grafy musí mít popisky.
   - Osy grafů musí obsahovat symbol veličiny a jednotku v hranatých závorkách (např. T [s]).
   - U rovnice fitu musí být uvedeny chyby parametrů fitu a koeficient determinace (R²).
4. POVINNÉ SOUHRNNÉ ANOTACE PRO VŠECHNY HLAVNÍ SEKCE:
   - Na nadpis KAŽDÉ hlavní sekce protokolu VŽDY umísti souhrnnou anotaci (search_text nastaven na název daného nadpisu) s komplexním rozborem:
     * Úvod / Teoretický úvod (search_text: "Teoretický úvod" nebo "Úvod"): shrň faktickou a fyzikální správnost teorie, vysvětlení principu jevu, číslování vzorců a definici všech symbolů.
     * Postup měření / Metodika (search_text: "Postup měření" nebo "Metodika"): zhodnoť styl (1. os. mn. č. přítomný čas), reprodukovatelnost postupu a počet opakování.
     * Výsledky / Vypracování (search_text: "Výsledky" nebo "Vypracování"): zhodnoť úplnost splnění všech úkolů ze zadání, tabulky, dohledatelnost mezivýsledků a grafy.
     * Diskuze (search_text: "Diskuze" nebo "Diskusia"): komplexní rozbor porovnání s tabulkou v násobcích σ, fyzikální rozbor systematických chyb aparatury místo výmluv na lidský faktor a návrh opatření.
     * Závěr (search_text: "Závěr" nebo "Záver"): zhodnoť zodpovězení všech úkolů ze zadání v minulém čase, správné zaokrouhlení a věrnost naměřeným datům.
5. MÍRNĚJŠÍ ZNÁMKOVÁNÍ (CÍLIT TYPICKY NA ZNÁMKY B A C):
   - Mnoho anotací v textu pomáhá studentovi se učit, ale nesmí zničit celkovou známku.
   - Seskupuj opakující se formální prohřešky v 'deductions' do rozumných souhrnných položek (např. jedna srážka -0.25 b za chybějící interpunkci u vzorců a mezery před jednotkami v celém protokolu).
6. STRIKTNÍ ZAMĚŘENÍ POUZE NA REÁLNÉ CHYBY (PŘÍSNÝ ZÁKAZ PRÁZDNÝCH KONSTATOVÁNÍ):
   - Označuj VÝHRADNĚ skutečné chyby, nedostatky, neakademický styl, špatné zaokrouhlení nebo chybějící části.
   - PŘÍSNÝ ZÁKAZ PRÁZDNÝCH KONSTATOVÁNÍ A POCHVAL typu 'úkoly jsou opsány správně', 'cíl je v pořádku', 'vzorec sedí'. Anotace slouží jako místa k nápravě!
7. ANOTACE VÝHRADNĚ JAKO ZVÝRAZNĚNÍ (HIGHLIGHT):
   - Všechny položky v 'annotations' MUSÍ mít "type": "highlight".
8. TERMINOLOGIE:
   - Chybové úsečky v grafech striktně označuj pojmem "errorbary".
9. MULTIMODÁLNÍ VIZUÁLNÍ KONTROLA GRAFŮ A TABULEK (PŘÍMÉ PDF VSTUPY):
   - K dispozici máš originální vysázené PDF (připojené v datech) a zároveň extrahovaný text.
   - Využij vizuální vnímání PDF ke kontrole grafů (zda jsou vyneseny errorbary, zda osy mají symboly veličin a jednotky v hranatých závorkách, zda body nejsou spojeny lomenou čarou, zda je u fitu uvedena rovnice s chybami parametrů) a formátování tabulek.

ZADÁNÍ A HODNOTÍCÍ METODIKA ÚLOHY:
Úloha {row['measurement_number']}: {row['measurement_name']}
STUDENT: {row['student_name']}
{instructions_block}
{presets_block}
ZÁVAZNÁ KRITÉRIA PRO HODNOCENÍ:
{DEFAULT_PHYSICS_GUIDELINES}

SPECIÁLNÍ POŽADAVKY NA DETAIL A HLOUBKU KONTROLY (KONTROLUJ SYSTEMATICKY KAŽDOU STRANU):
1. KONTROLA CHYB V TEXTU: Projdi systematicky celý protokol od 1. do poslední strany a označ každou skutečnou chybu.
2. VÝSLEDKY A VYPRACOVÁNÍ (max 3.0 b):
   - Zkontroluj splnění VŠECH bodů ze zadání.
   - Zkontroluj jednotky ve všech tabulkách, vzorcích a grafech.
   - Jsou grafy kompletní? Mají grafy popsány obě osy včetně jednotek v [ ]? Jsou vyneseny errorbary? Jsou uvedeny parametry fitu s nejistotami?
   - Nejsou data v grafu spojena lomenou čarou? Nemá graf titulek uvnitř plátna?
3. DISKUZE A ZÁVĚR (max 3.0 b):
   - Je diskuze pouze suchým výčtem naměřených čísel ze závěru? Pokud ano, strhni 0.25 b!
   - Chybí porovnání výsledku s tabulkovou nebo referenční hodnotou v počtu směrodatných odchylek σ či v %? Pokud ano, strhni body!
   - Používá student výmluvy na "chybu lidského faktoru", "nepřesné měřidlo", "zastaralý přístroj"? Zkritizuj to – v diskuzi musí být konkrétní fyzikální rozbor systematických chyb (tření, tepelné ztráty, reakční doba aparatury)!
4. CHYBY A ZAOKROUHLOVÁNÍ (max 2.0 b):
   - Platné cifry: Nejistota (chyba měření) smí mít maximálně 1 platnou číslici (2 pouze pokud začíná číslicí 1)!
   - Výsledná hodnota MUSÍ končit na stejném řádovém místě jako její nejistota (např. v = (12.3 ± 0.2) m/s).
   - Každé nesmyslné číslo s mnoha desetinnými místy v textu označ!
5. FORMÁT A AKADEMICKÝ STYL (max 2.0 b):
   - Je dodržena pevná osnova protokolu?
   - Je v textu odkaz na každý graf a tabulku?
   - Je dodržen akademický styl (3. osoba / trpný rod v úvodu a diskuzi, 1. os. mn. č. v postupu, zákaz 1. os. jednotného čísla)?
   - Vzorce mají čísla a interpunkci, symboly jsou definovány, reference citovány dle ČSN ISO 690 před přílohami.

PRAVIDLA PRO BODOVÉ SRÁŽKY:
- Bodové srážky musí být VÝHRADNĚ v násobcích 0.125 b (0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0).
- Celkové skóre by u dokončených protokolů mělo typicky odpovídat známce B nebo C (cca 7.5 - 8.75 bodů).

TEXT ODEVZDANÉHO PROTOKOLU:
{combined_text[:35000]}

ODPOVĚZ VÝHRADNĚ VE FORMÁTU PŘÍSNÉHO JSON S TOUTO STRUKTUROU:
{{
  "scores": {{
    "vysledky": 2.625,
    "diskuze": 2.5,
    "format": 1.5,
    "chyby": 1.625,
    "total_points": 8.25
  }},
  "deductions": [
    {{
      "category": "chyby",
      "pts": 0.25,
      "reason": "Chybné zaokrouhlení výsledků a nejistot na více místech protokolu (chyba smí mít max 1-2 platné číslice a hodnota musí končit na stejném řádu)."
    }},
    {{
      "page": 2,
      "category": "diskuze",
      "pts": 0.25,
      "reason": "V diskuzi chybí kvantitativní porovnání výsledku v násobcích σ s tabulkovou hodnotou a rozbor systematických chyb aparatury."
    }},
    {{
      "page": 3,
      "category": "format",
      "pts": 0.25,
      "reason": "Graf 1 a Tabulka 2 nejsou referencovány v textu protokolu a graf obsahuje nevhodný titulek uvnitř obrázku."
    }},
    {{
      "page": 1,
      "category": "format",
      "pts": 0.125,
      "reason": "Neakademický styl vyjadřování (použita 1. osoba j.č. 'změřil jsem' místo neosobního pasiva)."
    }},
    {{
      "page": 3,
      "category": "chyby",
      "pts": 0.25,
      "reason": "V grafech zcela chybí errorbary pro naměřené body."
    }}
  ],
  "annotations": [
    {{
      "page": 2,
      "type": "highlight",
      "search_text": "Diskuze",
      "comment": "Souhrnné zhodnocení diskuze: V diskuzi chybí porovnání odchylky v násobcích σ s tabulkovou hodnotou a fyzikální rozbor systematických chyb aparatury (tření na dráze). Doporučuji doplnit kvantitativní zhodnocení a navrhnout opatření k minimalizaci chyb."
    }},
    {{
      "page": 1,
      "type": "highlight",
      "search_text": "9.812345",
      "comment": "Chyba zaokrouhlování: zaokrouhlete výsledek na 1 až 2 platné číslice odpovídající nejistotě."
    }},
    {{
      "page": 2,
      "type": "highlight",
      "search_text": "chybou měření byl lidský faktor",
      "comment": "Lidský faktor není fyzikální vysvětlení – rozeberte konkrétní vlivy (tření, reakční doba aparatury)."
    }},
    {{
      "page": 2,
      "type": "highlight",
      "search_text": "změřil jsem závislost",
      "comment": "Neakademický styl: používejte neosobní trpný rod (např. 'byla změřena závislost')."
    }},
    {{
      "page": 3,
      "type": "highlight",
      "search_text": "Graf 1:",
      "comment": "Graf není v textu protokolu přímo referencován a postrádá errorbary."
    }}
  ],
  "summary": "Podrobný a konstruktivní souhrn hlavních nedostatků protokolu a doporučení pro studenta."
}}

ZÁVAZNÁ PRAVIDLA:
1. Srážky bodů musí být v násobcích 0.125 b!
2. Pro každou anotaci musí 'search_text' obsahovat PŘESNÝ fragment textu (2 až 6 po sobě jdoucích slov) přímo z odevzdaného protokolu na dané straně 'page'.
3. Všechny anotace MUSÍ mít type: "highlight".
4. Vytvoř anotace v textu POUZE pro skutečné chyby a nedostatky. Každá anotace musí studentovi věcně sdělovat, co má špatně a jak to opravit. Žádná prázdná konstatování ani komentáře k věcem, které jsou v pořádku.
"""

    parts = []
    if pdf_b64:
        parts.append({
            "inline_data": {
                "mime_type": "application/pdf",
                "data": pdf_b64
            }
        })
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.35
        }
    }

    preferred_model = (custom_model or get_ai_setting("gemini_model") or get_ai_setting("ai_model", "gemini-3.5-flash-lite")).strip()
    models_to_try = get_candidate_models(custom_model)
    last_error = None
    fallback_note = None

    for model_name in models_to_try:
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        # Retry up to 2 times on transient spikes
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=75.0) as client:
                    resp = await client.post(gemini_url, json=payload)
                    if resp.status_code == 400 and pdf_b64:
                        # Fallback to text-only payload if multimodal inline_data is rejected
                        text_payload = {
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": payload["generationConfig"]
                        }
                        resp = await client.post(gemini_url, json=text_payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(raw_text)
                        
                        if model_name != preferred_model and last_error:
                            fallback_note = f"Požadovaný model '{preferred_model}' vrátil {last_error}. Byla použita záloha '{model_name}'."

                        return build_resolved_result(
                            proto_id, 
                            parsed, 
                            doc, 
                            model_used=f"Google Gemini ({model_name})",
                            preferred_model=preferred_model,
                            fallback_note=fallback_note
                        )
                    elif resp.status_code in [503, 429]:
                        last_error = f"chybu {resp.status_code} (přetížení / vyčerpaný limit kvóty)"
                        if attempt == 0:
                            import asyncio
                            await asyncio.sleep(1.2)
                            continue
                    else:
                        last_error = f"chybu {resp.status_code}: {resp.text[:80]}"
                        break
            except Exception as e:
                err_msg = str(e) or type(e).__name__
                last_error = f"chybu spojení ({err_msg})"
                print(f"Exception connecting to {model_name} (attempt {attempt+1}):", err_msg)
                if attempt == 0:
                    import asyncio
                    await asyncio.sleep(1.0)
                    continue
                break

    raise RuntimeError(f"AI asistent nemohl protokol vyhodnotit. Všechny dostupné Gemini modely selhaly: {last_error or 'Chyba připojení nebo vyčerpaná kvóta'}. Zkontrolujte připojení k internetu a platnost API klíče.")

def resolve_single_annotation(a: dict, doc: fitz.Document, idx: int, proto_id: int, proposal_id: Optional[str] = None) -> AIAnnotationSuggestion:
    try:
        page_num = max(1, min(len(doc), int(a.get("page", 1))))
    except Exception:
        page_num = 1
    annot_type = "highlight"
    search_text = str(a.get("search_text") or "").strip()
    comment = str(a.get("comment") or "")

    rect = None
    point = None

    if search_text:
        cleaned_search = " ".join(search_text.split())
        page = doc[page_num - 1]
        rects = page.search_for(cleaned_search)

        # Try stripped punctuation
        if not rects:
            stripped = cleaned_search.strip('.,;:"\'()[]{}')
            if stripped != cleaned_search:
                rects = page.search_for(stripped)

        # Try sub-phrases of 4, 3, or 2 words
        words = cleaned_search.split()
        if not rects and len(words) > 3:
            rects = page.search_for(" ".join(words[:4]))
        if not rects and len(words) > 2:
            rects = page.search_for(" ".join(words[:3]))
        if not rects and len(words) > 1:
            rects = page.search_for(" ".join(words[:2]))

        # Search across all other pages in the document
        if not rects and len(doc) > 1:
            for alt_idx, alt_p in enumerate(doc):
                alt_rects = alt_p.search_for(cleaned_search)
                if not alt_rects and len(words) > 2:
                    alt_rects = alt_p.search_for(" ".join(words[:3]))
                if alt_rects:
                    page_num = alt_idx + 1
                    rects = alt_rects
                    break

        if rects:
            r = rects[0]
            rect = [round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)]
            point = [round(r.x0, 1), round(r.y0, 1)]

    # Fallback coordinates if text wasn't directly found in text stream
    if not rect:
        p_height = doc[page_num - 1].rect.height if len(doc) >= page_num else 842.0
        top_y = min(p_height - 60.0, 110.0 + ((idx % 12) * 38.0))
        rect = [72.0, round(top_y, 1), 480.0, round(top_y + 18.0, 1)]
        point = [72.0, round(top_y, 1)]

    # Ensure valid non-zero dimensions
    if rect[2] <= rect[0]:
        rect[2] = rect[0] + 120.0
    if rect[3] <= rect[1]:
        rect[3] = rect[1] + 16.0

    return AIAnnotationSuggestion(
        proposal_id=proposal_id or f"annot_{proto_id}_{idx+1}",
        page=int(page_num),
        type=annot_type,
        search_text=search_text,
        comment=comment,
        rect=rect,
        point=point
    )

def build_resolved_result(proto_id: int, parsed: dict, doc: fitz.Document, model_used: str = "Gemini Flash", preferred_model: Optional[str] = None, fallback_note: Optional[str] = None) -> AIAnalysisResult:
    scores = parsed.get("scores", {"vysledky": 2.25, "diskuze": 2.0, "format": 1.5, "chyby": 1.5, "total_points": 7.25})
    raw_deductions = parsed.get("deductions", [])
    raw_annotations = parsed.get("annotations", [])
    summary = parsed.get("summary", "Protokol byl detailně analyzován asistentem AI.")

    deductions: List[AIDeductionSuggestion] = []
    for idx, d in enumerate(raw_deductions):
        raw_pts = float(d.get("pts", d.get("points", 0.25)))
        pts = round(round(raw_pts / 0.125) * 0.125, 3)
        if pts <= 0:
            pts = 0.125
        cat = str(d.get("category", "format")).lower()
        if cat not in ["vysledky", "diskuze", "format", "chyby"]:
            cat = "format"
            
        ded_page = None
        if "page" in d and d["page"]:
            try:
                ded_page = max(1, min(len(doc), int(d["page"])))
            except Exception:
                pass
        if not ded_page:
            d_reason_lower = str(d.get("reason", "")).lower()
            for a in raw_annotations:
                a_comm = str(a.get("comment", "")).lower()
                a_search = str(a.get("search_text", "")).lower()
                if any(w in a_comm or w in a_search for w in ["hlavič", "graf", "tabul", "zaokrouhl", "chyb", "jednotk", "vzorec", "nejistot", "pomůck", "postup"] if w in d_reason_lower):
                    try:
                        ded_page = int(a.get("page", 1))
                        break
                    except Exception:
                        pass
        if not ded_page:
            ded_page = 1

        deductions.append(AIDeductionSuggestion(
            proposal_id=f"ded_{proto_id}_{idx+1}",
            category=cat,
            pts=pts,
            reason=d.get("reason", "Chyba v protokolu"),
            page=ded_page
        ))

    annotations: List[AIAnnotationSuggestion] = []
    for idx, a in enumerate(raw_annotations):
        annotations.append(resolve_single_annotation(a, doc, idx, proto_id))

    return AIAnalysisResult(
        protocol_id=proto_id,
        scores=scores,
        deductions=deductions,
        annotations=annotations,
        summary=summary,
        model_used=model_used,
        preferred_model=preferred_model,
        fallback_note=fallback_note
    )

def merge_ai_results(existing_data: dict, new_result: AIAnalysisResult) -> AIAnalysisResult:
    """Merges newly discovered deductions and annotations with existing proposals, avoiding duplicates."""
    proto_id = new_result.protocol_id

    # 1. Deductions
    existing_deds = existing_data.get("deductions", [])
    merged_deds = []
    seen_ded_keys = set()

    for d in existing_deds:
        reason = str(d.get("reason", "")).strip().lower()
        cat = str(d.get("category", "")).strip().lower()
        key = (cat, reason[:40])
        seen_ded_keys.add(key)
        merged_deds.append(AIDeductionSuggestion(
            proposal_id=d.get("proposal_id") or f"ded_{proto_id}_{len(merged_deds)+1}",
            category=d.get("category", "format"),
            pts=float(d.get("pts", d.get("points", 0.25))),
            reason=d.get("reason", ""),
            page=int(d.get("page", 1)) if d.get("page") else 1
        ))

    for d in new_result.deductions:
        reason = d.reason.strip().lower()
        cat = d.category.strip().lower()
        key = (cat, reason[:40])
        if key not in seen_ded_keys:
            seen_ded_keys.add(key)
            d.proposal_id = f"ded_{proto_id}_{len(merged_deds)+1}"
            merged_deds.append(d)

    # 2. Annotations
    existing_annots = existing_data.get("annotations", [])
    merged_annots = []
    seen_annot_keys = set()

    for a in existing_annots:
        page = int(a.get("page", 1))
        txt = str(a.get("search_text", "")).strip().lower()
        comment = str(a.get("comment", "")).strip().lower()
        key = (page, txt[:30] if txt else comment[:30])
        seen_annot_keys.add(key)
        merged_annots.append(AIAnnotationSuggestion(
            proposal_id=a.get("proposal_id") or f"annot_{proto_id}_{len(merged_annots)+1}",
            page=page,
            type=a.get("type", "highlight"),
            search_text=a.get("search_text"),
            comment=a.get("comment", ""),
            rect=a.get("rect"),
            point=a.get("point")
        ))

    for a in new_result.annotations:
        page = int(a.page)
        txt = str(a.search_text or "").strip().lower()
        comment = str(a.comment or "").strip().lower()
        key = (page, txt[:30] if txt else comment[:30])
        if key not in seen_annot_keys:
            seen_annot_keys.add(key)
            a.proposal_id = f"annot_{proto_id}_{len(merged_annots)+1}"
            merged_annots.append(a)

    summary = new_result.summary
    if existing_data.get("summary") and existing_data["summary"] != summary:
        summary = f"{existing_data['summary']}\n\n[Doplňující analýza]: {summary}"

    return AIAnalysisResult(
        protocol_id=proto_id,
        scores=new_result.scores,
        deductions=merged_deds,
        annotations=merged_annots,
        summary=summary,
        model_used=new_result.model_used,
        preferred_model=new_result.preferred_model,
        fallback_note=new_result.fallback_note
    )

async def chat_with_ai(
    proto_id: int, 
    user_message: str, 
    custom_key: Optional[str] = None, 
    custom_model: Optional[str] = None, 
    language: Optional[str] = None
) -> AIChatResponse:
    """Interactively process a question or grading assignment task in AI chat for a given protocol."""
    api_key = (custom_key or "").strip() or get_gemini_api_key()
    if not api_key:
        raise ValueError("Není nastaven platný API klíč pro Google Gemini. Zadejte jej prosím v Nastavení -> AI Asistent.")

    target_lang = (language or get_ai_setting("ai_language", "cs")).strip().lower()
    if target_lang == "sk":
        lang_directive = "JAZYK ODPOVĚDÍ: Veškeré textové odpovědi i případné komentáře v anotacích generuj striktně a výhradně ve SLOVENŠTINĚ."
    elif target_lang == "en":
        lang_directive = "LANGUAGE OF REPLIES: Generate all replies and annotation comments strictly and exclusively in ENGLISH."
    else:
        lang_directive = "JAZYK ODPOVĚDÍ: Veškeré textové odpovědi i případné komentáře v anotacích generuj striktně a výhradně v ČEŠTINĚ."

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    SELECT p.*, m.name as measurement_name, m.number as measurement_number, m.code as measurement_code, m.instructions_text as measurement_instructions
    FROM protocols p
    JOIN measurements m ON p.measurement_id = m.id
    WHERE p.id = ?
    """, (proto_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise ValueError("Protokol nenalezen")

    existing_chat_json = row["ai_chat_json"] or "[]"
    try:
        chat_history = json.loads(existing_chat_json)
    except Exception:
        chat_history = []

    source_path = row["source_path"]
    if not source_path or not os.path.isfile(source_path):
        conn.close()
        raise ValueError("Soubor protokolu nebyl nalezen na disku")

    doc = fitz.open(source_path)

    pdf_b64 = None
    try:
        with open(source_path, "rb") as f:
            pdf_bytes = f.read()
        if len(pdf_bytes) <= 20 * 1024 * 1024:
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    except Exception as e:
        print(f"Error reading PDF bytes for chat multimodal Gemini input: {e}")

    pages_text = []
    for idx, page in enumerate(doc):
        t = page.get_text()
        pages_text.append(f"--- STRANA {idx + 1} ---\n{t}")
    combined_text = "\n\n".join(pages_text)

    instructions = (row["measurement_instructions"] or "").strip()
    instructions_block = f"\nMETODICKÉ POKYNY A ZADÁNÍ ÚLOHY:\n{instructions}\n" if instructions else ""

    # Format recent history as text for Gemini prompt
    history_lines = []
    for h in chat_history[-10:]:
        role_label = "Vyučující" if h.get("role") == "user" else "AI Asistent"
        history_lines.append(f"{role_label}: {h.get('text', '')}")
    history_text = "\n".join(history_lines) if history_lines else "Zatím žádná předchozí konverzace."

    prompt = f"""Jsi AI asistent pro hodnocení a konzultaci laboratorních fyzikálních protokolů v aplikaci Praktika.
Spolupracuješ s vysokoškolským pedagogem / asistentem, který opravuje odevzdaný protokol studenta.

{lang_directive}

KONTEXT PROTOKOLU:
- Úloha: {row['measurement_number']}. {row['measurement_name']} (Kód: {row['measurement_code']})
- Student: {row['student_name']}
{instructions_block}

TEXT ODEVZDANÉHO PROTOKOLU:
{combined_text[:35000]}

DOSAVADNÍ HISTORIE CHATU:
{history_text}

AKTUÁLNÍ ZPRÁVA VYUČUJÍCÍHO:
{user_message}

POKYNY PRO ODPOVĚĎ:
1. DVĚ MOŽNOSTI CHOVÁNÍ:
   A) OTÁZKA / DOTAZ: Pokud vyučující pokládá obecný, faktický, fyzikální nebo metodický dotaz (např. "Jak zní vzorec pro Poissonovu konstantu?", "Jaké jsou tabulkové hodnoty mědi?"), odpověz srozumitelně, přesně a odborně v textu 'reply'. Pole 'annotations' ponech prázdné: [].
   B) KOREKČNÍ ÚKOL / POŽADAVEK NA OZNAČENÍ CHYB: Pokud vyučující zadává úkol zkontrolovat konkrétní část protokolu nebo označit chyby v textu (např. "Zkontroluj diskuzi a přidej komentáře k nedostatkům", "Označ chyby ve vzorcích teorie"):
      - V textu 'reply' shrň výsledek své kontroly a co jsi našel.
      - V poli 'annotations' vrať konkrétní seznam návrhů anotací k označení v textu protokolu!
2. PRAVIDLA PRO ANOTACE V 'annotations':
   - 'page': 1-indexované číslo strany v protokolu.
   - 'type': vždy "highlight".
   - 'search_text': PŘESNÝ krátký úsek textu (2 až 6 slov) z dané strany protokolu, který má být zvýrazněn.
   - 'comment': věcná, konstruktivní a přesná poznámka pro studenta k nalezené chybě.
   - ZÁKAZ indexových/mezerových halucinací ve vzorcích: surový text z PDF maže formátování indexů (např. m2c2 místo m₂c₂). NIKDY nekritizuj dolní indexy ani chybějící mezery u exponentů. Soustřeď se na fyzikální platnost, jednotky, chybná tvrzení a nesrozumitelné formulace.
3. MULTIMODÁLNÍ VIZUÁLNÍ KONTEXT:
   - Jako součást vstupu máš přiložen celý vysázený PDF soubor protokolu.
   - Pokud se vyučující ptá na grafy, tabulky, schémata či vizuální zpracování protokolu, vycházej přímo z vizuální podoby stránek v PDF.

ODPOVĚZ VÝHRADNĚ VE FORMÁTU PŘÍSNÉHO JSON S TOUTO STRUKTUROU:
{{
  "reply": "Textová odpověď pro vyučujícího...",
  "annotations": [
    {{
      "page": 1,
      "type": "highlight",
      "search_text": "text z protokolu",
      "comment": "Pedagogický komentář k chybě..."
    }}
  ]
}}
"""

    chat_parts = []
    if pdf_b64:
        chat_parts.append({
            "inline_data": {
                "mime_type": "application/pdf",
                "data": pdf_b64
            }
        })
    chat_parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": chat_parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.3
        }
    }

    models_to_try = get_candidate_models(custom_model)
    raw_response = None
    last_error = None

    for model_name in models_to_try:
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            async with httpx.AsyncClient(timeout=65.0) as client:
                resp = await client.post(gemini_url, json=payload)
                if resp.status_code == 400 and pdf_b64:
                    # Fallback to text-only payload if multimodal inline_data is rejected
                    text_payload = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": payload["generationConfig"]
                    }
                    resp = await client.post(gemini_url, json=text_payload)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    raw_response = json.loads(raw_text)
                    break
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:80]}"
        except Exception as e:
            last_error = str(e)
            continue

    if not raw_response or not isinstance(raw_response, dict):
        conn.close()
        raise RuntimeError(f"AI asistent neodpověděl: {last_error or 'Neznámá chyba'}")

    reply_text = str(raw_response.get("reply", "")).strip()
    raw_annots = raw_response.get("annotations", [])
    if not isinstance(raw_annots, list):
        raw_annots = []

    resolved_annots: List[AIAnnotationSuggestion] = []
    ts = int(datetime.now().timestamp() * 1000)
    for i, a in enumerate(raw_annots):
        prop_id = f"chat_{proto_id}_{ts}_{i+1}"
        resolved = resolve_single_annotation(a, doc, i, proto_id, proposal_id=prop_id)
        resolved_annots.append(resolved)

    # Append to chat history
    now_iso = datetime.now().isoformat()
    chat_history.append({
        "role": "user",
        "text": user_message,
        "timestamp": now_iso,
        "annotations_added": 0
    })
    chat_history.append({
        "role": "assistant",
        "text": reply_text,
        "timestamp": now_iso,
        "annotations_added": len(resolved_annots)
    })

    # Save to DB
    cur.execute("UPDATE protocols SET ai_chat_json = ? WHERE id = ?", (json.dumps(chat_history, ensure_ascii=False), proto_id))

    # If annotations were generated, also merge them into protocols.ai_proposals_json
    if resolved_annots:
        existing_proposals_raw = row["ai_proposals_json"]
        if existing_proposals_raw:
            try:
                ep_data = json.loads(existing_proposals_raw)
            except Exception:
                ep_data = {}
        else:
            ep_data = {}
        ep_annots = ep_data.get("annotations", [])
        for ra in resolved_annots:
            ep_annots.append(ra.dict())
        ep_data["annotations"] = ep_annots
        cur.execute("UPDATE protocols SET ai_proposals_json = ? WHERE id = ?", (json.dumps(ep_data, ensure_ascii=False), proto_id))

    conn.commit()
    conn.close()

    return AIChatResponse(
        reply=reply_text,
        annotations=resolved_annots,
        history=[AIChatMessage(**m) for m in chat_history]
    )

def get_protocol_chat_history(proto_id: int) -> List[AIChatMessage]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT ai_chat_json FROM protocols WHERE id = ?", (proto_id,))
    row = cur.fetchone()
    conn.close()
    if not row or not row[0]:
        return []
    try:
        data = json.loads(row[0])
        return [AIChatMessage(**m) for m in data]
    except Exception:
        return []

def clear_protocol_chat_history(proto_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE protocols SET ai_chat_json = '[]' WHERE id = ?", (proto_id,))
    conn.commit()
    conn.close()



