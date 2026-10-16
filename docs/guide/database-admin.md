# Správa databáze, diagnostika a nastavení

Sekce **Nastavení** je rozdělena na uživatelské preference cvičícího a administrátorskou správu databáze a diagnostiky serveru.

---

## 👤 Uživatelská nastavení (Per-User)

Každý přihlášený uživatel má přístup ke svým osobním preferencím:

- **Změna jména a hesla**: Správa přihlašovacích údajů a zobrazovaného jména na anotacích.
- **Osobní Gemini API klíč**: Vlastní klíč pro AI asistenta.
- **Nastavení zoomu a ovládání**:
    - **Plynulost touchpadu**: Možnost zvolit jemný multiplikátor pro plynulý touchpad zoom vs. krokový zoom myší (`Ctrl + Scroll`).
    - **Výchozí zvětšení**: Automatické přizpůsobení šířce okna (*Fit Width*) nebo 100% zobrazení.
    - **Směr zoomování**: Přirozené vs. invertované gesto zoomu.

---

## 🗄 Správa databáze (Pouze Administrátoři)

Administrátor má k dispozici nástroje pro bezpečný provoz databáze SQLite:

### Automatické zálohování
- Databáze podporuje režim **WAL (Write-Ahead Logging)**, který umožňuje bezpečné čtení a zápis bez zamykání.
- Možnost zapnout automatické denní zálohování s volbou maximálního počtu uchovávaných záloh (např. posledních 14 dní).

### Manuální záloha a obnova (Restore)
- **Vytvořit zálohu nyní**: Okamžitě provede atomický snapshot databáze do archivu v `data/backups/praktika_backup_YYYYMMDD_HHMMSS.sqlite3`.
- **Stažení zálohy**: Stažení archivu do počítače pro off-site archivaci.
- **Nahrát a obnovit**: Možnost nahrát existující zálohu a provést kompletní obnovení databázového stavu.

---

## 🩺 Diagnostika a stav systému

Diagnostická karta poskytuje administrátorovi reálný přehled o stavu serveru:

- **Velikost databáze a disku**: Aktuální velikost SQLite souboru a volné místo na disku.
- **Verze komponent**: Verze Pythonu, FastAPI, PyMuPDF a SQLite.
- **Počty záznamů**: Celkový počet protokolů, zapsaných anotací, hodnocení a registrovaných uživatelů.
- **Stav AI Engine**: Kontrola dostupnosti a odezvy Google Gemini API.
