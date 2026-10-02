// Die Roadmap im Programm: was schon da ist, was als Nächstes kommt, was später folgt. Plakativ — eine Überschrift und
// ein kurzer Satz je Punkt. Eine Reihenfolge, keine Termine. Wer etwas fertigstellt, schiebt es von „Als Nächstes“ nach „Jetzt“;
// die Quelle der Wahrheit bleibt KONZEPT §7 und OFFEN.md.
const ROADMAP = [
  ["Jetzt da", "da", [
    ["Katalog", "Ordner einlesen, Vorschaubilder, Suche, Tags, Sammlungen, 3D-Ansicht — in Raster, Liste und Karten, auch gruppiert."],
    ["Baugruppen", "Stückliste mit Mengen und Kaufteilen, Filament und Druckzeit über alle Ebenen, als PDF zum Ausdrucken."],
    ["Drucke festhalten", "Wann, mit welchem Filament, wie es wurde — mit Foto. Der beste Druck wird zur Referenz: „so war es gut“."],
    ["Öffnen im Slicer und CAD", "Ein Klick auf deinem Rechner, mit den Programmen, die du in den Einstellungen wählst."],
  ]],
  ["Als Nächstes", "naechst", [
    ["Notizen und Anhänge", "An jeder Baugruppe: Konstruktionsnotizen in Markdown, dazu Montageanleitungen und Zeichnungen als Dateien."],
    ["Schnelleres Einlesen", "Vorschaubilder im Hintergrund vorbauen, damit auch große Sammlungen sofort zügig aufgehen."],
    ["G-Code zuordnen", "Das Ergebnis aus dem Slicer einem Modell zuordnen und die Einstellungen daraus übernehmen."],
    ["Warteschlange", "Was als Nächstes gedruckt wird, in einer Reihenfolge, die du ziehen kannst. Gebaut, aber noch ausgeblendet."],
  ]],
  ["Später", "spaeter", [
    ["Filament-Lager", "Spulen und Fächer erfassen, abbuchen und vorher wissen: reicht das Filament für diesen Druck?"],
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
