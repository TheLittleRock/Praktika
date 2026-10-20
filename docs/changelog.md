# Historie verzí (Changelog)

Všechny významné změny v projektu **Praktika Evaluation Studio** jsou zaznamenány v tomto souboru.

Formát vychází ze standardu [Keep a Changelog](https://keepachangelog.com/cs/1.0.0/) a projekt dodržuje [Sémantické verzování](https://semver.org/lang/cs/).

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
