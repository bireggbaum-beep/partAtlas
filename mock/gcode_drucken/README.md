# Konzept „G-Code und Reiter Drucken“ — Schemas und Mock (29./30.10.2026)

Entstanden im Gespräch mit dem Anwender, nachdem der Tester G-Codes aus dem Slicer in den Ordner exportiert und keine Zuordnung gefunden hat.
**Noch nicht in `KONZEPT.md`** — erst mit dem Anwender abstimmen, dann dort festhalten. Die `.html` sind die Quellen; die `.png` daraus gerendert
(Chromium, 2×). `drucken_mock.html` zeigt Bilder relativ (`gc1z.png`).

| Datei | Zeigt |
|---|---|
| `gcode_kette.png` | **Heute:** vier Stationen (Modell → Slicen → an den Drucker → Druck) und was PartAtlas 1.0.5 an jeder weiss. G-Code im Ordner ist unsichtbar. |
| `gcode_plan.png` | **Planungsstand** nach KONZEPT.md und OFFEN.md: gebaut, offen, zurückgestellt (25.10.). |
| `gcode_fluss.png` | **Vorschlag:** der G-Code gibt es einmal am Modell, egal wie er kam; „Gedruckt …“ legt den Druck an; ein Reiter „Drucken“ statt „Slicer“ + „Drucke“. Grün bleibt, orange neu, grau entfällt. |
| `drucken_mock.png` | **Mock** des Reiters „Drucken“ (dunkles Schema C, Halter des Testers): oben „Im Slicer öffnen“ und „Nochmal drucken“, darunter der Verlauf des Modells, unten die verfügbaren G-Codes. |

## Was entschieden ist (Anwender)
- Die Richtung stimmt: **ein Reiter „Drucken“ je Modell**, oben Verlauf und Drucken, unten die verfügbaren G-Codes.
- **Ein G-Code ist vor und nach dem Druck derselbe** — er gehört einmal zum Modell; Drucke hängen an ihm (Tester).
- **Lose G-Codes** (automatisch eingelesen) hängen am Modell, man kann sie drucken; sie haben eine **Druckhistorie** und man kann die Drucke **bewerten**.
- **Es gibt zwei Sichten auf dieselbe Liste:** Verlauf des Modells (alle Drucke, auch ohne G-Code) und Historie eines G-Codes (nur seine Drucke). Jeder Druck wird nur einmal gespeichert.
- **„Gedruckt ohne G-Code“ gibt es immer:** Modell im Slicer öffnen und von dort drucken. Der G-Code kann später nachkommen (vom Drucker geholt oder exportiert) und der Druck wandert darunter.
- Ein exportierter G-Code ist **vorbereitet, nicht gedruckt**. „Gedruckt“ sagt nur der Mensch (oder später der Drucker).

## Noch offen
- Zuordnung beim Einlesen: eindeutige G-Codes still zuordnen, unklare unter Bereinigen? (Vorschlag; Inhalt nennt das Quellmodell: `; printing object "…"`, `EXCLUDE_OBJECT_DEFINE NAME=…`, tolerant vergleichen, der Slicer schreibt Sonderzeichen um.)
- Nie gedruckte G-Codes aus PartAtlas entfernen (Datei im Ordner bleibt)? Stern/Referenz am G-Code statt am Druck?
- Mock noch nicht mit dem Tester besprochen („Wie ist es geworden?“-Zeile, „nicht gedruckt“). G-Code später vom Drucker holen = eigene Entscheidung (Anwender 25.10.: keine Druckeranbindung).
- Aufwand grob 3–4 in zwei bis drei Paketen (zwei Reiter zu einem, Einlesen von G-Code, Kante Modell → G-Code, Umzug bestehender G-Codes).
- Weitere Rückmeldung des Testers: ASN öffnet einen G-Code im Betrachter (Einstellungen gesperrt, Senden an den Drucker geht) → Knopf „Nochmal“ öffnet den fertigen G-Code, ändern geht nur über das Modell.
