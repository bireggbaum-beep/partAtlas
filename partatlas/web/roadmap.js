// Die Roadmap im Programm: was schon da ist, was als Nächstes kommt, was später folgt. Plakativ — eine Überschrift und
// ein kurzer Satz je Punkt. Eine Reihenfolge, keine Termine. Wer etwas fertigstellt, schiebt es von „Als Nächstes“ nach „Jetzt“;
// die Quelle der Wahrheit bleibt KONZEPT §7 und OFFEN.md.
const ROADMAP = [
  ["Jetzt da", "da", [
    ["Katalog", "Ordner einlesen, Vorschaubilder, 3D-Ansicht, Suche und gemerkte Suchen, Tags, Sammlungen, Varianten — in Raster, Liste und Karten."],
    ["Ordnen wie im Dateimanager", "Ordner anlegen, umbenennen, verschieben; Modelle umbenennen direkt am Namen; Rückgängig mit Strg+Z."],
    ["Baugruppen", "Stückliste mit Mengen und Kaufteilen, Notizen und Anhänge, Filament und Druckzeit über alle Ebenen, als PDF."],
    ["Drucke festhalten", "Wann, womit, wie es wurde — mit Foto und G-Code. Einstellungen in Worten, zwei Drucke im Vergleich."],
    ["Filament-Lager", "Spulen erfassen, nachkaufen, beim Druck abziehen, Kosten — und vorher wissen: reicht das Filament?"],
    ["Aufräumen ohne Risiko", "Fehlende und doppelte Dateien, Archiv, Papierkorb, automatische Sicherungen — partAtlas löscht in deinen Ordnern nichts."],
  ]],
  ["Als Nächstes", "naechst", [
    ["Versionsverlauf", "Frühere Fassungen einer Datei aufheben, ansehen und als Kopie zurückholen — „gestern war es noch richtig“."],
    ["Backup und Wiederherstellen", "Katalog und Dateien in eine ZIP-Datei, und sicher zurück: immer als neuer Bestand neben dem alten."],
    ["Warteschlange", "Was als Nächstes gedruckt wird, in einer Reihenfolge, die du ziehen kannst. Gebaut, aber noch ausgeblendet."],
  ]],
  ["Später", "spaeter", [
    ["Drucker anbinden", "Moonraker, PrusaLink und Bambu im Heimnetz; Temperatur- und Verlaufskurven am Druck."],
    ["Mehrere Drucker", "Prüfen, welcher Drucker passt, eine gemeinsame Warteschlange, STL mit deinen Referenzeinstellungen slicen."],
    ["Zugriff aus dem Heimnetz", "Mit Passwort, damit auch Tablet und Handy mitmachen. Bis dahin bleibt partAtlas bewusst nur auf diesem Rechner."],
  ]],
];

async function roadmap() {
  const fassung = $("#version")?.textContent || "";
  await dialog(`<h2>Wohin partAtlas geht</h2>
    <p class="dim">${fassung ? `Du hast Fassung ${esc(fassung)}. ` : ""}Eine Reihenfolge, keine Termine — was kommt, kann sich verschieben.</p>
    <div class="rm">${ROADMAP.map(([titel, art, punkte]) => `
      <section class="rm-gruppe rm-${art}"><h3>${esc(titel)}</h3>
        ${punkte.map(([name, text]) => `<div class="rm-punkt"><b>${art === "da" ? "✓ " : ""}${esc(name)}</b><span>${esc(text)}</span></div>`).join("")}
      </section>`).join("")}</div>
    <div class="knoepfe"><button class="knopf akzent" value="ok">Schließen</button></div>`);
}

document.addEventListener("click", (e) => { if (e.target.closest?.("#roadmap")) roadmap(); });
