# partAtlas — Stand und nächste Schritte

Arbeitsstand für den nächsten Chat. Führend bleibt `KONZEPT.md`; hier steht,
was gerade offen ist und was entschieden wurde. Nach jeder erledigten Sache
aktualisieren.

## Zuerst wissen

- **Server und Tests laufen nur mit `flatgraph`.** In Cloud-Sitzungen ist
  `flatgraphdb` nur erreichbar, wenn es beim Start als Repository
  angehängt wurde (öffentlich reicht nicht; ohne Anhängen: HTTP 403).
  Ohne flatgraph lassen sich weder die Suiten noch `tests/test_ui.py`
  ausführen. Erst prüfen: `python3 -c "import flatgraph"`.
- **Nie geprüft, weil flatgraph fehlte:** die neuen Prüfungen in
  `tests/test_ui.py` (Runde 1 und 2). Bei der ersten Gelegenheit laufen
  lassen und Fehler beheben. Geprüft wurden nur der DOM-Abgleich
  (`abgleichen()` in `app.js`) und das fixierte Kopfstück des Inspektors,
  je isoliert in Chromium.
- Arbeitsweise: `CLAUDE.md` (eine Sache pro Antwort, Tests sparsam).

## Erledigt

Runde 1 (13 Punkte): verlorene Klicks (Ursache: GET schrieb
`zuletzt_angesehen` → Live-Meldung → komplettes Neuzeichnen; jetzt kein
Schreiben mehr und Abgleich statt `innerHTML`), Enter im Dialog = Hauptaktion,
Kaufteile-Wähler (feste Höhe, alle Kategorien, ✓ nimmt zurück), Baugruppe
(Name/Beschreibung an Ort und Stelle, ganze Zeile klickbar, Notizfeld raus,
Raster/Liste/Sortieren dort ausgeblendet), Seitenleisten in der Breite
ziehbar, schmale Scrollleisten, Zähler „Neu hinzugefügt“.

Runde 2: **c)** Inspektor: Vorschau und Name bleiben oben fest, die
technischen Daten heissen „Modelldaten“, stehen unter „Zum Drucken“ und
sind standardmässig offen.

Runde 3: **Bereinigen** — „Aufräumen“ ist aus der Seitenleiste raus; in der
Activity Bar sitzt statt des Papierkorbs ein Besen (🧹) mit Zählabzeichen
(Duplikate + fehlt + unlesbar). Er schaltet die ganze Seitenleiste um:
Papierkorb · Duplikate · Datei fehlt · Unlesbar. Ungeprüft in Chromium
(flatgraph fehlte); die zwei angepassten Prüfungen in `tests/test_ui.py`
stehen noch aus. Später mögliche Kategorien: Nicht verknüpft, Ohne Vorschau.

## Offen, in dieser Reihenfolge

1. **Warteschlange (a, b)** — entschieden, noch nicht gebaut:
   - Die Warteschlange besteht aus **Einträgen**: eine Baugruppe oder ein
     Einzelmodell, mit Anzahl Sätze. Eigener Knotentyp statt Feld
     `queue_position` am Modell; KONZEPT §6.1 anpassen; bestehende
     Positionen übernehmen.
   - **Seitenleiste als Baum:** Baugruppe (🧩) oberste Ebene, ihre offenen
     Teile mit Menge darunter, aufklappbar. Einzelmodelle auf gleicher
     Ebene mit eigenem Symbol (🧊). Dieselbe Baugruppe zweimal = ein Eintrag
     „×2 Sätze“.
   - Ziehen verschiebt die oberste Ebene (Baugruppe samt Teilen).
   - Abschnitt einklappbar, begrenzte Höhe mit eigenem Scrollen.
   - Block verschwindet, wenn alle Teile gedruckt sind; „Fehlende in die
     Warteschlange“ legt einen Baugruppen-Eintrag an.
   - Sortieren-Knopf in der Warteschlange ausblenden (wie in der
     Baugruppenansicht).
2. **d) Rechte Seitenleiste:** Informationsdichte. Richtung: Reiter.
   Erst zusammen entwerfen, dann bauen. Vorbild ist 3MF Katalog o. ä.,
   **nicht pDMS** (zu geringe Dichte).
3. **e) Listenansicht:** Spalten ein-/ausblenden, in der Breite ziehen,
   Spalte „Baugruppe“. Sie ist heute zu starr.

Hinweis: Bestehende Notizen an Baugruppen-Positionen sind nur noch als Text
sichtbar, nicht bearbeitbar — bewusst, Testbestand.
