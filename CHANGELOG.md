# Changelog

Všechny významné změny v projektu **Praktika Evaluation Studio** jsou zaznamenány v tomto souboru.

Formát vychází ze standardu [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/) a projekt dodržuje [Sémantické verzování](https://semver.org/lang/cs/).

## [2.20.1] - 2026-10-21

### 🚀 Opravy a vylepšení ve verzi 2.20.1

#### 🎓 Plná podpora ČVUT Moodle (formát Tiles, detekce skupin a synchronizace hodnocení)
- **Kompatibilita s Tiles (dlaždicovým) uspořádáním kurzu**: Seznam úloh se nově načítá z Moodle rozhraní `/mod/assign/index.php?id={course_id}`, které spolehlivě vrací všech 41 úloh včetně sekcí a témat (`01 - Vzduchová dráha...`, `02 - Dynamika...`), počtu odevzdaných prací a počtu čekajících na hodnocení.
- **Detekce studijních skupin a kroužků**: Skupiny (`Středa 8:00`, `Středa 12:00`, `Středa 16:00`, `Tuesday 10AM`, `Pátek 10:00`) jsou dynamicky extrahovány z `/user/index.php?id={course_id}` společně s přiřazením studentů.
- **Přehledné filtrování a seznam neohodnocených prací**: Dialog Moodle obsahuje nahoře filtry pro výběr konkrétní úlohy i skupiny a pod nimi přehlednou interaktivní tabulku odevzdaných neohodnocených prací.
- **Inteligentní automatické párování (Auto-match)**:
  - Automatické spárování úloh `P1`–`P12` na lokální úlohy v Praktiku (`measurements`).
  - Automatické spárování skupin na termíny (`slots`).
  - Možnost automatického vytvoření chybějícího termínu v aktivním semestru na jedno kliknutí.
- **Zápis známek A–F dle ČVUT stupnice a slovních komentářů**:
  - Implementováno odesílání hodnocení do Moodle přes interní službu `mod_assign_submit_grading_form`.
  - Automatický přepočet bodů na známku ECTS (A >= 90%, B >= 80%, C >= 70%, D >= 60%, E >= 50%, F < 50%) s možností ruční úpravy učitelem před odesláním.
  - Zápis slovního pedagogického komentáře a nahrání opraveného PDF.
- **Oprava formátování dialogu nápovědy cookie**: V `AppModal.alert` přidána podpora `isHtml: true`, takže se instrukce pro získání cookie MoodleSession zobrazují s funkčními odkazy a zvýrazněným textem místo surových HTML tagů.

## [2.20.0] - 2026-10-21

### 🚀 Novinky a vylepšení ve verzi 2.20.0

#### 👁️ Analytika zobrazení hodnocení studentem
- **Měření reálného času aktivního čtení**: Stránka se studentským hodnocením (`/v/{share_token}`) nyní pomocí Page Visibility API (`document.visibilityState === 'visible'`) a periodického heartbeat signálu přesně měří dobu, po kterou student hodnocení aktivně studoval. Opuštění stránky nebo přepnutí na jinou záložku čítač okamžitě pozastaví.
- **Bezpečný přenos a ochrana proti nafukování**: Přírůstky času jsou na backendu validovány a zastropovány (max. 30 s na signál) proti manipulaci. Dokončení relace je spolehlivě odesíláno i při zavření okna přes `navigator.sendBeacon`.
- **Přehledné indikátory v tabulce i ve Studiu**: V tabulce protokolů přibyl nový sloupec "Zobrazeno" s odznaky (např. `👁️ 3× • 4m 12s` nebo `👁️ Nezobrazeno`), filtr zobrazení a řazení dle času čtení. V záhlaví Studia je přítomen živý indikátor.
- **Detailní historie relací studenta**: Kliknutím na odznak se otevře modální okno s rozpadem jednotlivých návštěv, časových razítek, celkové doby a typu zařízení (Počítač, Mobil, Tablet).

#### 🎓 Integrace s ČVUT Moodle bez nutnosti administrátorského API
- **Podpora stahování a nahrávání na ČVUT Moodle**: Přímé propojení s Moodle (`moodle-vyuka.cvut.cz`, výchozí kurz `16880`) umožňující stahovat odevzdané protokoly a nahrávat opravené soubory zpět bez nutnosti REST API klíče.
- **Bezpečné přihlášení přes Microsoft Entra ID (SSO)**:
  - Interaktivní pomocný skript `scripts/moodle_login.py` využívající Playwright Chromium pro pohodlné jednorázové přihlášení učitele v okně prohlížeče (včetně 2FA/MFA) s automatickým uložením session cookie.
  - Možnost přímého zadání nebo aktualizace `MoodleSession` cookie v dialogu *Nastavení -> Moodle*.
  - Tlačítko pro okamžitý test spojení a validaci přihlášení.
- **Automatická detekce úloh a kruhů**: Aplikace automaticky načte seznam úloh (`mod/assign`) a studijních kruhů přímo z vybraného kurzu.
- **Hromadné stažení odevzdání**: Stažení ZIP archivu odevzdaných úloh z Moodle, inteligentní rozbalení a automatické vytvoření či aktualizace protokolů v databázi se zachováním vazeb na studenta.
- **Příprava a odeslání zpětné vazby do Moodle**: Funkce hromadného exportu a odeslání opravených PDF s hodnocením ve formátu akceptovaném Moodle funkcí *Nahrát více souborů se zpětnou vazbou v zipu* (`action=uploadfeedbackzip`).

## [2.19.1] - 2026-10-21

### 🚀 Opravy a vylepšení ve verzi 2.19.1

#### 🔗 Spolehlivé zobrazení tlačítka odkazu pro studenta
- **Doplnění `p.share_token` do SQL dotazu**: Opraven endpoint `/api/protocols`, kde v SQL dotazu chyběl sloupec `p.share_token`, kvůli čemuž se tlačítko `🔗` v tabulce nezobrazovalo.
- **Rychlé kopírování i alias `/student/{token}`**: Tlačítko `🔗` v tabulce protokolů je nyní viditelné u všech protokolů. Přidáno přesměrování z `/student/{token}` na kanonické `/v/{token}`.

#### 🪟 Striktní oddělování panelů Bodování a AI na protilehlé strany
- **Odstranění kolizí na jedné straně**: Bodování i AI asistent nyní mají výchozí dokování na protilehlých stranách (Bodování vpravo, AI vlevo).
- **Univerzální kontrola `ensureOppositePanels()`**: Zajišťuje automatické rozdělení stran při inicializaci, otevření Studia, spuštění analýzy i přepínání dokování jednotlivých panelů.

#### 📑 Plovoucí tlačítko miniatur v rohu PDF a zobrazení celé stránky
- **Přemístění tlačítka miniatur**: Tlačítko miniatur bylo odebráno z přeplněného levého panelu nástrojů a umístěno jako čisté plovoucí tlačítko do pravého horního rohu PDF pracovní plochy.
- **Přizpůsobení vyhledávací lišty**: Plovoucí vyhledávací lišta (`Ctrl+F`) se nyní automaticky odsazuje od pravého okraje (`right: 66px`), aby nekolidovala s tlačítkem miniatur.
- **Nedeformované miniatury s plným poměrem stran**: Miniatury nyní zobrazují celou stránku se zachováním přesného poměru stran (A4, na šířku apod.) a s 2x supersamplingem pro vysokou ostrost.

#### 🔍 Křišťálově ostré PDF písmo a subpixelové vyhlazení
- **Eliminace subpixelového rozostření**: Odstraněn nesoulad mezi CSS rozměry a rozměry plátna. Zaveden jednotný celočíselný poměr plátna `[nextCanvas.width / viewport.width, 0, 0, nextCanvas.height / viewport.height, 0, 0]`.
- **Retina supersampling**: Zvýšeno minimální měřítko DPR na 2.0x–3.0x a doplněna CSS direktiva `image-rendering: -webkit-optimize-contrast;` pro perfektní ostrost vektorového textu při všech úrovních přiblížení.

#### 🛡️ Odstranění duplicit schválených AI komentářů
- **Konec dvojitého vkládání**: `PDFStudio.approveAIProposal` již nevkládá dočasnou klientskou anotaci navíc před backendovým zpracováním, čímž byla odstraněna duplikace a ztmavnutí komentářů.
- **Geometrická kontrola duplicit v plátně**: Do `addAnnotation()` byla přidána pojistka kontrolující shodu strany, textu a pozice existujících anotací.

#### 🌐 Klikací odkazy v PDF funkční ve všech nástrojích
- **Konec omezení na nástroj výběru**: Odkazy na web i interní reference v PDF dokumentu nyní fungují ve všech nástrojích Studia bez nutnosti přepínat na nástroj Výběr.
- **Priorita vrstvy odkazů (`z-index: 15`)**: Odkazy přijímají kliknutí nad vrstvou anotací a zabraňují nechtěnému spuštění kreslení.

#### 📊 Detailní logování AI a srozumitelné chybové hlášky
- **Kategorie `ai` v systémových logách**: Veškeré požadavky, odpovědi a nezpracované chybové zprávy z Gemini API se zaznamenávají do `system_logs`.
- **Detailní chybová bublina v chatu**: V případě selhání AI (např. vyčerpání kvóty, neplatný klíč) chatovací bublina zobrazí přesnou příčinu chyby s odkazem na systémové logy.

#### 🤖 Podpora modelů Gemini 3.6 Flash & Free Tier
- **Výchozí model Gemini 3.6 Flash**: Výchozím modelem pro analýzu i chat je nyní `gemini-3.6-flash`, dostupný v bezplatném tarifu Google AI Studio.
- **Kompletní výběr modelů v Nastavení**: Přidány modely `gemini-3.6-flash`, `gemini-3.8-flash`, `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3-flash`, `gemini-2.5-flash` a `gemini-2.5-flash-lite`.
- **Aktualizace dokumentace a README**: Odstraněny zastaralé zmínky o Gemini 2.5 a sjednocena dokumentace.

## [2.19.0] - 2026-10-21

### 🚀 Novinky a vylepšení ve verzi 2.19.0

#### 📂 Drag & Drop import protokolů na domovské obrazovce
- **Celostránková plocha pro přetažení souborů**: Přetažením PDF souborů myší na domovskou obrazovku se okamžitě zobrazí animovaný overlay s rozostřeným pozadím (`backdrop-filter: blur(10px)`).
- **Hromadné vhození a automatická detekce**: Po puštění souborů se otevře importní okno, soubory se automaticky předvyplní a spustí se autodetekce údajů bez nutnosti klikat na tlačítko výběru.

#### 🔤 TeX / LaTeX normalizace diakritiky a asynchronní sync
- **Podpora pro LaTeXem generovaná PDF**: Vyřešeno selhání detekce jména (např. v protokolu úlohy 6), kde TeX ukládá diakritiku jako samostatné akcenty (`jm´eno: Jakub Petrˇz´ılek`). Funkce `normalize_latex_pdf_text` nyní skládá všechny TeX akcenty (`´`, `ˇ`, `˚`, `¨`, dotless `ı`) do standardního NFC kódování Unicode.
- **Asynchronní sync při rychlém odeslání**: Pokud uživatel ihned po výběru souboru stiskne `Enter`, aplikace počká na běžící promise autodetekce na pozadí a automaticky doplní detekované jméno i úlohu bez nutnosti ručního vypisování.

#### 🏷️ Standardizované pojmenování exportovaných PDF
- **Jednotný název souboru**: Formát `{Předmět}_Uloha_{číslo}_{Příjmení}_{Jméno}_opraveno.pdf` (např. `FPRA1_Uloha_06_Petrzilek_Jakub_opraveno.pdf`).
- **Implementováno ve všech exportech**: Jednotné názvy se používají při přímém stažení opraveného PDF, při vypálení hodnocení i při hromadném ZIP exportu protokolů.

#### ⌨️ Univerzální klávesové zkratky dialogů a Studia
- **Potvrzení klávesou `Enter`**: Ve všech kontextových a modálních oknech (import protokolu, úprava metadat, hromadné úpravy, přepnutí uživatele, přihlášení, informační okna) potvrdí klávesa `Enter` formulář.
- **Zrušení klávesou `Escape`**: Klávesa `Escape` spolehlivě zavře jakékoli otevřené kontextové okno, vyhledávací lištu nebo zruší rozpracovaný koncept komentáře v PDF.
- **Zkratky v plovoucí kartě komentáře**: `Enter` (bez Shiftu) odešle a uloží poznámku s případnou bodovou srážkou, `Escape` kartu zavře a zahodí dočasné zvýraznění.
- **Klávesy `Delete` / `Backspace`**: Okamžité smazání aktivně vybrané anotace na plátně PDF.

#### 🪟 Inteligentní oddělování postranních panelů Studia
- **Automatické rozdělení stran (Left vs. Right)**: Otevření obou panelů (AI asistent i Bodování) je automaticky rozmístí na protější strany (jeden vlevo, druhý vpravo), čímž zůstává PDF vycentrováno uprostřed a panely se nepřekrývají ani nedělí nevzhledně o jednu stranu.
- **Volitelné nastavení v Vzhledu**: Přidána volba v Nastavení -> Vzhled: *„Povolit dokování obou postranních panelů na stejné straně“* pro uživatele, kteří preferují mít oba panely na jedné straně.

#### 📑 Vysouvací lišta miniatur stránek (Thumbnails Drawer)
- **Rychlá navigace po stránkách protokolu**: Nové tlačítko v nástrojové liště i klávesová zkratka `M` otevře levý panel s náhledy jednotlivých stránek PDF a okamžitým skokem na vybranou stránku.

#### 🔗 Rychlé kopírování odkazu pro studenta
- **Tlačítko v tabulce protokolů**: Kliknutím na ikonku `🔗` v řádku protokolu se studentský odkaz na opravený protokol s tokenem okamžitě zkopíruje do schránky s notifikací toastu.

#### 🔠 Vyhledávání nezávislé na diakritice (Unaccent)
- **SQLite funkce `unaccent()`**: Hledání v protokolech i filtrování jmen studentů na hlavní stránce nyní funguje bez ohledu na háčky a čárky (např. zadání „petrzilek“ bez problémů najde studenta „Jakub Petržílek“).

#### 🎨 Vizuální opravy loga a semestru v postranním panelu
- **Zamezení lámání loga Praktika**: Zajištěn jednořádkový nerozdělený text „Praktika Studio“.
- **Kompaktní kód semestru**: Výběrové pole aktivního semestru v postranním panelu zobrazuje pouze čistý kód semestru (např. `2026ZS`), takže se text pohodlně vejde do rámečku bez ořezání.

## [2.18.2] - 2026-10-21

### 🚀 Opravy a vylepšení ve verzi 2.18.2

#### 📐 Zapouzdření ovladačů PDF a ochrana postranních panelů
- **Kontejner `.studio-pdf-workspace`**: Plocha PDF byla zapouzdřena do samostatného flexibilního kontejneru. Vyhledávací lišta (`Ctrl+F`), plovoucí tlačítko na celou obrazovku v pravém dolním rohu i indikátor ukládání jsou ukotveny výhradně uvnitř tohoto kontejneru.
- **Konec překrývání panelů AI a Bodování**: Při otevření, přikotvení nebo změně velikosti doku hodnocení či panelu AI se kontejner PDF automaticky přizpůsobí zbývajícímu prostoru. Ovladače zůstávají v rozích viditelné plochy PDF a nikdy nezasahují do postranních panelů.

#### 🎨 100% solidní a neprůhledné okno Nastavení
- **Oprava průhlednosti**: Odstraněna nedefinovaná proměnná a nastaveno plně neprůhledné pozadí `var(--card-bg)` s odpovídajícím stínováním a ohraničením. Text PDF protokolu na pozadí již neprosvítá skrze dialogové okno.

#### 🛡️ Automatické zaznamenávání chyb v kódu (Backend & Frontend)
- **Globální výjimkový handler v Pythonu (`@app.exception_handler`)**: Každá neošetřená serverová výjimka a HTTP 500 chyba se automaticky zapíše do databáze `system_logs` jako `ERROR` v kategorii `system` včetně typu výjimky, zprávy, tracebacku, uživatelského jména a IP adresy.
- **Sběr klientských chyb v JavaScriptu (`/api/system/client-log`)**: Běhové chyby JS v prohlížeči (`window.onerror`, unhandled promise rejections) se automaticky přeposílají na server a ukládají do systémových logů v kategorii `frontend`.
- **Kategorie `frontend` v prohlížeči logů**: Přidán filtr v okně Nastavení pro snadné zobrazení a analýzu chyb z klientského rozhraní.

## [2.18.1] - 2026-10-20

### 🚀 Opravy a vylepšení ve verzi 2.18.1

#### ⚙️ Dvousloupcové nastavení a zamezení cachování
- **Zamezení agresivnímu cachování v prohlížeči**: `serve_spa()` nyní vrací `Cache-Control: no-cache, no-store, must-revalidate` hlavičky a všechny skripty i styly používají verzovací řetězec `?v={{ version }}`. Tím je zaručeno okamžité načtení nejnovějšího 2-sloupcového layoutu i systémových auditních logů.
- **Jasná struktura 11 kategorií**: Levý postranní panel s přehlednou vertikální navigací pro osobní, hodnotící i administrátorské kategorie.
- **Řízení viditelnosti pro administrátora**: Administrátorské položky (Systémové logy, Uživatelé, Databáze, Diagnostika) jsou dostupné pouze přihlášenému správci.

#### 🖥️ Plovoucí tlačítko Fullscreen v pravém dolním rohu
- **Odstranění z levého panelu**: Tlačítko pro celou obrazovku bylo kompletně odstraněno z levé svislé nástrojové lišty Studia, aby nezabíralo místo hodnotícím funkcím.
- **Plovoucí ovladač v rohu PDF plochy**: Umístěno jako diskrétní plovoucí tlačítko v pravém dolním rohu s obousměrnou synchronizací s klávesou `F11`.

#### 🔍 Globální zachytávání Ctrl+F
- **Capture-phase klávesový posluchač**: Stisk `Ctrl+F` (či `Cmd+F`) je ve Studiu zachycen v capture fázi dříve, než jej stihne zachytit prohlížeč. Otevírá plovoucí vyhledávač v PDF s automatickým výběrem textu a počítadlem výskytů.

#### 📊 Výchozí zobrazení vlastních protokolů pro administrátora a řazení
- **Výchozí filtr „Moje protokoly“**: Správce po přihlášení vidí výhradně své vlastní protokoly (`evaluator_id = me`). Všichni hodnotitelé jsou dostupní přes volbu `Všichni hodnotitelé`.
- **Chronologické řazení termínů a česká abeceda**: Řazení termínů dnů v týdnu od pondělí do pátku s časem, české abecední řazení u jmen a číselné u skóre.

#### 📋 Oprava mazání předvoleb a úprav srážek
- **Mazání častých chyb**: Opraveno oprávnění a mazání předvoleb v Nastavení s potvrzovacím dialogem, ošetřením chyb a právy pro správce i asistenty.
- **Okamžitý přepočet srážek**: Úprava bodové hodnoty i textu v hodnotícím doku okamžitě přepočítá body a promítne se do konceptu.

#### 📝 Přesné označování textu v PDF
- **Odstranění kolizního řazení v TextLayer**: Ponecháno přirozené čtení textu PDF.js bez umělého přehazování elementů, což eliminuje přeskakování na následující řádky při označování nadpisů a tabulek.
- **Zpřesnění CSS řádků**: Nastaveno `line-height: normal;` a přesné ohraničení spanů.

#### 🤖 AI Chat – historie per-protokol a multi-turn paměť
- **Trvalá historie konverzace**: Zprávy jsou uloženy v SQLite sloupci `protocols.ai_chat_json` a automaticky se načítají při otevření protokolu.
- **Konverzační kontext pro Gemini**: Model má k dispozici celou historii dosavadní diskuze a dokáže přirozeně navazovat na doplňující otázky vyučujícího s plnou podporou KaTeX matematiky.

## [2.18.0] - 2026-10-20

### 🚀 Novinky a vylepšení ve verzi 2.18.0

#### 📜 Systémové auditní logy a správa
- **Auditní záznamy událostí**: Záznam všech důležitých operací v systému (přihlášení/odhlášení, nahrání, editace a smazání protokolů, uložení hodnocení, stažení/obnova/optimalizace databáze, AI analýzy a chat).
- **Prohlížeč logů v Nastavení**: Přehledná tabulka s barevnými odznaky úrovní (INFO, WARNING, ERROR) a kategorií, fulltextovým vyhledáváním a stránkováním.
- **Export do CSV a JSON**: Export záznamů do CSV s UTF-8 BOM pro bezchybné zobrazení české diakritiky v MS Excel, a do strukturovaného JSON.
- **Promazávání logů**: Bezpečné promazávání auditních logů starších než 7, 30 nebo 90 dní (nebo kompletní výmaz) s automatickým auditním záznamem o promazání.

#### ⚙️ Kompletní redesign okna Nastavení
- **Dvousloupcový layout**: Přehledný levý panel se všemi 11 kategoriemi bez rušivých vnořených hlaviček: Můj profil, Vzhled & Ovládání, Změna hesla, Laboratorní úlohy, Časté chyby & Předvolby, AI Asistent, Uživatelé, Databáze & Zálohy, Systémové logy, Diagnostika & Stav, O aplikaci.
- **Plná viditelnost pro administrátora**: Všechny administrátorské sekce (Uživatelé, Databáze, Logy, Diagnostika) jsou okamžitě přístupné pro přihlášeného správce.
- **Funkční Changelog**: Spolehlivé načítání historie verzí v záložce *O aplikaci*.

#### 🔍 Vyhledávání v PDF (Ctrl+F)
- **Kompaktní plovoucí lišta bez zbytečných tlačítek**: Vyvolání klávesovou zkratkou `Ctrl+F` (nebo `Cmd+F`), která zabrání otevření nativního dialogu prohlížeče a otevře vyhledávač přímo v plátně Studia. Žádné zbytečné tlačítko v levé svislé nástrojové liště.
- **Diakriticky necitlivé hledání v češtině**: Spolehlivě najde výrazy i bez ohledu na háčky a čárky (např. *mereni* najde *měření*).
- **Interaktivní navigace a zvýraznění**: Počítadlo shod (`1/N`), navigace `Enter` / `Shift+Enter` (nebo šipkami) a zavření klávesou `Escape`.

#### 📊 Řazení sloupců a výchozí filtr pro správce
- **Seřazení protokolů na hlavní stránce**: Možnost řazení podle studenta, úlohy, termínu, stavu, hodnocení a vyučujícího s respektováním české abecedy (`localeCompare('cs')`).
- **Ergonomické zarovnání indikátorů**: Jemné indikátory řazení (`▲`, `▼`, `⇅`) vycentrované vedle textu záhlaví bez vertikálního rozbití řádku.
- **Výchozí filtr „Moje protokoly“ pro administrátora**: Po přihlášení správce se výchozí filtr hodnotitele automaticky nastaví na jeho vlastní protokoly (`evaluator_id = 'me'`).

#### 🖥️ Režim na celou obrazovku (Fullscreen)
- **Nativní Fullscreen API**: Jednoklikové tlačítko `⛶ Celá obrazovka` v záhlaví Studia s automatickou detekcí a přepínáním ikon, plně kompatibilní s klávesou `F11`.

#### 🔬 Opravy AI chatu, ostrosti PDF a exportu příloh
- **Ošetření LaTeX zpětných lomítek v AI (`Invalid \escape`)**: Zaveden `robust_json_loads` s automatickým ošetřením a escapováním zpětných lomítek u fyzikálních a matematických symbolů (`\sigma`, `\Delta`, `\frac`).
- **Odolnost proti výpadkům 503 u Gemini**: Automatický retry a fallback napříč kandidátními modely při dočasném přetížení Google Gemini API.
- **Přísně věcná kritika**: Eliminace prázdných pochval v sekčních komentářích a soustředění na věcné a fyzikální nedostatky.
- **Nulový překryv textů v příloze PDF**: Sanitizace kontextových snippetů na jeden řádek a izolované obdélníky pro komentáře, čímž je zamezeno vzájemnému překrytí textů.
- **Tmavé posuvníky pro studentský náhled**: Přidány dark mode styly pro posuvníky ve studentském náhledu.
- **Konec skákání při zoomu**: Zafixováno kotvení pohledu na střed a přepočet souřadnic bez trhání plátna nahoru a dolů.
- **Výběr řádků v tabulkách**: Seřazení textových elementů do vizuálního čtecího pořadí před vykreslením textové vrstvy umožňuje označit jednotlivé řádky tabulky bez nechtěných přeskoků.
- **Oprava aktualizace srážek bodů**: Opraveno předávání identifikátorů polí v `AppModal.showForm`, úpravy textu i bodů se ihned projeví a přepočítají.

## [2.17.0] - 2026-10-19

### 🚀 Novinky a vylepšení ve verzi 2.17.0

#### 🎯 Zrušení nového zvýraznění a spolehlivá klávesa Escape
- **Okamžité odstranění zvýraznění při zrušení**: Při stisku klávesy `Escape` nebo kliknutí na tlačítko *Zrušit* při zadávání komentáře k nově vytvořenému zvýraznění se zvýraznění kompletně a bezestopy odstraní z plátna, ze seznamu anotací i z historie akcí (`Undo`).
- **Klávesa Escape pro zavření okénka**: Stisk klávesy `Escape` spolehlivě zavírá okénko komentáře jak z textového pole, tak z jakéhokoliv místa na obrazovce. Při editaci již existující dřívější poznámky obnoví stisk `Escape` původní text i barvu bez smazání anotace.
- **Zvýraznění bez komentáře na stisk Enter**: Čisté zvýraznění bez textového komentáře se potvrdí stiskem `Enter` (nebo kliknutím na *Uložit komentář*) s prázdným polem.

#### 📍 Inteligentní pozicování okénka komentáře (Acrobat Comment Card)
- **Automatické překlopení nad označený text**: Plovoucí karta komentáře měří svou reálnou výšku (~360 px) a detekuje přiblížení ke spodnímu okraji okna. Pokud se karta pod označený řádek nevejde, automaticky se otevře **NAD** označeným textem.
- **100% viditelnost a bezpečný clamping**: Souřadnice karty jsou striktně ořezány v mezích okna prohlížeče (`window.innerWidth`, `window.innerHeight`) s bezpečným odstupem 16 px. Karta ani její spodní ovládací tlačítka už nikdy nezmizí pod dolním okrajem obrazovky.
- **Responzivní posun**: V případě velmi malých obrazovek je karta omezena na `max-height: calc(100vh - 32px)` s vnitřním posuvníkem.

#### ⚡ Responzivní a přesné označování textu (PDF.js TextLayer)
- **Kalibrace měřítka textové vrstvy**: Každé stránce je při renderování předána dynamická CSS proměnná `--scale-factor: viewport.scale`. Tím je odstraněn rozpad geometrie písem a nesoulad souřadnic v PDF.js 3.11.174 při jakékoliv úrovni zoomu.
- **Okamžitá odezva výběru bez zpoždění**: Odstraněna redukce průhlednosti (`opacity: 0.25`) textové vrstvy. Nativní výběr myší je jasný, sytě modrý a okamžitě viditelný během tažení myší.
- **Konec nechtěných přeskoků na další řádky**: Algoritmus označování textu inteligentně seskupuje segmenty na stejném řádku do čistých linií a filtruje nechtěné koncové caret artefakty při označování nadpisů.
- **Globální zachycení myši**: Výběr textu spolehlivě funguje i v případě, že uživatel uvolní tlačítko myši těsně za okrajem stránky či v mezeře mezi stranami.

## [2.16.0] - 2026-10-17

### 🚀 Novinky a vylepšení ve verzi 2.16.0

#### 📑 Multimodální analýza a AI Chat s celým PDF dokumentem (Google Gemini 3.5 Flash)
- **Přímé zasílání celého vysázeného PDF**: Všechny požadavky na AI analýzu (`analyze_protocol`) i konverzaci (`chat_with_ai`) nyní posílají celkový PDF dokument nativně v `inline_data` (`application/pdf`, base64).
- **Vizuální inspekce grafů a tabulek**: Model Gemini má k dispozici originální vizuální podobu protokolu a může přímo kontrolovat:
  - přítomnost a správnost popisků os a jednotek v hranatých závorkách (např. $T\ [\text{s}]$),
  - vynesení chybových úseček (**errorbarů**),
  - proložení teoretickou křivkou fitu namísto nevhodných lomených spojnic bodů,
  - parametry fitu s nejistotami a koeficientem determinace $R^2$,
  - formátování a popisky tabulek.
- **Robustní automatický fallback**: V případě jakéhokoliv problému se síťovým přenosem binárních dat proběhne okamžitý transparentní fallback na textový režim.

#### 🧮 Podpora Markdown a matematiky LaTeX (KaTeX) v AI Chatu
- **Lokální offline KaTeX & Marked**: Zprávy asistenta i AI v chatu jsou renderovány pomocí lokálně uložených knihoven `marked.min.js` a `KaTeX` (včetně fontů v `app/static/vendor/` pro 100% offline provoz).
- **Matematické výrazy a symboly**: Plná podpora inline matematiky (`$...$`, `\(...\)`) i display bloků (`$$...$$`, `\[...\]`).
- **Ochrana vzorců před poškozením**: Matematické výrazy jsou před parsováním Markdownu tokenizovány a chráněny, takže podtržítka dolních indexů ani hvězdičky násobení nejsou poškozeny jako kurzíva či tučné písmo.

#### 📐 Ergonomické textové pole a interaktivní průvodce chatem
- **Automaticky zvětšované textové pole**: Vstupní textarea se plynule přizpůsobuje délce psaného promptu (`min-height: 56px`, `max-height: 220px`) a umožňuje také manuální svislé roztažení.
- **Tlačítko [ℹ️ Návod k chatu]**: V záhlaví chatu přibylo tlačítko otevírající interaktivní nápovědu. Vysvětluje obě možnosti využití chatu (teoretické dotazy bez zásahu do PDF vs. korekční úkoly s automatickým generováním anotací do textu) a nabízí klikací ukázkové prompty k okamžitému vyzkoušení.

#### 🔀 Nezávislé ukotvení panelů (AI asistent a Bodování vlevo / vpravo)
- **Nezávislé přepínání strany**: Panel AI asistenta i Bodovací dok disponují vlastním tlačítkem `[⇄]` pro přepínání strany ukotvení (vlevo vs. vpravo) s perzistencí v `localStorage`.
- **Současné otevření obou panelů**: Pokud je jeden panel ukotven vlevo a druhý vpravo, **mohou být oba panely otevřené současně**. Vzniká tak komfortní třísloupcové uspořádání (AI Asistent vlevo, PDF plátno uprostřed a Bodování vpravo).
- **Inteligentní přemístění při kolizi**: Při otevření druhého panelu na stejné straně se protilehlý panel automaticky přemístí na opačnou stranu.
- **Překrytí stavu uložení**: Levý dok má nastaven vyšší `z-index`, takže čistě a nerušeně překrývá plovoucí odznáček stavu uložení `#autosave-indicator`.

#### ⚡ Atomický Undo / Redo pro zvýraznění s komentářem
- **Sloučení do 1 události historie**: Vytvoření zvýraznění textu a následné vepsání komentáře do otevírací karty se v historii změn (`historyStack`) nyní eviduje jako jediná atomická událost.
- **Jedno kliknutí na Zpět**: Stisknutí `Ctrl+Z` (nebo kliknutí na tlačítko Zpět) odstraní zvýraznění i jeho komentář najednou bez nutnosti dvojitého klikání.

---

## [2.15.0] - 2026-10-17

### 🚀 Novinky a vylepšení ve verzi 2.15.0

#### 💬 Interaktivní AI Chat s automatickými návrhy do PDF
- **Dvouzáložkový panel AI asistenta**: V panelu asistenta přibyly záložky `[📋 Návrhy chyb]` pro strukturovaný přehled detekcí a `[💬 AI Chat]` pro přirozenou konverzaci.
- **Duální konverzační režim**:
  - *Fyzikální dotazy*: Odpovědi na teoretické dotazy, ověřování vztahů a jednotek bez zásahu do PDF.
  - *Zadávání korekčních úkolů*: Možnost zadat asistentovi konkrétní pokyn (např. *„Zkontroluj vzorce a jednotky v diskuzi“*). AI chyby nejen vysvětlí v chatu, ale rovnou je **automaticky vygeneruje jako návrhy označení do textu protokolu**, které asistent může okamžitě schválit nebo zamítnout.
- **Rychlé promptové čipy**: Tlačítka pro rychlé spuštění typických úkolů (kontrola vzorců a jednotek, zhodnocení diskuze, dotaz na teorii).
- **Perzistentní historie konverzace**: Historie zpráv je ukládána v databázi pro každý protokol zvlášť s možností promazání tlačítkem *Smazat chat*.

#### 🎯 Zpřesnění AI asistenta a eliminace falešných chyb
- **Konec halucinací o dolních indexech a mezerách ve vzorcích**: Upraven systémový prompt Gemini pro potlačení falešných detekcí způsobených artefakty při extrakci textu z PDF (rozpad dolních indexů $m_2 c_2$, chybějící mezery u rovnic jako `K^{-1}.Tento`).
- **Zaměření na fyzikální podstatu**: AI se striktně orientuje na věcnou správnost, fyzikální interpretaci, metodiku, výpočty a logickou návaznost diskuze.

#### 🔗 Plně funkční klikací odkazy v PDF prohlížeči
- **Interaktivní hypertextové odkazy**: Webové URL adresy (externí zdroje, datasheety) i vnitřní křížové odkazy (rovnice, citace literatury, kapitoly) jsou nyní v plátně Studia plně klikací přes transparentní vrstvu `.pdf-links-layer`.
- **Hladká navigace**: Interní odkazy plynule odscrollují na příslušnou cílovou stránku protokolu.

#### 🛠️ Ergonomie anotací a editoru komentářů
- **Klávesové zkratky v komentářích**: Klávesa `Enter` v textovém poli komentáře okamžitě uloží a zavře komentářovou kartu; `Shift + Enter` vytvoří nový řádek.
- **Ochrana zvýraznění před posunem**: Zvýraznění textu nelze nechtěně posouvat nástrojem Výběr (zůstávají pevně ukotvena k textu), avšak kliknutí na ně nástrojem Výběr okamžitě otevře komentář k editaci.
- **Bezpečné poznámky**: Nově vytvořené poznámky mají volbu srážky bodů ve výchozím stavu vypnutou (`checked = false`).
- **Otevření existující poznámky**: Kliknutí na existující poznámku `[⊖]` v nástroji Poznámka (i Výběr) otevře existující poznámku pro úpravu a přesun, místo vytvoření nežádoucí duplikace.
- **Rychlý převod výběru textu**: Výběr textu myší v nástroji Ruka / Výběr lze jedním kliknutím na Zvýrazňovač či Přeškrtnutí okamžitě převést na anotaci.
- **Plnohodnotný obousměrný Undo / Redo**: Historie změn (`Ctrl+Z`, `Ctrl+Y`, `Ctrl+Shift+Z`) eviduje nejen přidání a smazání, ale i posun libovolného prvku po plátně a editaci textu komentáře. V liště přibylo tlačítko `Vpřed`.
- **Spolehlivé skrývání hover tooltipů**: Plovoucí bubliny komentářů a návrhů okamžitě mizí při opuštění prvku kurzorem, při scrollování, smazání či schválení návrhu.

---

## [2.14.0] - 2026-10-16

### 🚀 Novinky a vylepšení ve verzi 2.14.0

#### 📱 Responzivní mobilní rozhraní studentského náhledu (`student_view.html`)
- **Segmentovaný přepínač záložek pro mobily a tablety (`<= 900px`)**: Na displejích telefonů a tabletů se pod hlavičkou zobrazuje přepínač mezi záložkou `[📄 Protokol (PDF)]` a `[📊 Hodnocení & Poznámky]`.
- **Automatická navigace na stranu**: Kliknutí na libovolnou poznámku v záložce Hodnocení automaticky přepne na záložku Protokol, odscrolluje přímo na danou stranu a zvýrazní ji pulzním rámečkem.
- **Kompaktní mobilní záhlaví**: Tlačítka v záhlaví (Tmavý režim, Exportované PDF, Stáhnout PDF) na malých displejích automaticky skryjí dlouhé textové popisky a zobrazují pouze zřetelné ikony, čímž eliminují nežádoucí lámání řádků.
- **Plné zachování PC verze**: Pro obrazovky `> 900px` zůstává identické ergonomické dvoupanelové uspořádání.

#### 🔍 Studio-style zoom mechanika ve studentském náhledu
- **Izolace zoomu pro PDF**: Gesta touchpad pinch a `Ctrl + Scroll` kolečkem myši zoomují výhradně PDF canvas a zabraňují nechtěnému zvětšování celého okna prohlížeče (`e.preventDefault()`).
- **Okamžitá odezva s kotvením na kurzor**: Okamžitá transformace CSS `scale(ratio)` s následným debouncovaným ostrým vykreslením po 180 ms udržuje obsah pod kurzorem myši zcela stabilní.

#### 📚 Sloučení Úvodu a Rychlého startu & Úprava klíčových schopností
- **Sjednocení `docs/index.md`**: Původní samostatný rychlý start byl přímo integrován do hlavní stránky, včetně správných výchozích údajů (`admin` / `admin123`) a přehledného rozcestníku.
- **Klíčové schopnosti**: Záložka přejmenována na „PDF Studio“, text zaměřen čistě na dostupné anotační nástroje a Acrobat kompatibilitu. Přidána nová záložka popisující studentský webový náhled.

#### 🎬 Oprava zobrazování animací a ucelené přetočení workflow
- **Náprava cesty v MkDocs**: Raw HTML tagy `<picture>` byly nahrazeny standardní Markdown syntaxí `![Ukázka](../assets/images/clip_....webp)`, což vyřešilo problém s relativními cestami ve vnořených adresářích `/guide/assistant/` a `/guide/admin/`.
- **Kompletní a realistické demonstrace**: Všechny animace v 18 FPS zachycují ucelené kroky hodnocení na protokolu Štěpána Skalky (otevření dialogu importu s autodetekcí, hromadné schválení, napsání a uložení poznámky k rovnici (3), animace srážky a celkového hodnocení, rozsvícení zeleného stavu uložení).

---

## [2.13.0] - 2026-10-16

### 🚀 Novinky a vylepšení ve verzi 2.13.0

#### 🎨 Přepracování studentského náhledu na živé vykreslovací jádro Studia (`/v/{share_token}`)
- **Vykreslování identické se Studiem**: Studentský prohlížeč již nenačítá pre-renderované PDF s vypálenými křivkami, ale čisté zdrojové PDF, nad nímž se dynamicky tvoří SVG/HTML vrstva anotací.
- **Interaktivní bubliny (Hover Tooltips)**: Najetím myši na zvýrazněný text, ikonku komentáře `[⊖]`, šipku, přeškrtnutí či špendlík se zobrazí plovoucí bublina se jménem asistenta a komentářem.
- **Přepínání motivu vzhledu**: V záhlaví přibylo tlačítko pro přepnutí motivu zobrazení (`☀️` / `🌙`) s perzistencí v `localStorage`.
- **Přepínač režimů a spolehlivý Fallback**: Možnost přepnout mezi `🎨 Interaktivní náhled` a `📄 Exportované PDF`. Při absenci zdrojového souboru systém automaticky přejde na zobrazení exportovaného PDF.

#### 🎥 Plynulé 18 FPS animace se zvětšenou virtuální myší
- **Zvýšení snímkové frekvence na 18 FPS**: Všechny nahrávky byly znovu natočeny s vysokou plynulostí v optimalizovaném formátu WebP i palette-dithered GIF.
- **Viditelný zvětšený kurzor myši**: Do headless prohlížeče je injektován kontrastní zvětšený kurzor (32 px) se světelným pulzem (click ripple) při stisku tlačítka.
- **Realistické fyzikální hodnocení bez náhodných čmáranic**: Všechny ukázky demonstrují skutečné pedagogické korekce protokolu Štěpána Skalky (*Kalorimetrie* – chybějící čárka ve vzorci (3), diskuze tepelných ztrát, orientační šipky na tabulku).
- **3 nové animované ukázky v dokumentaci**:
  - *Studentský náhled* (`clip_student_view`)
  - *Hromadné operace v přehledu* (`clip_batch_ops`)
  - *Administrátorské nastavení a správa systému* (`clip_admin_settings`)

#### 📚 Komplexní audit a revize dokumentace
- Příručky pro asistenty i správce byly zrevidovány, doplněny o nové kapitoly a prověřeny pomocí `mkdocs build --strict`.

---

## [2.12.0] - 2026-10-16

### 🚀 Novinky a vylepšení ve verzi 2.12.0

#### 📱 Interaktivní studentský náhled s PDF.js prohlížečem (`/v/{share_token}`)
- **Plnohodnotný PDF.js engine**: Místo statického `<iframe>` student nyní vidí identický ostrý canvas viewer jako asistent ve Studiu, a to včetně offline podpory v plném rozlišení obrazovky (HiDPI / Retina).
- **Dvoupanelové rozvržení**:
  - *Vlevo*: Interaktivní PDF plátno s ovládáním zoomu (+, −, přizpůsobení na šířku okna) a indikátorem stran.
  - *Vpravo*: Přehled hodnocení s velkou známkou, body, dílčími kategoriemi, celkovým slovním hodnocením asistenta a interaktivním seznamem všech poznámek.
- **Klikací proskakování na poznámky**: Kliknutí na libovolnou poznámku v pravém sloupci okamžitě a plynule posune PDF prohlížeč na příslušnou stranu a na moment ji zvýrazní.
- **Plná mobilní responzivita**: Na telefonech a tabletech se panely automaticky poskládají pod sebe s optimalizovaným vertikálním posunem.

#### 💬 Celkové slovní hodnocení protokolu pro Moodle i studenta
- **Vyhrazené pole v bodovacím doku**: Přidáno pole *Celkové slovní hodnocení (pro Moodle i studenta)*, kam může cvičící uvést souhrnný dojem a zhodnocení celého protokolu.
- **Automatická propagace do všech výstupů**: Text se automaticky propisuje do Moodle textového výstupu (`generateOutput2`), do Acrobat samolepicí poznámky na 1. straně PDF, do souhrnné přílohy (Appendix) i do studentského náhledu.

#### 🎯 Oprava hover tooltipů nad ostrými pravoúhlými zvýrazněními v PDF
- **Interaktivní komentáře při najetí myší**: K vektorovým pravoúhlým zvýrazněním byla doplněna neviditelná obdélníková anotace (`/Square`, `border=0`, transparentní barva). Prohlížeče Adobe Acrobat, Chrome i Brave tak spolehlivě zobrazují plovoucí bublinu s komentářem a jménem autora při najetí kurzoru myši, aniž by docházelo k deformaci či zaoblení hran zvýraznění.

#### 🎥 Přegenerování reálných animací a snímků s protokoly Štěpána Skalky
- **Výhradní použití autorových testovacích protokolů**: Všechny screenshoty a animované ukázky v dokumentaci i README byly nově pořízeny pomocí Playwright a ffmpeg přímo nad protokoly Štěpána Skalky (`Protokoly testovaci/Kalorimetrie.pdf`).
- **Nové specializované animované klipy**: Pro jednotlivé fáze hodnocení byly vytvořeny plynulé odlehčené WebP/GIF klipy (import s autodetekcí, práce s AI asistentem, kreslení anotací, bodování a export).
- **Zlidštění příručky pro asistenty**: Doplněny praktické rady pro cvičící a zvýrazněno pravidlo uložení konceptu (`Ctrl+S` / `Dokončit`) před stažením PDF.

---

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
