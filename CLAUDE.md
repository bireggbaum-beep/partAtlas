# partAtlas — Arbeitsweise

- Führend ist `KONZEPT.md`. Alles auf Deutsch.
- **Tests sparsam:** nach einer Änderung nur die Suite, die sie prüft,
  und deren Gegenprobe. Alle Suiten nur ab und zu (vor einer Fassung).
  `tests/test_ui.py` nur, wenn sich die Oberfläche geändert hat — sie
  startet Chromium und ist teuer.
