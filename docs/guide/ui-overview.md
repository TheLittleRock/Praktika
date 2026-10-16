# Uživatelské rozhraní a správa protokolů

Hlavní obrazovka aplikace slouží jako přehledný dashboard pro správu všech odevzdaných laboratorních prací.

---

## 📊 Přehledová tabulka protokolů

V tabulce jsou přehledně zobrazeny všechny klíčové informace o odevzdaných protokolech:

| Sloupec | Popis |
|---|---|
| **Výběr (Checkbox)** | Slouží pro hromadné operace (hromadné přiřazení asistenta, změna stavu, export nebo smazání). |
| **Student** | Jméno studenta extrahované automaticky z PDF nebo zadané manuálně. |
| **Úloha** | Číslo a oficiální název měřené úlohy z fyzikálního praktika. |
| **Termín** | Den v týdnu a čas cvičení (např. *Pondělí 14:00*). |
| **Cvičící** | Přiřazený asistent, který je za opravu zodpovědný. |
| **Stav** | Barevný indikátor: *K opravě* (oranžová), *Rozpracováno* (modrá), *K revizi* (žlutá), *Opraveno* (zelená). |
| **Body & Známka** | Celkový bodový zisk (např. *8.5 / 10*) a výsledná známka ECTS. |
| **AI Status** | Indikace stavu AI analýzy: *Připraveno*, *Analyzuji...*, nebo *Neanalyzováno*. |

---

## 🔍 Filtrování a vyhledávání

V horní liště tabulky jsou k dispozici rychlé filtry:

- **Fulltextové vyhledávání**: Okamžité filtrování podle jména studenta, názvu úlohy nebo termínu.
- **Filtr podle semestru**: Výběr akademického roku a semestru (např. *ZS 2025/2026*).
- **Filtr termínu**: Zobrazení pouze konkrétní studijní skupiny.
- **Filtr úloh**: Zobrazení konkrétní fyzikální úlohy.
- **Rychlé záložky**:
    - **Všechny**: Kompletní seznam prací.
    - **Moje protokoly**: Zobrazuje pouze protokoly přiřazené aktuálně přihlášenému vyučujícímu (včetně čerstvě nahraných).
    - **K opravě**: Zobrazuje práce čekající na hodnocení.
    - **Opraveno**: Dokončené protokoly.

---

## ⚡ Hromadné akce (Bulk Operations)

Zaškrtnutím jednoho nebo více protokolů se nad tabulkou automaticky zobrazí panel hromadných akcí:

- **Hromadné přiřazení asistenta**: Převedení vybraných protokolů na jiného cvičícího.
- **Hromadná změna termínu / úlohy**: Hromadná úprava metadat při přesunu studenta mezi skupinami.
- **Hromadné smazání**: Bezpečné odstranění záznamů včetně přidružených PDF souborů a anotací (s potvrzovacím dialogem).
