// Anhänge und Notizen (anhaenge.py): an Modellen im Reiter Übersicht, an Baugruppen in eigenen Reitern.
//
// Ein Anhang ist eine Kopie im Bestand (Entscheid 12.10.2026). Ansehen im Browser nur für PDF, Bilder und Text; „Öffnen“ startet eine
// Kopie im Programm des Rechners — ändert man sie, hängt man die neue Fassung wieder an. Hineinziehen auf die Liste hängt an.

const ANH_SYMBOL = { pdf: "PDF", cdr: "CDR", svg: "SVG", dxf: "DXF", dwg: "DWG", png: "Bild", jpg: "Bild", jpeg: "Bild", webp: "Bild",
                     txt: "Text", md: "Text", docx: "DOC", doc: "DOC", xlsx: "XLS", zip: "ZIP", step: "STEP", stp: "STEP" };
const anhGroesse = (b) => b >= 1048576 ? `${zahl(b / 1048576, 1)} MB` : `${zahl(Math.max(1, b / 1024), 0)} kB`;

function anhaengeHtml(art, id, liste, { leerText = "Noch nichts angehängt." } = {}) {
  const zeilen = liste.map((a) => {
    const endungA = (a.name.split(".").pop() || "").toLowerCase();
    return `<div class="anh-zeile" data-anh="${esc(a.k)}">
      <span class="anh-typ">${esc(ANH_SYMBOL[endungA] || endungA.toUpperCase().slice(0, 4) || "?")}</span>
      <a class="anh-name" href="${esc(a.url)}${a.anzeigen ? "" : "?herunterladen=1"}" ${a.anzeigen ? 'target="_blank" rel="noopener"' : "download"}
         title="${a.anzeigen ? "Im Browser ansehen" : "Herunterladen"}: ${esc(a.name)}">${esc(a.name)}</a>
      <span class="anh-groesse dim">${anhGroesse(a.groesse)}</span>
      <span class="anh-akt">
        <button type="button" data-anh-oeffnen title="Mit dem Programm des Rechners öffnen (eine Kopie — Änderungen als neue Fassung wieder anhängen)">↗</button>
        <a href="${esc(a.url)}?herunterladen=1" download title="Herunterladen">⤓</a>
        <button type="button" data-anh-name title="Umbenennen">✎</button>
        <button type="button" data-anh-weg title="Entfernen — die Datei kommt ins Archiv des Bestands, nicht weg">×</button></span></div>`;
  }).join("");
  return `<div class="anh-ziel" data-anh-art="${art}" data-anh-id="${esc(id)}">
    ${zeilen || `<p class="dim anh-leer">${leerText}</p>`}
    <button type="button" class="knopf klein anh-plus" data-anh-plus>＋ Datei anhängen</button>
    <span class="dim anh-tipp">oder hierher ziehen</span></div>`;
}

async function anhaengeHochladen(art, id, dateienListe) {
  let n = 0;
  for (const f of dateienListe) {
    try {
      const r = await fetch(`/api/anhaenge/${art}/${encodeURIComponent(id)}?name=${encodeURIComponent(f.name)}`, { method: "POST", body: f });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.fehler || d.detail || `${f.name} nicht angehängt.`);
      n++;
    } catch (e) { toast(e.message); }
  }
  if (n) toast(n === 1 ? "Angehängt." : `${n} Dateien angehängt.`);
  anhNeuZeichnen(art, id);
}

function anhNeuZeichnen(art, id) {
  if (art === "modell" && zustand.gewaehlt === id) { zustand.angezeigt = null; waehle(id); }
  if (art === "baugruppe" && typeof ladeBaugruppe === "function") ladeBaugruppe();
}

const anhWahl = Object.assign(document.createElement("input"), { type: "file", multiple: true, hidden: true });
document.body.append(anhWahl);
anhWahl.addEventListener("change", () => {
  const z = anhWahl.ziel;
  const f = [...anhWahl.files];
  anhWahl.value = "";
  if (z && f.length) anhaengeHochladen(z.art, z.id, f);
});

document.addEventListener("click", async (e) => {
  const ziel = e.target.closest?.(".anh-ziel");
  if (!ziel) return;
  const art = ziel.dataset.anhArt, id = ziel.dataset.anhId;
  if (e.target.closest("[data-anh-plus]")) { anhWahl.ziel = { art, id }; return anhWahl.click(); }
  const zeile = e.target.closest("[data-anh]");
  if (!zeile) return;
  const k = zeile.dataset.anh;
  try {
    if (e.target.closest("[data-anh-oeffnen]")) return await api(`/api/anhaenge/${art}/${id}/${k}/oeffnen`, { method: "POST" });
    if (e.target.closest("[data-anh-weg]")) {
      const r = await rueckfrage(`<h2>Anhang entfernen?</h2><p>„${esc(zeile.querySelector(".anh-name").textContent)}“ verschwindet aus der Liste.
        Die Datei kommt ins Archiv des Bestands — partAtlas löscht nichts, was du hineingetan hast.</p>
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr akzent" value="ja">Entfernen</button></div>`);
      if (r.a !== "ja") return;
      await api(`/api/anhaenge/${art}/${id}/${k}`, { method: "DELETE" });
      return anhNeuZeichnen(art, id);
    }
    if (e.target.closest("[data-anh-name]")) {
      const alt = zeile.querySelector(".anh-name").textContent;
      const r = await rueckfrage(`<h2>Anhang umbenennen</h2><input type="text" name="name" value="${esc(alt)}">
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Umbenennen</button></div>`);
      if (r.a !== "ja" || !r.name.trim() || r.name === alt) return;
      await api(`/api/anhaenge/${art}/${id}/${k}`, { method: "PATCH", body: { name: r.name } });
      return anhNeuZeichnen(art, id);
    }
  } catch (err) { toast(err.message); }
});

// Hineinziehen aus dem Dateimanager. Im Erfassen vor den anderen Zielen (Galerie, Drucke): eine Anhang-Liste ist nie zugleich etwas anderes.
const anhZiel = (e) => e.target.closest?.(".anh-ziel");
window.addEventListener("dragover", (e) => {
  const z = anhZiel(e);
  if (!z || ![...(e.dataTransfer?.types || [])].includes("Files")) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  z.classList.add("abwurf-ziel");
  e.dataTransfer.dropEffect = "copy";
}, true);
window.addEventListener("dragleave", (e) => { anhZiel(e)?.classList.remove("abwurf-ziel"); }, true);
window.addEventListener("drop", (e) => {
  const z = anhZiel(e);
  if (!z || !e.dataTransfer?.files?.length) return;
  e.preventDefault();
  e.stopImmediatePropagation();
  z.classList.remove("abwurf-ziel");
  anhaengeHochladen(z.dataset.anhArt, z.dataset.anhId, [...e.dataTransfer.files]);
}, true);

// ---------------------------------------------------------------- Notizen
//
// Markdown, gespeichert beim Verlassen des Feldes und eine Sekunde nach dem letzten Tippen. Die Vorschau setzt nur das Nötigste um
// (Überschriften, Listen, fett, kursiv, Code, Links) — aus maskiertem Text, damit nichts aus der Notiz als HTML wirkt.

function markdownHtml(text) {
  const inline = (s) => esc(s)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*]+)\*/g, "$1<i>$2</i>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
  const aus = [];
  let liste = null;
  for (const zeile of (text || "").split("\n")) {
    const h = zeile.match(/^(#{1,3})\s+(.*)/), li = zeile.match(/^\s*[-*]\s+(.*)/), nr = zeile.match(/^\s*\d+[.)]\s+(.*)/);
    if ((li || nr) && liste !== (li ? "ul" : "ol")) { if (liste) aus.push(`</${liste}>`); liste = li ? "ul" : "ol"; aus.push(`<${liste}>`); }
    if (!li && !nr && liste) { aus.push(`</${liste}>`); liste = null; }
    if (h) aus.push(`<h${h[1].length + 2}>${inline(h[2])}</h${h[1].length + 2}>`);
    else if (li || nr) aus.push(`<li>${inline((li || nr)[1])}</li>`);
    else if (zeile.trim()) aus.push(`<p>${inline(zeile)}</p>`);
  }
  if (liste) aus.push(`</${liste}>`);
  return aus.join("") || '<p class="dim">Noch keine Notizen.</p>';
}

const notizSpeichern = { zeit: null, laeuft: null };
async function notizJetztSpeichern(feld) {
  clearTimeout(notizSpeichern.zeit);
  const wert = feld.value, ziel = feld.dataset.notiz;
  if (feld.dataset.gespeichert === wert) return;
  const [art, id] = ziel.split(":");
  try {
    if (art === "modell") await api(`/api/modelle/${id}`, { method: "PATCH", body: { notiz: wert } });
    else await api(`/api/baugruppen/${id}`, { method: "PATCH", body: { notizen: wert } });
    feld.dataset.gespeichert = wert;
    const s = feld.parentElement.querySelector(".notiz-stand");
    if (s) s.textContent = "gespeichert";
  } catch (e) { toast(e.message); }
}
document.addEventListener("input", (e) => {
  const f = e.target.closest?.("[data-notiz]");
  if (!f) return;
  const s = f.parentElement.querySelector(".notiz-stand");
  if (s) s.textContent = "…";
  clearTimeout(notizSpeichern.zeit);
  notizSpeichern.zeit = setTimeout(() => notizJetztSpeichern(f), 1000);
});
document.addEventListener("focusout", (e) => { const f = e.target.closest?.("[data-notiz]"); if (f) notizJetztSpeichern(f); });
