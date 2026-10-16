# Korekční PDF Studio

**Korekční PDF Studio** je srdcem celé aplikace. Umožňuje interaktivní revizi a kreslení poznámek přímo do odevzdaného dokumentu.

![Korekční PDF Studio](../assets/images/studio_overview.png)

---

## 🛠 Nástrojová lišta

V horní části Studia se nachází lišta s nástroji:

| Ikona / Nástroj | Klávesa | Popis |
|---|---|---|
| **Ruka / Výběr (Pan / Select)** | `H` | Posun plátna a výběr nakreslených objektů (zobrazení manipulačního rámečku s táhly a košem). |
| **Zvýrazňovač (Highlight)** | `S` | Vytváří ostré zvýraznění s podtržením přes vybrané řádky textu s volitelnou barvou. |
| **Přeškrtnutí (Strikeout)** | `X` | Červená přeškrtávací linka pro chybné vzorce nebo zavádějící text. |
| **Poznámka (Sticky Note)** | `N` | Vloží na libovolné místo v dokumentu vektorovou Acrobat-kompatibilní bublinu s komentářem. |
| **Volné pero (Pen)** | `P` | Hladké kreslení od ruky pro podtrhávání nebo ruční poznámky. |
| **Obdélník (Rect)** | `R` | Ohraničující rámeček s pevnou linkou a jemnou polo-průhlednou výplní (18 % opacita). |
| **Šipka (Arrow)** | `A` | Směrová šipka s ostrým plným hrotem ukazující na konkrétní chybu. |
| **Vepsaný text (Typewriter)** | `T` | Přímé vepsání textového řádku do PDF. |

---

## 📐 Výběr, posouvání a mazání nakreslených objektů

Od verze 2.10.0 je k dispozici plná manipulace se všemi nakreslenými tvary:
- **Aktivace výběru**: V režimu **Ruka / Výběr** (`H`) klikněte na libovolný tvar (obdélník, šipka, perokresba, text).
- **Manipulační rámeček**: Kolem objektu se objeví aktivní Acrobat rámeček se 4 rohovými body a červenou ikonou koše.
- **Přesouvání**: Uchopením a tažením myší lze objekt libovolně přemístit na nové místo.
- **Smazání**: Stiskněte klávesu **`Delete`** nebo **`Backspace`**, případně klikněte na **ikonu koše**.

---

## 🎨 Správa barev a nezávislost nástrojů

Aplikace striktně odděluje barvy pro budoucí kreslení od již nakreslených objektů:

- **Změna barvy v liště**: Nastavuje barvu výhradně pro **následující** kresby. Nikdy zpětně nepřepisuje barvu dříve nakreslených tvarů nebo perokreseb.
- **Změna barvy zvýraznění**: Pokud chcete změnit barvu konkrétního zvýraznění, otevřete jeho detail kliknutím. V editační kartě se zobrazí paleta šesti barevných teček. Kliknutím na barvu se okamžitě aktualizuje pouze toto jedno označení.
- **Výplň obdélníků**: Výplň obdélníku se automaticky přizpůsobuje zvolené barvě obrysu (např. modrý obrys má modrou průhlednou výplň, červený obrys červenou).

---

## 💬 Karta editace komentáře & rychlé předvolby

Kliknutím na jakoukoliv textovou poznámku nebo zvýraznění se otevře plovoucí editační karta:

1. **Jméno cvičícího a čas**: Automaticky zaznamenáno v metadatech anotace.
2. **Volba barvy**: Rychlé přepínání barev (červená, žlutá, zelená, modrá, růžová, oranžová).
3. **Pole pro text poznámky**: Podporuje libovolně dlouhý komentář s diakritikou.
4. **Čipy rychlých komentářů**: Předvolené časté připomínky (např. *„, kde... chybí čárka!“*, *„Graf není referencován v textu“*).
5. **Uložení do vlastních předvoleb**: Kliknutím na ⭐ lze napsaný text uložit do své osobní šablony pro další protokoly.
6. **Vazba na bodovou srážku**: Zaškrtnutím volby *Strhnout body* lze přímo z komentáře odečíst body (např. -0.25 b v kategorii Formát).

---

## 💾 Plovoucí automatické ukládání

V levém dolním rohu obrazovky se nachází minimalistický indikátor stavu:

- **Zelená tečka**: *Uloženo* (všechny změny jsou bezpečně zapsány v databázi na serveru).
- **Pulzující žlutá tečka**: *Ukládám...* (probíhá asynchronní zápis).
- **Oranžová tečka**: *Neuloženo* (změna čeká ve frontě na odeslání).

Indikátor je plně průhledný, neobsahuje žádné pozadí, překrývá PDF stránku bez kolize a **nikdy nezmenšuje ani neposouvá viewport dokumentu**.
