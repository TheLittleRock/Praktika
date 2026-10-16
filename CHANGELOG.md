# Changelog

Všechny významné změny v projektu **Praktika Evaluation Studio** jsou zaznamenány v tomto souboru.

Formát vychází ze standardu [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/) a projekt dodržuje [Sémantické verzování](https://semver.org/lang/cs/).

## [2.11.0] - 2026-10-16

### 🚀 Novinky a vylepšení ve verzi 2.11.0

#### 📐 Ostré pravoúhlé zvýraznění textu v exportovaném PDF
- **Vzhled shodný s aplikací**: Zvýrazněný text je v exportovaném PDF vykreslen jako čistý pravoúhlý obdélník s pevnou podtrhávací linkou na účaří textu (35% krytí).
- **Konec zaoblených pilulek v Chromium**: Odstraněna nativní vrstva `add_highlight_annot`, která v prohlížečích Chrome a Brave způsobovala nevzhledné zakulacování a deformaci hran textových bloků.

#### 💬 Odstranění duplicitních ikon volných poznámek
- **Čistá nativní ikona**: Vypuštěna vlastní kreslená vektorová bublina; v PDF zůstává pouze jediná nativní ikona PDF prohlížeče doplněná o přehledný indexový štítek `[X]`.

#### ✍️ Plynulé vyhlazování kreslení perem (Ink Smoothing)
- **Chaikinův vyhlazovací algoritmus**: Tahy perem jsou ve webovém canvasu (`pdf_viewer.js`) i v exportním modulu (`pdf_service.py`) automaticky vyhlazovány pomocí sub-divizního algoritmu rohů (Chaikin / B-spline).
- **Filtrace mikropohybů**: Vstupní vzorkování filtruje drobné chvění ruky a micro-jitter (body bližší než 1.8 px), díky čemuž jsou volné křivky organické, plynulé a přirozené.

#### 📑 Závěrečná stránka „Přehled hodnocení a poznámek“ (Appendix)
- **Kompletní přehled komentářů**: Na konec PDF se automaticky generuje strukturovaná příloha s kartami všech poznámek (`[1]`, `[2]`, ...), kontextovými výňatky zvýrazněného textu a srážkami bodů pro Moodle.
- **Obousměrné PDF odkazy**: Kliknutím na číslo poznámky `[X]` v textu protokolu čtenář okamžitě skočí na příslušnou kartu v příloze; kliknutím na tlačítko `Zpět na str. X ↗` se okamžitě vrátí na přesné místo v textu protokolu.

#### 📱 QR kód & Veřejný studentský náhled (`/v/{share_token}`)
- **QR kód na 1. straně**: V hlavičkové kartě hodnocení na první straně PDF je vložen QR kód a klikací hypertextový odkaz směřující na zabezpečený veřejný náhled.
- **Responzivní studentské zobrazení**: Student si může bez nutnosti přihlášení otevřít přehled hodnocení na libovolném zařízení (PC, tablet, mobil), prohlédnout si známku, body, rozpis srážek, interaktivní PDF náhled s tooltipy a stáhnout opravený soubor.

---

## [2.10.0] - 2026-10-16

### 🚀 Novinky a vylepšení ve verzi 2.10.0

#### 🎯 Nástroj Výběr a správa anotací na plátně
- **Aktivní označení tvarů**: Nástroj *Výběr textu / posun* (klávesa `V`) umožňuje kliknutím označit jakýkoliv nakreslený prvek (obdélník, šipku, pero, vepsaný text, poznámku).
- **Posun tažením (Drag & Drop)**: Označený prvek lze chytit a myší přesunout na nové místo v protokolu se zachováním přesných PDF souřadnic.
- **Okamžité smazání**: Klávesy `Delete` a `Backspace` smažou vybranou anotaci bez nutnosti otevírání editačního okna.
- **Nezávislost barev**: Dokončený obdélník i kresba si trvale uchovává zvolenou barvu; pozdější změna barvy v nástrojové liště ji retroaktivně nepřebarví.

#### 🤖 AI Asistent hodnocení & Lokalizace
- **Okamžité schvalování a zamítání na plátně**: Tlačítka `✓ Aplikovat` a `✕ Zahodit` přímo na štítku návrhu v textu PDF okamžitě promítnou anotaci do plátna i bočního panelu bez zpoždění či nutnosti znovunačtení dokumentu.
- **Oprava párování v databázi**: Odstraněna chyba párování indexů při schvalování dílčích návrhů z rozsáhlého seznamu.
- **Preference jazyka AI**: Do uživatelského nastavení přidána volba výchozího jazyka výstupů AI (*Čeština*, *Slovenština*, *Angličtina*, *Automaticky dle protokolu*). Asistent tak dostává zpětnou vazbu ve svém rodném jazyce i při hodnocení cizojazyčného protokolu.
- **Bohatší detekce chyb**: Zvýšena citlivost analýzy na 15–35+ konkrétních věcných a syntaktických nedostatků (interpunkce rovnic, chybějící čárka před ", kde", velká písmena po vzorcích, chybějící errorbary a odchylky v násobcích σ).

#### 🖨️ Exportované PDF & Moodle integrace
- **Dedikovaná Moodle poznámka na 1. straně**: Detailní rozpis srážek byl vyjmut z plochy hlavičkové karty a umístěn jako samostatná Acrobat poznámka v záhlaví 1. strany protokolu, obsahující kompletní formátovaný text pro vložení do LMS Moodle.
- **Oprava UTF-16 diakritiky**: Texty komentářů jsou ukládány s Unicode BOM (`\ufeff`), což zajišťuje bezchybné zobrazení českých a slovenských znaků (`ř, š, č, ě, ž, ť, ď`) v prohlížečích Chrome, Brave i Adobe Acrobat.
- **Acrobat-style zvýraznění**: V PDF exportu se zvýraznění vykresluje jako ostrý poloprůhledný obdélník s pevnou podtrhávací linkou odpovídající přesnému účaří textu.

#### 📍 Plovoucí indikátor ukládání (Autosave Badge)
- Indikátor stavu uložení byl přemístěn do levého dolního rohu samotného plátna PDF (`position: absolute`). Plovoucí badge tak nezakrývá tlačítka `Dokončit` ani ozubené kolo v bočním panelu.

#### 📚 Sjednocení verzování a nová dokumentace
- **Single Source of Truth**: Centrální definice verze v `app/version.py` napojená do FastAPI metadat, rozhraní i API endpointu `GET /api/version`.
- **Automatizovaná dokumentace**: Příručka v Material for MkDocs rozdělena na specializovanou sekci pro asistenty a pro administrátory, doplněná o strojově generované animace (Playwright + ffmpeg) a ostré snímky zachycující reálný stav aplikace s reálnými protokoly.

---

## [2.9.0] - 2026-10-16

### 🎨 Korekční PDF Studio & Vizuály
- **Plovoucí indikátor ukládání**: Převeden na minimalistickou indikaci bez pozadí, která se zobrazuje přes PDF a nezmenšuje viewport.
- **Barevná paleta v editoru komentáře**: Přidána volba šesti barevných teček přímo do karty komentáře pro okamžitou změnu barvy konkrétního zvýraznění.
- **Sladění výplně obdélníků**: Výplň rámečku na plátně se dynamicky generuje jako polo-průhledná barva (15 %) odpovídající barvě obrysu.
- **Acrobat-style bublina**: Vektorový piktogram komentáře s bílými linkami textu plně kompatibilní s Adobe Acrobatem.

---

## [2.8.0] - 2026-10-16

### ⚙️ Hromadné operace & Správa databáze
- **Hromadné operace**: Možnost hromadného přiřazení asistenta, změny termínu a mazání protokolů.
- **Správa databáze v nastavení**: Zálohování SQLite databáze jedním kliknutím, stahování záložních souborů a obnova databáze.
- **Diagnostika a stav**: Informace o využití diskového prostoru, počtu protokolů a stavu databáze přístupné správcům.
- **Plynulé zoomování**: Oddělení citlivosti plynulého touchpad zoomu od krokového posunu myší.

---

## [2.7.0] - 2026-10-15

### 🤖 Dokovatelný AI panel & Předvolby
- **Oboustranné dokování AI panelu**: Možnost přichycení panelu k pravému i levému okraji okna nebo jeho volné plovoucí umístění.
- **Integrace s Google Gemini**: Hloubková analýza laboratorních protokolů z fyzikálních praktik.
- **Systém osobních předvoleb**: Ukládání vlastních často používaných komentářů tlačítkem `⭐ Uložit jako předvolbu`.

---

## [2.6.0] - 2026-10-15

### 🖥️ In-App Dialogy & Filtrování
- **Kompletní odstranění nativních browser promptů**: Nahrazení systémových `prompt()`, `confirm()` a `alert()` komponentou `AppModal`.
- **Filtrování dle předmětů**: Dynamické filtrování úloh a protokolů podle předmětů FPRA1, FPRA2 a ZFM2.

---

## [2.5.0] - 2026-10-15

### 🚀 Zdokonalení AI asistenta & Pravidla hodnocení
- **Implementace pravidel hodnocení**: Zapracování 26 snímků z prezentace "Nejčastější chyby v protokolech".
- **Povinný rozbor diskuze**: Automatická souhrnná anotace na nadpisu diskuze k argumentaci a interpretaci výsledků.
- **Zpřesněný krokový zoom**: Zavedení tlačítek `Fit` a `Fill` pro přizpůsobení velikosti okna.

---

## [2.4.0] - 2026-10-14

### 📂 Autodetekce & Struktura předmětů
- **Inteligentní autodetekce metadat**: Automatické rozpoznání jména studenta, předmětu a čísla úlohy z textu protokolu a názvu souboru.
- **Oddělení rolí**: Zabezpečení rozhraní správce a omezení úprav cizích protokolů pro asistenty.

---

## [2.3.0] - 2026-10-14

### 🤖 AI Syntéza manuálu zadání
- **Automatická syntéza zadání na hodnotící manuál**: Generování strukturované rubriky pro asistentovo hodnocení z nahraného PDF návodu.
- **0-Flicker HiDPI zoom**: Odstranění problikávání a skákání po dokončení zoomování při použití HiDPI rastrování.

---

## [2.2.0] - 2026-10-14

### 🎨 HiDPI Vektorové vykreslování & Acrobat styl
- **HiDPI / Retina vykreslování**: Využití `window.devicePixelRatio` pro dokonalou ostrost matematických rovnic v PDF.js.
- **Červené přeškrtnutí textu**: Anotační nástroj pro přeškrtnutí textu červenou linkou.
- **Klávesové zkratky**: Jednopísmenné přepínání anotačních nástrojů podle Adobe Acrobat (`V`, `H`, `S`, `T`, `N`, `P`, `R`, `A`).

---

## [2.1.0] - 2026-10-14

### 🌟 Acrobat Workflow & Moodle export
- **TextLayer výběr textu**: Označení textu myší a vložení žlutého zvýraznění s plovoucí bublinou.
- **Nástroj Typewriter**: Přímé vepsání textu do PDF protokolu.
- **Výstup 1 a 2 pro Moodle**: Generování souboru `bodovani.txt` a jednořádkového souhrnu.

---

## [2.0.0] - 2026-10-14

### 🏗️ Monolitická architektura
- Přechod na backend na bázi **FastAPI + SQLite + PDF.js + PyMuPDF**.
- Čtyřpilířový hodnotící systém po 0.125 b: Výsledky (max 3), Diskuze (max 3), Formát (max 2), Chyby (max 2).
- Vypalování anotací a hlavičky do PDF protokolu.
