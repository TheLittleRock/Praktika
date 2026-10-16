# Historie verzí (Changelog)

Všechny významné změny v projektu Praktika jsou dokumentovány v tomto souboru.

---

## [v2.9.0] – 2026-10-16

### 🎨 Korekční PDF Studio & Vizuály
- **Plovoucí indikátor ukládání**: Převeden na minimalistickou průhlednou indikaci v levém dolním rohu bez pozadí, která se zobrazuje přes PDF a nezmenšuje ani neposouvá viewport.
- **Nezávislost barev nástrojů**: Změna barvy v nástrojové liště již retroaktivně nepřebarvuje dříve nakreslené tvary a perokresby.
- **Barevná paleta v editoru komentáře**: Přidána volba šesti barevných teček přímo do karty komentáře pro okamžitou změnu barvy konkrétního zvýraznění.
- **Sladění výplně obdélníků**: Výplň rámečku na plátně se nyní dynamicky generuje jako polo-průhledná barva odpovídající barvě obrysu.

### 🤖 AI Asistent (Gemini)
- **Oprava schvalování na plátně**: Opraven chybějící export `window.App`, který způsoboval nečinnost tlačítek *✓ Aplikovat* u návrhů přímo v textu.
- **Synchronizace seznamů v reálném čase**: Po schválení nebo zamítnutí návrhu položka okamžitě zmizí jak z plátna, tak z postranního panelu asistenta.
- **Červená výchozí barva**: AI návrhy a zvýraznění mají výchozí červenou barvu `#ef4444` s možností následné uživatelské úpravy.
- **Fokus na chyby**: Kalibrace promptu pro potlačení prázdných konstatování a maximální záchyt reálných nedostatků (interpunkce rovnic, nejistoty typu B, diskuze).

### 🖨 Exportované PDF & Moodle
- **Předání srážek do exportu**: Opraveno předávání detailních srážek do modulu `burn_annotations_to_pdf`.
- **Acrobat-style poznámková bublina**: Vektorový piktogram komentáře s bílými linkami textu plně kompatibilní s Adobe Acrobatem.
- **Ostré rámečky a šipky**: Pevný sytý obrys obdélníků s 15% průhlednou výplní a šipky s plným trojúhelníkovým hrotem.
- **Oprava známky v hlavičce**: Zajištěn správný výpočet a tisk písmene známky (A–F).

### 📚 Dokumentace & DevOps
- **Material for MkDocs**: Nasazen profesionální generátor dokumentace s přepínáním tmavého/světlého režimu a vyhledáváním.
- **Docker Compose & Portainer**: Konfigurace pro snadné nasazení s automatickou publikací obrazů do GitHub Container Registry (`ghcr.io/thelittlerock/praktika:latest` a `:dev`).
- **Rozdělení větví**: Nastavení workflow pro větve `dev` (vývoj) a `main` (produkční vydání).
- **Čisté repozitáře**: Odstranění testovacích souborů z repozitáře a jejich přidání do `.gitignore`.

---

## [v2.8.0] – 2026-10-16

- Přidána podpora hromadných operací (hromadné přiřazení asistenta, změna termínu, smazání).
- Přidána automatická záloha a manuální správa SQLite databáze do sekce Nastavení.
- Přidána diagnostická karta s informacemi o stavu serveru a diskovém úložišti.
- Zlepšena plynulost zoomování touchpadem a oddělení krokového zoomu myší.

---

## [v2.7.0] – 2026-10-15

- Implementován dokovatelný postranní panel AI Asistenta s možností přichycení vpravo i vlevo.
- Zavedena integrace s modelem Google Gemini 2.5 Flash pro fyzikální analýzu protokolů.
- Zaveden systém rychlých předvoleb komentářů pro cvičící.

---

## [v2.0.0] – 2026-10-14

- Přechod na monolitickou architekturu FastAPI + PDF.js + PyMuPDF.
- Zavedení strukturované čtyřpilířové hodnotící rubriky pro fyzikální praktika.
- Implementace generování exportního textu pro LMS Moodle.
