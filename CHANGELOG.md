# Changelog

Všechny významné změny v projektu **Praktika Evaluation Studio** jsou zaznamenány v tomto souboru.

Formát vychází ze standardu [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/) a projekt dodržuje [Sémantické verzování](https://semver.org/lang/cs/).

---

## [2.5.0] - 2026-10-15

### 🚀 Novinky a vylepšení ve verzi 2.5.0

#### 🖥️ Kompletní odstranění nativních browser promptů (In-App Dialogy)
- Veškerá systémová volání `prompt()`, `confirm()` a `alert()` byla zcela nahrazena integrovaným oknem `AppModal` s profesionálním designem ladícím s aplikací.
- Plynulá úprava existujících srážek bodů přímo přes elegantní formulář se zachováním hodnot a klávesovými zkratkami Enter / Escape.
- Tlačítka shrnutí přejmenována na `📋 Souhrn` (jednořádkový přehled) a `📄 Bodování pro Moodle` (strukturovaný rozpis srážek pro studenta). Textové pole pro srážku se automaticky vertikálně přizpůsobuje délce textu.

#### 🤖 AI Asistent hodnocení & Oboustranné dokování
- **Flexibilní dokování panelu AI**: Panel lze volně oddokovat a přetahovat myší. Při přiblížení k levému i pravému okraji obrazovky se zobrazí vizuální náhled snapnutí a panel se animovaně ukotví.
- **Okamžité zobrazení na plátně**: Návrhy AI se promítnou do plátna ihned po dokončení analýzy bez nutnosti znovuotevření protokolu.
- **Výhradně zvýrazňovací anotace**: AI již nenavrhuje přeškrtávání, ale striktně zvýraznění textu s komentářem.
- **Pravidla podle prezentace "Nejčastější chyby v protokolech"**:
  - Implementováno všech 26 snímků z prezentace.
  - Zvláštní důraz na diskuzi (povinný souhrnný komentář u nadpisu diskuze k argumentaci a chybějícím interpretacím).
  - Používání termínu "errorbary", kontrola odkazů na grafy a tabulky v textu.
  - Mírnější a spravedlivé hodnocení (typicky známky B a C) se seskupováním podobných chyb do sdružených srážek.
  - Plná podpora češtiny i slovenštiny.
- **Indikace stavu API klíče**: Pokud asistent nebo správce nemá nastaven platný klíč Gemini, panel AI asistenta i nastavení na to zřetelně upozorní.

#### 🔍 Zpřesněné zoomování & Dotykové ovládání
- Krokový zoomovací pás: `[50%, 65%, 80%, 100%, 125%, 150%, 175%, 200%, 250%, 300%]`.
- Nová tlačítka v ovládací liště: `−`, `+`, `Fit` (přizpůsobit výšce okna) a `Fill` (přizpůsobit šířce okna).
- Tlumená citlivost Ctrl+kolečko/touchpad zabraňující nechtěným skokům mezi měřítky.

#### 📂 Předměty (FPRA1, FPRA2, ZFM2), Autodetekce a Šablony
- Termíny cvičení jsou rozděleny podle předmětů (`FPRA1`, `FPRA2`, `ZFM2`). Výběr úloh v okně nahrávání se dynamicky filtruje podle předmětu vybraného termínu.
- Inteligentní autodetekce hlavičky při nahrání protokolu: automaticky z textu protokolu a názvu souboru rozpozná jméno studenta, předmět, číslo úlohy a spáruje termín cvičení.
- Předvolby a časté chyby jsou odděleny pro každého asistenta zvlášť s možností uložit libovolný komentář přímo tlačítkem `⭐ Uložit jako předvolbu`.

#### 🔒 Zabezpečení a Role (Správce vs. Asistent)
- Asistenti mají v rozhraní zakázáno modifikovat úlohy a termíny jiných cvičení (zobrazení pouze pro čtení).
- Asistenti nemohou přemazávat ani mazat protokoly přiřazené jiným hodnotitelům.
- Filtr podle hodnotitele v přehledu protokolů je zobrazen pouze administrátorům.
- Každý asistent si může v nastavení spravovat svůj vlastní osobní Gemini API klíč.

---

## [2.3.0] - 2026-10-14

### 🤖 AI Syntéza manuálu zadání & Hyper-kritický hodnotitel
- **Automatická syntéza zadání na hodnotící manuál (rubriku)**:
  - Při nahrání návodu k laboratorní úloze v PDF nebo TXT formátu Gemini AI zanalyzuje text a vytvoří stručný, strukturovaný hodnotící manuál (Cíl a princip, Povinné tabulky/grafy, Výpočty a chyby, Kritické body a časté chyby).
  - Tlačítko `✨ Přeformulovat AI na manuál` v dialogu pokynů umožňuje kdykoliv manuál z textu vygenerovat či aktualizovat.
- **Hyper-kritický a nekompromisní AI hodnotitel**:
  - Přísná kontrola všech prohřešků: chybějící errorbary v grafech, neúplné jednotky, suchý výčet v diskuzi, výmluvy na "lidský faktor", nedodržení platných cifer u nejistot a chybějící neosobní pasivum.
- **Interaktivní vizuální návrhy v textu PDF plátna**:
  - Návrhy AI se přímo vykreslují na příslušných stránkách PDF (přeškrtávací červená čára, purpurový rámeček, plovoucí akční lišta).
  - Kliknutí na kterýkoliv návrh v pravém AI panelu okamžitě plynule odscrolluje dokument na konkrétní místo v protokolu s pulzujícím fialovým rámečkem.
  - Tlačítka `✓ Aplikovat` a `✕ Zahodit` fungují nezávisle z plátna i z postranního panelu, bez zasekávání nebo přeskočení ostatních návrhů.

### 🔍 0-Flicker & 0-Jump plynulý zoom
- **Odstranění problikávání a skákání po dokončení zoomu**:
  - Plynulá CSS transformace je zachována i během asynchronního dopočítávání rastru v PDF.js.
  - Vykreslování probíhá na pozadí do nového canvasu a výměna je provedena synchronně bez jediného bílého snímku či posunu scrollbaru.

### 🎨 Dolaďování profesionálního UI a ovládacích prvků
- **Odstranění přetékání tlačítka v opravně**:
  - Tlačítko `← Protokoly` ve vertikální nástrojové liště je upraveno pro šířku 84 px a nikdy nepřetéká.
- **Odlišení ikonek v navigaci**:
  - Ikonka pro *Termíny a úlohy* změněna z ozubeného kolečka na moderní kalendář s checkmarkem (`calendar-check`), čímž je okamžitě odlišitelná od *Nastavení*.
- **Čisté uspořádání patičky ve sbaleném režimu**:
  - V sbaleném postranním panelu (v Opravně PDF) je nahoře umístěn modrý čtvercový avatar uživatele `[ SA ]` (36×36 px) a přímo pod ním tmavé tlačítko s ozubeným kolečkem nastavení `[ ⚙ ]` (36×36 px), přesně podle preferovaného dřívějšího rozvržení.

---

## [2.2.0] - 2026-10-14

### 🤖 AI Asistent hodnocení (Google Gemini 1.5 Flash & Heuristika)
- **Automatická kontrola a předpříprava opravy protokolu**:
  - Tlačítko `✨ AI Asistent` v nástrojové liště Opravny PDF provede hloubkovou analýzu textu protokolu s využitím bezplatného Google Gemini 1.5 Flash API (či vestavěné offline fyzikální heuristiky).
  - Připraví strukturované návrhy srážek bodů přesně v násobcích 0.125 b ve standardních kategoriích (*Výsledky*, *Diskuze*, *Formát*, *Chyby*).
  - Využívá PyMuPDF vektorové vyhledávání v textu PDF (`page.search_for(search_text)`) pro přesné určení souřadnic a návrh konkrétních zvýraznění, přeškrtnutí a poznámek.
- **Interaktivní schvalovací okno (AI Review Modal)**:
  - Přehledný souhrn a seznam všech navržených srážek i anotací s možností hromadného i individuálního výběru checkboxem.
  - Asistent má nad vším plnou kontrolu – schválí jen to, co uzná za vhodné, a může vše dále v aplikaci libovolně upravit.
- **Správa API klíče v nastavení**:
  - Nová záložka `🤖 AI Asistent` v nastavení aplikace pro zadání bezplatného Gemini API klíče s indikátorem stavu a odkazem na Google AI Studio.

### 🎨 Profesionální moderní UI & Vzhled ve stylu VS Code a Acrobat
- **Přepracovaný tmavý režim (Dark Mode)**:
  - Odstraněn modravý nádech; nahrazen neutrálními profesionálními šedými tóny inspirovanými editorem VS Code (`#1e1e1e` pozadí, `#252526` karty a panely, `#383838` ohraničení, `#007acc` primární akcent).
  - Pozadí plátna PDF nastaveno na neutrální tmavou barvu `#282828` ve stylu Adobe Acrobat.
- **Rozšířený a přehledný boční panel nástrojů (76 px)**:
  - Nástrojová lišta vlevo rozšířena na 76 px, každé tlačítko má čistou vektorovou SVG ikonu a pod ní čitelný štítek (Výběr, Zvýraznit, Škrtnout, Vepsat, Poznámka, Pero, Rámeček, Šipka, Zpět).
  - Odstraněno jakékoliv přetékání textu (např. dřívější ořezané `Rozdě...`).
- **Plovoucí komentářové bubliny ladící s novým motivem**:
  - Okamžitá reakce při označení textu, hlavička s profilem asistenta, rychlé předvolby a tlačítka pro uložení.

### 🔍 Ostrost textu a plynulé zoomování
- **Retina / HiDPI vektorová ostrost písma**:
  - Použití `transform: [dpr, 0, 0, dpr, 0, 0]` v kontextu PDF.js společně s `devicePixelRatio` zajišťuje krystalicky ostrý vektorový text a matematické vzorce při jakémkoliv měřítku bez artefaktů.
- **Fix zachování pozice při zoomování**:
  - Zoomování si přesně pamatuje aktuální stránku i vertikální posun v okně; odstraněno nežádoucí skákání na první stránku při změně měřítka.
  - Akcelerovaný a responzivnější rendering.

### 📁 Standardy pojmenování a správa metadat
- **Oficiální kódy předmětů (FPRA1, FPRA2, ZFM2)**:
  - Zimní praktika: `FPRA1` (např. složka `FPRA1_2026ZS`).
  - Letní praktika: `FPRA2` a `ZFM2` (např. složka `FPRA2_2026LS`, `ZFM2_2026LS`).
- **Zjednodušené názvy složek termínů**:
  - Praktika trvají vždy 4 hodiny od celé hodiny – složky jsou nyní stručné a přehledné: `Pondeli_8h`, `Pondeli_8h_F3` (odstraněny zbytečné nuly v minutách a časy konce).
- **Úprava metadat protokolů přímo v rozhraní**:
  - Nové tlačítko `✏️` u každého protokolu v tabulce přehledu. Umožňuje opravit jméno studenta, změnit semestr, termín nebo přiřazenou laboratorní úlohu.

### ℹ️ Záložka "O aplikaci" a Changelog
- **Centrální přehled verze**:
  - Zobrazení aktuální verze `v2.2.0` v navigační liště.
  - V nastavení přibyla nová záložka `ℹ️ O aplikaci` s informacemi o systému a integrovaným interaktivním prohlížečem historie změn (Changelog).

### 🚀 Zvýšení produktivity a pokročilé nástroje opraváře
- **Plynulý Touchpad / Trackpad Zoom bez zoomování webu**:
  - Gesto roztažení/sevření prstů (pinch-to-zoom) a `Ctrl` + kolečko myši plynule zoomují zobrazené PDF plátno namísto celého webového rozhraní prohlížeče.
  - Využívá GPU akcelerovaný CSS náhled v reálném čase (60 fps) s debouncovaným (120 ms) ostrým vykreslením v HiDPI rozlišení.
  - Nový odznak s procentem zvětšení (`125%`) v nástrojové liště, kliknutím resetuje zoom na výchozí hodnotu.
- **Klávesové zkratky podle Adobe Acrobat**:
  - Jednopísmenné přepínání nástrojů (pokud není aktivní psaní do vstupního pole):
    - `V`: Posun / výběr textu (Pan)
    - `H`: Zvýraznění textu (Highlight)
    - `S`: Červené přeškrtnutí textu (Strikeout)
    - `T`: Text do PDF (Typewriter)
    - `N`: Vložení poznámky / bubliny (Note)
    - `P`: Červené kreslící pero (Pen)
    - `R`: Obdélníkový rámeček (Rect)
    - `A`: Směrová šipka (Arrow)
    - `+` / `=`: Zvětšit měřítko (+15 %)
    - `-` / `_`: Zmenšit měřítko (-15 %)
    - `0`: Reset měřítka na 125 %
  - Globální akční zkratky:
    - `Ctrl + Z`: Krok zpět (Undo anotace)
    - `Ctrl + S`: Uložit rozpracovaný koncept
    - `Ctrl + Enter`: Dokončit hodnocení a vygenerovat opravené PDF
    - `Alt + Vlevo` / `Alt + Vpravo`: Okamžitý přechod na předchozího / dalšího studenta
    - `Esc`: Zavření plovoucí bubliny nebo otevřeného nastavení/modálu
- **Plynulé přepínání mezi studenty v Opravně**:
  - Tlačítka `◀ Předchozí` a `Další ▶` přímo v hlavičce studia i plovoucí liště na celou obrazovku umožňují plynule pokračovat v opravování dalšího protokolu bez nutnosti návratu do hlavního přehledu.
- **Červené přeškrtnutí textu (Strikeout Tool)**:
  - Nový anotační nástroj pro přeškrtnutí chybného textu či vzorce červenou vektorovou linkou s možností připojit vysvětlující komentář v bublině.
  - Vypaluje se jako nativní PDF anotace přeškrtnutí (`fitz.Page.add_strikeout_annot`).
- **Kopírování výsledků jedním kliknutím**:
  - V bodovací kartě přibyly tlačítka pro okamžité zkopírování jednořádkového souhrnu (Výstup 1 pro IS) a textového rozpisu bodů (Výstup 2 pro `bodovani.txt`) do schránky s vizuální toast notifikací.
- **Vizuální ukazatel bodového stavu**:
  - Grafický ukazatel (Progress bar) v bodovací kartě přehledně zobrazuje aktuální zisk bodů (0 až 10 b) s dynamickým barevným podbarvením (zelená pro výborné, modrá pro dobré, oranžová pro hraniční a červená pro nedostatečné).
- **Hromadné stahování v ZIP archivu**:
  - Nový endpoint `GET /api/export/zip` a tlačítko `📦 Stáhnout ZIP` v přehledu. Zabalí všechna opravená PDF i soubory `bodovani.txt` odpovídající aktuálnímu filtru (semestr, termín, úloha) do přehledné adresářové struktury.
- **Hromadné nahrávání protokolů (Multi-file Batch Upload)**:
  - Dialog nahrávání podporuje výběr více souborů najednou s automatickou extrakcí příjmení studenta z názvu souboru (např. `FPRA1_Boril_uloha1.pdf` -> `Boril`) a ukazatelem průběhu nahrávání.
- **Export známek do CSV pro Microsoft Excel**:
  - Endpoint `GET /api/export/csv` a tlačítko `📊 Export CSV` generuje tabulku výsledků v kódování UTF-8 s BOM a oddělovačem středník (`;`), připravenou pro bezproblémové otevření v českém Excelu i import do studijních systémů.
- **Nový stav protokolu "K přepracování" (Revision)**:
  - Tlačítko `⟳ K přepracování` v Opravně pro protokoly vyžadující opravu od studenta, včetně oranžového statusového štítku a možnosti filtrování.
- **Přiřazování protokolů asistentům**:
  - Správce aplikace může v tabulce přehledu vybrat asistenta, kterému je protokol přidělen k opravě.

---

## [2.1.0] - 2026-10-14

### 🌟 Zásadní novinky a přepracování rozhraní (Adobe Acrobat Workflow)
- **Ostré vykreslování PDF ve vysokém rozlišení (HiDPI / Retina)**:
  - Přidána podpora `window.devicePixelRatio` pro rendering pláten PDF.js. Texty, grafy i tabulky v protokolu jsou nyní dokonale ostré bez jakéhokoliv rozmazání.
- **Skutečný výběr textu myší (PDF.js TextLayer)**:
  - Implementována transparentní textová vrstva synchronizovaná s plátnem. Umožňuje označit konkrétní slova, věty či rovnice přímo kurzorem myši a následně aplikovat žluté zvýraznění s komentářem.
- **Plovoucí komentářové bubliny ve stylu Adobe Acrobat**:
  - Odstraněna nepraktická vyskakovací okna prohlížeče (`prompt()`). Komentáře se nyní zadávají do moderní plovoucí karty přímo vedle označeného textu.
  - Karta obsahuje jméno a iniciálu hodnotitele, čas vložení, pole pro text, rychlé předvolby ("čipy") a volitelný přepínač pro automatické promítnutí srážky do bodování.
- **Nástroj přímého psaní do textu (Typewriter / Psací stroj)**:
  - Přidán nástroj pro přímé vepsání textu kamkoliv do PDF protokolu červeným písmem. Vypaluje se jako nativní vektorový text (`fitz.Page.insert_text`), ideální pro doplňování poznámek přímo k výpočtům studenta.
  - Odstraněno nepotřebné razítko "K přepracování".
- **Vertikální nástrojová lišta (Acrobat styl)**:
  - Přidána možnost přepnout lištu nástrojů na vertikální postranní panel vlevo. Tím se uvolní maximum vertikálního prostoru pro čtení a anotování protokolu.
  - Přepínatelné v nastavení aplikace (horizontální vs vertikální lišta).
- **Moderní tmavý režim (Dark Mode)**:
  - Kompletní podpora tmavého režimu (`data-theme="dark"`) s plynulým přepínáním přímo v horní liště i v nastavení.
  - Všechny panely, modály a formuláře mají vyladěné kontrastní barvy.
- **Nastavení aplikace v překryvném okně (Overlay Modal)**:
  - Implementováno centrální nastavení přístupné přes ozubené kolo s 5 specializovanými záložkami:
    1. *Vzhled & Rozhraní*: Volba motivu (světlý/tmavý) a pozice nástrojové lišty.
    2. *Správa laboratorních úloh*: Přidávání, přejmenování a mazání úloh rozdělených podle typu (ZS, LS, ZFM).
    3. *Časté chyby & Předvolby*: Oddělená správa předvoleb pro srážky bodů (v násobcích 0.125 b) a pro textové komentáře do PDF.
    4. *Správa uživatelů*: Přidávání a odebírání asistentů (zobrazuje se pouze správci aplikace).
    5. *Změna hesla*: Bezpečná změna hesla pro přihlášeného uživatele.

### 🛡️ Role a bezpečnost
- **Role "Správce aplikace" (Admin) vs "Asistent" (Evaluator)**:
  - Uživatele může spravovat výhradně správce aplikace.
  - Asistentům se v přehledu protokolů zobrazují pouze protokoly jim přiřazené nebo dosud nepřiřazené; administrátor má globální přehled nad všemi protokoly.
- **Zabezpečení přihlašovacího dialogu**:
  - Odstraněna nápověda s výchozími přihlašovacími údaji i předvyplněné heslo z formuláře.
  - Implementováno přímé hašování hesel přes `bcrypt`.

### 📚 Úlohy a termíny
- **Předdefinováno 12 oficiálních úloh pro zimní semestr (FPRA1 / ZS)**:
  - Přesně podle zadání: 01 - Vzduchová dráha, 02 - Dynamika rotačního pohybu, ..., 12 - Coulombův zákon.
  - Odstraněno duplicitní číslování (např. nevzhledné `U01: Úloha 1:`).
- **Oprava formátování termínů**:
  - Odstraněno zdvojené vypisování názvů a časů termínů (`Pondělí 8:00 - 10:00 (Pondělí 08:00 - 10:00 (F3))`).
  - Přidána možnost odstraňovat nepotřebné termíny s kontrolou návaznosti.
  - Opraveno rozložení karet ve správě termínů (odstraněno ořezávání podoken na menších monitorech).

### 🎨 Detaily a vizuální prvky
- Vytvořena vektorová SVG ikona (favicon) s fyzikálním motivem atomu a orbitalů.
- Zpřesněna responzivita pro rozlišení 1920x1080, 1366x768 a 1280x800.
- Přidány elegantní úzké posuvníky ladící s tématem.

---

## [2.0.0] - 2026-10-14

### Přidáno
- Přechod z jednoduchého statického HTML na plnohodnotnou webovou aplikaci na bázi **FastAPI + SQLite + PDF.js + PyMuPDF**.
- Hierarchická struktura složek na disku: `data/protocols/<semestr>/<termin>/<uloha>/<student>/[source|corrected]`.
- Systém bodování s přesností na násobky 0.125 b:
  - 4 kategorie: Výsledky (max 3), Diskuze (max 3), Formát (max 2), Chyby (max 2).
  - Výstup 1: Jednořádkový formát pro studijní systém.
  - Výstup 2: Detailní strukturovaný soubor `bodovani.txt`.
- Vypalování anotací a souhrnné hlavičky do PDF protokolu pomocí knihovny `PyMuPDF (fitz)`.
- Rozdělení do semestrů (`2026ZS`, `2026LS`).
- Týdenní termíny cvičení s místnostmi a časy.
- Příprava skriptů pro spuštění na Windows (`run.bat`), Linuxu (`run.sh`) a Dockeru (`Dockerfile`, `docker-compose.yml`).

---

## [1.0.0] - Původní stav

### Přidáno
- Původní jednoduchý skript `praktika.html` generující jednořádkový textový souhrn hodnocení.

