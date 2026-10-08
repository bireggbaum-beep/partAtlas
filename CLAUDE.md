# partAtlas — Arbeitsweise

- Führend ist `KONZEPT.md`. Alles auf Deutsch.
- Stand, Entscheidungen und nächste Schritte: `OFFEN.md` — zu Beginn lesen,
  nach jeder erledigten Sache aktualisieren.
- **Tests sparsam:** nach einer Änderung nur die Suite, die sie prüft,
  und deren Gegenprobe. Alle Suiten nur ab und zu (vor einer Fassung).
  `tests/test_ui.py` nur, wenn sich die Oberfläche geändert hat — sie
  startet Chromium und ist teuer.
- **`test_ui.py` komplett NUR unmittelbar vor einem Push auf `main` für den Tester** (Vorgabe des Anwenders, 8.10.2026, nach zu vielen
  Läufen) — nicht je Fassung auf dem Branch, nicht nach jedem Paket. Sonst nur die geänderten Prüfungen gezielt (eigenes kleines Skript).
- **`test_ui.py` nie mehrfach hintereinander komplett** (Vorgabe des Anwenders, 7.10.2026). Gegenproben
  für Oberflächen-Prüfungen gezielt, nicht als ganze Suite. Prüfungen nur für Verhalten, das unbemerkt kaputtgehen kann — nicht für
  einmalige Gestaltung (Farben, Abstände, Aufbau eines Panels).
- **Jede Suite hat eine Zeitgrenze** (`muster.zeitgrenze`): hängt sie, bricht sie ab und zeigt die Zeile.
- **Arbeit in kleinen Paketen:** vorher sagen, was und wie lange; nach spätestens ~10 Minuten anhalten und berichten.
- **Eine Sache pro Antwort.** Nicht fünf Aspekte in einer Frage-Antwort
  bündeln; ein Verhalten durchdenken, bauen oder vorschlagen, dann das
  nächste.
- **Ton der Oberfläche:** ein gutes Werkzeug (KONZEPT §2) — freundlich,
  den Anwender ernst nehmend, weder kindisch noch übertechnisch.
