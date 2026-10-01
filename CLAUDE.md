# partAtlas — Arbeitsweise

- Führend ist `KONZEPT.md`. Alles auf Deutsch.
- **Tests sparsam:** nach einer Änderung nur die Suite, die sie prüft,
  und deren Gegenprobe. Alle Suiten nur ab und zu (vor einer Fassung).
  `tests/test_ui.py` nur, wenn sich die Oberfläche geändert hat — sie
  startet Chromium und ist teuer.
- **Eine Sache pro Antwort.** Nicht fünf Aspekte in einer Frage-Antwort
  bündeln; ein Verhalten durchdenken, bauen oder vorschlagen, dann das
  nächste.
- **Ton der Oberfläche:** Werkzeug, kein Assistent (KONZEPT §2).
  Fachbegriffe ja, sachlich und knapp; keine Wohlfühltexte.
