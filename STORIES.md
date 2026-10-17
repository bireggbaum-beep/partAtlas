# partAtlas — Nutzungsprofile und Geschichten

Zweck: den roten Faden sichtbar machen (Anwender, 17.10.2026: „fühlt sich nicht
ganz rund an“) und daraus das Profil der weiteren Fassungen ableiten.
Massstab: KONZEPT §0. **Stand der Geschichten ist ein Entwurf und eine
Einschätzung aus dem Code und den Rückmeldungen, nicht getestet** — jede
Geschichte wird durchgespielt, bevor ihr Stand als gesichert gilt.

## Profile — wofür partAtlas benutzt wird

Ein Anwender ist meist mehrere davon, in dieser Reihenfolge der Tiefe:

1. **Verwalten.** Eine wachsende Sammlung von Dateien ordnen, finden,
   aufräumen, sichern. Die einfachste Stufe; ohne sie hat nichts anderes
   Boden. *Heute am weitesten.*
2. **Drucken.** Von der Datei zum Druck: im Slicer öffnen, drucken, festhalten,
   was eingestellt war und wie es lief; später genauso nochmal.
   *Teilweise da (Druckhistorie, Referenz, Vergleich), von der Verwaltung
   aus noch nicht selbstverständlich erreichbar.*
3. **Entwickeln.** Ein Teil ändert sich über die Zeit: Fassungen, Baugruppen,
   Stückliste, was gehört zusammen. *Baugruppen da, Versionsverlauf fehlt.*
4. **Betreiben** (später). Drucker, Lager, Warteschlange über mehrere Geräte.
   *Phase 3 und 4 im KONZEPT; nur bei echtem Bedarf.*

Der rote Faden läuft durch alle vier: **dasselbe Modell, von der Ankunft bis
zur letzten Fassung und dem letzten Druck.** Fehlt er irgendwo, wirkt
partAtlas wie ein Nachschlagewerk statt wie ein Werkzeug.

**Gewichtung nach dem Tester (17.10.2026):** Verwalten und Entwickeln zählen
am meisten; Drucken reicht ihm über „Öffnen in …“ und die Schnelltasten. Sein
Alltag: Er baut Dinge, die aus viel mehr als Druckteilen bestehen. Das
gedruckte Teil (z. B. eine Schleifwalze) ist nur eine Komponente, und es
entwickelt sich weiter: optimiert, oder als Variante (längere Walze nach Norm).
Die Frage ist also nicht „welche Fassung dieser Datei“, sondern
**„welche Fassung oder Variante gehört in welches Ganze“.**

## Geschichten

Stand: **ja** = geht durchgehend · **Lücke** = geht mit benannter Lücke ·
**nein** = fehlt.

### Verwalten

**V1 Ankommen.** Ich habe ein Modell als ZIP oder Einzeldatei geladen und will
es im Katalog finden, ohne es von Hand einzusortieren.
Stand: *ja.* Ordner werden an Ort und Stelle gelesen, Archive entpackt, Tags
automatisch. Lücke: 7z und rar.

**V2 Wiederfinden.** Ich weiss nur „das Halterchen mit dem Clip“ und finde es
über Suche, Tags, Ordner oder Sammlungen.
Stand: *ja.* Offen: die Suche kennt keine Eigenschaften wie Grösse oder Volumen
als Filter.

**V3 Ordnen wie im Dateimanager.** Ich benenne um, verschiebe, lege Ordner an,
nehme es zurück.
Stand: *ja* (1.0), Windows-Prüfung steht aus.

**V4 Aufräumen.** Meine Sammlung ist gewachsen; Doppeltes, Totes und
Unlesbares soll weg, ohne dass ich etwas verliere.
Stand: *ja.* Papierkorb, nichts wird auf der Platte gelöscht.

**V5 Umziehen und Sichern.** Neuer Rechner oder Festplattenschaden: alles ist
wieder da.
Stand: *Lücke.* Automatische Sicherung der Datenbank gibt es; Backup als
Datei und sicheres Wiederherstellen sind zurückgestellt (OFFEN).

**V6 Installieren und aktuell bleiben.** Ich lade eine Datei, starte sie per
Doppelklick, und neue Fassungen kommen von allein.
Stand: *nein.* Das ist der Tauri-Schritt.

### Drucken

**D1 Aussuchen und starten.** Ich finde ein Teil, öffne es im Slicer, drucke es.
Stand: *ja* für das Öffnen; was ich dabei einstelle, wird nicht von selbst
erfasst.

**D2 Festhalten.** Nach dem Druck lege ich fest, wie er lief: Ergebnis, Foto,
G-Code, Einstellungen.
Stand: *Lücke.* Druckeintrag mit Foto und G-Code ist da; ob der Weg dorthin
vom Modell aus kurz genug ist, ist ungeprüft.

**D3 Nochmal wie damals.** Ich will genau so drucken wie beim besten Druck.
Stand: *Lücke.* Referenz je Modell und Vergleich zweier Drucke sind da; „Nochmal“
direkt auf den Drucker ist es nicht.

**D4 Echte Slicer-Dateien.** Meine 3MF/G-Code aus Bambu Studio oder
Anycubic Slicer Next werden richtig gelesen.
Stand: *ungeprüft.* Wartet auf echte Dateien vom Tester.

### Entwickeln

**E1 Neue Fassung.** Ich ändere ein Teil, und die alte Fassung bleibt greifbar
und vergleichbar.
Stand: *nein.* Versionsverlauf je Modell, hoch priorisiert (OFFEN).

**E2 Baugruppe.** Ich halte fest, welche Teile zu einem Produkt gehören, wie
viele ich brauche, was fehlt.
Stand: *ja.* Baugruppen mit Stückliste, Kaufteilen, Fortschritt, Einkaufsliste.

**E3 Aus CAD.** Meine STEP- und FCStd-Dateien haben eine Vorschau und Masse.
Stand: *Lücke.* Nur mit FreeCAD oder dem eingebetteten Thumbnail; ohne
FreeCAD keine Geometrie (Entscheidung zusammen mit Tauri).

## Was daraus folgt (Vorschlag, der Anwender entscheidet)

- Die Lücken liegen fast alle an den **Nahtstellen** zwischen den Profilen:
  Modell → Druck (D1–D3) und Modell → Fassung (E1). Dort entsteht der Faden.
- Reihenfolge nach dem Desktop-Programm: E1 und V5 gehören zusammen
  (Fassung und Sicherung teilen sich die Frage, wie alte Stände sicher
  daneben liegen); danach D2/D3 am Modell statt in einer eigenen Ecke.
- Betreiben bleibt, bis jemand es braucht.
