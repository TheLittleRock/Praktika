# Praktika – Systém pro hodnocení laboratorních protokolů

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyMuPDF](https://img.shields.io/badge/PyMuPDF-1.24%2B-orange.svg)](https://pymupdf.readthedocs.io/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.5-4285F4.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-GHCR-2496ED.svg?logo=docker&logoColor=white)](https://github.com/TheLittleRock/Praktika/pkgs/container/praktika)
[![Documentation](https://img.shields.io/badge/Docs-Material%20for%20MkDocs-526cfe.svg?logo=materialformkdocs&logoColor=white)](https://thelittlerock.github.io/Praktika/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Praktika** je webová aplikace pro vyučující a asistenty fyzikálních praktik, určená k efektivní, objektivní a detailní revizi studentských protokolů v PDF formátu.

Nabízí interaktivní korekční studio s vektorovými kreslícími nástroji (zvýrazňovač, pero, tvary, šipky, poznámky kompatibilní s Adobe Acrobatem), asistenci jazykového modelu **Google Gemini 2.5 Flash** s českými fyzikálními rubrikami a export hodnocení připravený pro LMS Moodle.

📖 **Kompletní dokumentace projektu:** [https://thelittlerock.github.io/Praktika/](https://thelittlerock.github.io/Praktika/)

---

## 🎬 Ukázka rozhraní a práce v aplikaci

### 1. Interaktivní workflow v Korekčním PDF Studiu (Animace)
Reálná ukázka práce v aplikaci: kreslení a výběr geometrických tvarů, manipulace a mazání, zobrazení panelu AI asistenta se schválením návrhu v textu a zadávání bodových srážek:

![Interaktivní práce v Korekčním PDF Studiu](docs/assets/images/studio_workflow.webp)

---

### 2. Řídicí panel (Dashboard) & Správa protokolů
Okamžitý přehled stavu odevzdaných prací, filtrování podle semestrů a termínů, statistiky a hromadný export:

![Řídicí panel](docs/assets/images/dashboard_overview.png)

---

### 3. AI Asistent (Google Gemini) s podporou jazyků
Boční panel s hloubkovou analýzou, fyzikálními připomínkami (*interpunkce vzorců ", kde"*, *errorbary*, *citace grafů v textu*) a rychlým schvalováním:

![AI Asistent](docs/assets/images/studio_ai_drawer.png)

---

### 4. Exportované opravené PDF s Moodle komentářem
Výstupní PDF s přehlednou hodnoticí hlavičkou, vektorovými anotacemi s diakritikou a samolepicí Acrobat poznámkou pro Moodle:

![Exportované PDF](docs/assets/images/pdf_export_sample.png)

---

### 5. Interaktivní studentský náhled a Tmavý režim (`/v/{share_token}`)
Responzivní webový náhled pro studenty s plnohodnotným živým vykreslovacím jádrem (Studio Engine), interaktivními tooltipy při najetí myší, přepínáním do tmavého režimu (Dark Mode), přehledem bodů a celkovým slovním hodnocením asistenta:

![Interaktivní studentský náhled a tmavý režim](docs/assets/images/clip_student_view.webp)

---

## 🚀 Rychlá instalace

### Varianta A: Spuštění přes Docker & Portainer (Doporučeno)

Předpřipravené kontejnery jsou automaticky publikovány do GitHub Container Registry (GHCR).

Vytvořte soubor `docker-compose.yml`:

```yaml
version: '3.8'

services:
  praktika:
    image: ghcr.io/thelittlerock/praktika:latest
    container_name: praktika
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - praktika_data:/app/data
    environment:
      - PRAKTIKA_DATA_DIR=/app/data
      - PRAKTIKA_SECRET_KEY=zvolte-tajny-nahodny-klic
      - GEMINI_API_KEY=vas-volitelny-gemini-klic

volumes:
  praktika_data:
    name: praktika_data
```

Spusťte kontejner:
```bash
docker compose up -d
```

Aplikace bude dostupná na adrese `http://localhost:8000`.  
Výchozí přihlašovací údaje správce: **Uživatel:** `admin`, **Heslo:** `admin123`.

> [!TIP]
> Pro testování nejnovější vývojové verze nastavte `image: ghcr.io/thelittlerock/praktika:dev`.

---

### Varianta B: Lokální instalace (Python 3.10+)

```bash
# 1. Klonování repozitáře
git clone https://github.com/TheLittleRock/Praktika.git
cd Praktika

# 2. Vytvoření virtuálního prostředí
python3 -m venv venv
source venv/bin/activate

# 3. Instalace závislostí
pip install -r requirements.txt

# 4. Spuštění serveru
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌿 Struktura větví repozitáře

Projekt dodržuje standardní větvení:

- **`main`**: Stabilní produkční verze. Každý push do `main` automaticky publikuje Docker image `:latest` a aktualizuje GitHub Pages dokumentaci.
- **`dev`**: Aktivní vývojová větev. Všechny nové funkce a opravy směřují do `dev` a generují Docker image `:dev`. Po otestování je větev sloučena do `main`.

---

## 📄 Licence a historie změn

Projekt je licencován pod otevřenou licencí [MIT](LICENSE).  
Přehled všech novinek a úprav naleznete v **[Changelogu](docs/changelog.md)**.
