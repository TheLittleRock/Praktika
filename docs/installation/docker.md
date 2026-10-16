# Instalace přes Docker & Portainer

Aplikace Praktika je plně kontejnerizována a její předpřipravené obrazy jsou automaticky publikovány do **GitHub Container Registry (GHCR)** pro architektury `linux/amd64` i `linux/arm64`.

---

## 🐳 Rychlé spuštění přes Docker Compose

Nejjednodušší způsob nasazení je pomocí připraveného souboru `docker-compose.yml`:

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

### Příkazy pro spuštění:

```bash
# Stažení obrazu a spuštění kontejneru na pozadí
docker compose up -d

# Zobrazení logů běžící aplikace
docker compose logs -f

# Zastavení kontejneru
docker compose down
```

Po spuštění je aplikace dostupná v prohlížeči na adrese `http://vase-ip:8000`.

---

## 🚀 Nasazení v Portaineru

Aplikaci lze do prostředí **Portainer** nasadit během jedné minuty:

1. Přihlaste se do webového rozhraní Portaineru.
2. Přejděte do sekce **Stacks** a klikněte na **+ Add stack**.
3. Pojmenujte stack (např. `praktika`).
4. Zvolte metodu **Repository** nebo **Web editor**:
    - **Metoda Repository**:
        - **Repository URL:** `https://github.com/TheLittleRock/Praktika.git`
        - **Repository reference:** `refs/heads/main` (nebo `refs/heads/dev` pro vývojovou verzi)
        - **Compose path:** `docker-compose.yml`
    - **Metoda Web editor**: Vložte výše uvedený YAML kód přímo do editoru.
5. V sekci **Environment variables** nastavte proměnné:
    - `PRAKTIKA_SECRET_KEY`: Dlouhý náhodný řetězec pro šifrování relací.
    - `GEMINI_API_KEY`: Váš API klíč ze služby Google AI Studio (volitelné).
6. Klikněte na **Deploy the stack**.

---

## 🏷 Dostupné tagy obrazu (Image Tags)

V GitHub Container Registry jsou udržovány následující tagy:

| Tag | Větev v repozitáři | Popis |
|---|---|---|
| `:latest` | `main` | Stabilní produkční verze doporučená pro běžný provoz. |
| `:v2.9` | `main` | Konkrétní číslované vydání verze v2.9. |
| `:dev` | `dev` | Nejnovější vývojová verze obsahující čerstvé úpravy před vydáním. |

Pro přepnutí na vývojovou verzi stačí v konfiguraci uvést:
```yaml
image: ghcr.io/thelittlerock/praktika:dev
```
nebo nastavit proměnnou prostředí `PRAKTIKA_TAG=dev`.
