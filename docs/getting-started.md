# Rychlý start s Praktika Evaluation Studio

Tento průvodce vás provede základními kroky od spuštění aplikace a prvního přihlášení až po kompletní workflow opravy laboratorního protokolu.

---

## 1. Přihlášení do aplikace

Po spuštění aplikace (lokálně nebo v Docker kontejneru) otevřete webový prohlížeč na adrese:

```
http://localhost:8000
```

Při prvním spuštění se zobrazí přihlašovací okno. Výchozí účet hlavního správce aplikace má tyto přihlašovací údaje:

| Položka | Hodnota |
| :--- | :--- |
| **Uživatelské jméno** | `admin` |
| **Výchozí heslo** | `admin123` |
| **Role** | Správce aplikace (admin) |

> [!TIP]
> Po prvním přihlášení doporučujeme změnit výchozí heslo v záložce **⚙ Nastavení -> 🔒 Změna hesla**.

---

## 2. Hlavní přehled (Dashboard)

Po přihlášení se zobrazí hlavní řídicí panel aplikace:

![Přehled řídicího panelu](assets/images/dashboard_overview.png)

Na řídicím panelu máte k dispozici:
- **Přepínač semestrů**: Umožňuje přepínat mezi aktuálním a minulými semestry (např. *ZS 2026/2027*).
- **Informativní statistické karty**: Okamžitý přehled celkového počtu odevzdaných prací, rozpracovaných konceptů, dokončených protokolů a průměrné známky.
- **Rychlý filtr a vyhledávání**: Filtrování podle konkrétní laboratorní úlohy, rozvrhového termínu, cvičícího nebo stavu.

---

## 3. Nahrání studentských protokolů

1. V horní nástrojové liště klikněte na tlačítko **+ Nahrát protokoly**.
2. Otevře se dialog pro nahrání souborů:

![Okno nahrání protokolů](assets/images/upload_modal.png)

3. Zvolte semestr, termín cvičení (např. *Středa 8:00*) a laboratorní úlohu.
4. Přetáhněte jeden nebo více PDF souborů do vyznačené zóny.
5. Systém automaticky analyzuje text v hlavičce PDF a extrahuje jméno studenta.
6. Klikněte na **Nahrát protokol(y)**. Pokud je v nastavení povolen AI asistent s volbou automatické analýzy, protokol se ihned na pozadí připraví k vyhodnocení.

---

## 4. Výběr příručky podle vaší role

Aplikace rozlišuje specifické potřeby asistentů (cvičících) a správců systému:

<div class="grid cards" markdown>

-   :material-account-edit:{ .lg .middle } __[Příručka pro asistenty](guide/assistant.md)__

    ---

    Kompletní průvodce opravou protokolu:
    - Práce s kreslicími a anotačními nástroji
    - Výběr, přesouvání a mazání geometrických tvarů
    - Práce s návrhy AI asistenta a jejich schvalování v textu
    - Bodovací dock, katalogy častých chyb a export pro Moodle

    [:octicons-arrow-right-24: Přejít na příručku pro asistenty](guide/assistant.md)

-   :material-shield-crown:{ .lg .middle } __[Příručka pro správce](guide/admin.md)__

    ---

    Správa a konfigurace celého systému:
    - Správa semestrů a rozvrhových termínů
    - Správa laboratorních úloh a AI syntéza hodnoticích rubrik
    - Konfigurace Gemini AI modelů a jazyka výstupů
    - Uživatelské účty a správa SQLite databáze & zálohy

    [:octicons-arrow-right-24: Přejít na příručku pro správce](guide/admin.md)

</div>
