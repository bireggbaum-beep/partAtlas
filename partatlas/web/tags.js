// Tags verwalten: alle Tags auf einen Blick, umbenennen, zusammenführen, löschen — und die automatischen gesammelt loswerden.
//
// Anlass (Capacities „Tag löschbar machen“, Bug, hoch): einmal angelegt, liess sich ein Tag nicht mehr loswerden; aus Dateinamen
// entstehen bei 9 000 Dateien tausende. Ein eigenes Fenster (nicht #dialog), damit Rückfragen darüber erscheinen können, ohne es zu
// ersetzen. Gelöschte Tags gehen in den Papierkorb und kommen nicht wieder automatisch (Sperrliste, unten im Fenster aufhebbar).

const tv = { daten: null, wahl: new Set(), filter: "", sort: "anzahl" };

async function tagsVerwalten(markiert) {
  let el = $("#tagverw");
  if (!el) {
    el = document.createElement("dialog");
    el.id = "tagverw";
    document.body.append(el);
    el.addEventListener("close", () => { ladeSeite(); neuLaden(); });
  }
  tv.wahl = new Set(markiert ? [markiert] : []);
  tv.filter = "";
  await tvLaden();
  if (!el.open) el.showModal();
  el.querySelector(".tv-suche")?.focus();
}

async function tvLaden() {
  try { tv.daten = await api("/api/tags/verwaltung"); } catch (e) { return toast(e.message); }
  const da = new Set(tv.daten.tags.map((t) => t.name));
  for (const n of [...tv.wahl]) if (!da.has(n)) tv.wahl.delete(n);
  tvZeichnen();
}

function tvZeilen() {
  const q = tags_norm(tv.filter);
  const l = tv.daten.tags.filter((t) => !q || t.name.includes(q));
  return tv.sort === "name" ? l.sort((a, b) => natuerlich(a.name, b.name)) : l;
}
const tags_norm = (s) => (s || "").trim().replace(/^#/, "").toLowerCase();

function tvZeichnen() {
  const el = $("#tagverw"), d = tv.daten;
  const zeilen = tvZeilen();
  const autoN = d.tags.filter((t) => t.auto).length;
  const n = tv.wahl.size;
  const kopf = el.querySelector(".tv-suche");
  const fokus = document.activeElement === kopf, pos = kopf?.selectionStart;
  el.innerHTML = `<div class="tv">
    <div class="tv-kopf"><h2>Tags verwalten</h2><span class="dim">${zahl(d.tags.length, 0)} Tags${autoN ? ` · ${zahl(autoN, 0)} davon ganz oder teilweise automatisch` : ""}</span>
      <button type="button" class="tv-zu" data-tv="zu" title="Schließen (Esc)">✕</button></div>
    <div class="tv-werkzeug">
      <input type="text" class="tv-suche" placeholder="Tag suchen …" value="${esc(tv.filter)}" autocomplete="off" spellcheck="false">
      <label class="tv-sort">Sortieren <select data-tv-sort><option value="anzahl" ${tv.sort === "anzahl" ? "selected" : ""}>nach Anzahl</option>
        <option value="name" ${tv.sort === "name" ? "selected" : ""}>nach Name</option></select></label>
    </div>
    <div class="tv-aktionen ${n ? "" : "ohne"}">
      <span>${n ? `${n} gewählt` : "Tags ankreuzen, um sie umzubenennen, zusammenzuführen oder zu löschen."}</span>
      ${n === 1 ? `<button type="button" class="knopf" data-tv="umbenennen">Umbenennen …</button>` : ""}
      ${n > 1 ? `<button type="button" class="knopf" data-tv="zusammen">Zusammenführen …</button>` : ""}
      ${n ? `<button type="button" class="knopf gefahr" data-tv="loeschen">Löschen …</button>` : ""}
    </div>
    <div class="tv-liste" role="table">
      <div class="tv-zeile tv-titelzeile" role="row"><input type="checkbox" data-tv-alle ${zeilen.length && zeilen.every((t) => tv.wahl.has(t.name)) ? "checked" : ""}
        title="Alle gezeigten wählen"><span>Tag</span><span class="zahl">Modelle</span><span class="zahl" title="Davon automatisch aus dem Dateinamen">automatisch</span><span></span></div>
      ${zeilen.map((t) => `<label class="tv-zeile ${tv.wahl.has(t.name) ? "gewaehlt" : ""}" role="row">
        <input type="checkbox" data-tv-wahl="${esc(t.name)}" ${tv.wahl.has(t.name) ? "checked" : ""}>
        <span class="tv-name">#${esc(t.name)}</span><span class="zahl">${t.anzahl ? zahl(t.anzahl, 0) : '<span class="dim">–</span>'}</span>
        <span class="zahl dim">${t.auto ? zahl(t.auto, 0) : ""}</span>
        <button type="button" class="knopf-text" data-tv-zeigen="${esc(t.name)}" title="Modelle mit diesem Tag zeigen" ${t.anzahl ? "" : "disabled"}>Zeigen</button></label>`).join("")
        || `<p class="dim tv-leer">${d.tags.length ? "Kein Tag passt zur Suche." : "Noch keine Tags."}</p>`}
    </div>
    <div class="tv-fuss">
      <div class="tv-block"><b>Automatische Tags</b>
        <p class="dim">${d.auto_tags ? "partAtlas schlägt beim Einlesen Tags aus dem Dateinamen vor (Einstellungen › Einlesen)." : "Tags aus dem Dateinamen sind ausgeschaltet (Einstellungen › Einlesen)."}
          Alle automatisch angehängten entfernen: von Hand gesetzte bleiben, vorher wird gesichert.</p>
        <button type="button" class="knopf" data-tv="auto" ${autoN ? "" : "disabled"}>Alle automatischen entfernen …</button></div>
      ${d.gesperrt.length ? `<div class="tv-block"><b>Nicht mehr vorgeschlagen</b>
        <p class="dim">Diese Wörter werden beim Einlesen nicht mehr zu Tags — weil du sie gelöscht oder zusammengeführt hast. Ein Klick nimmt das zurück.</p>
        <div class="tv-gesperrt">${d.gesperrt.map((g) => `<button type="button" class="chip" data-tv-frei="${esc(g)}" title="Wieder vorschlagen">${esc(g)} ×</button>`).join("")}</div></div>` : ""}
    </div></div>`;
  const neu = el.querySelector(".tv-suche");
  if (fokus) { neu.focus(); neu.setSelectionRange(pos, pos); }
}

// Rückfrage über dem Fenster: ein zweites, kleines <dialog> — #dialog würde den Inhalt des Einstellungsdialogs o. ä. ersetzen.
function rueckfrage(html) {
  const d = document.createElement("dialog");
  d.className = "tv-frage";
  d.innerHTML = `<form method="dialog">${html}</form>`;
  document.body.append(d);
  d.showModal();
  d.querySelector("input[type=text]")?.select();
  d.querySelector("form").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.matches("input[type=text]")) { e.preventDefault(); d.querySelector(".akzent")?.click(); }
  });
  return new Promise((ok) => d.addEventListener("close", () => {
    const werte = Object.fromEntries([...d.querySelectorAll("input")].filter((i) => i.type !== "radio" || i.checked)
      .map((i) => [i.name, i.type === "checkbox" ? i.checked : i.value]));
    d.remove();
    ok({ a: d.returnValue, ...werte });
  }, { once: true }));
}

async function tvAktion(was) {
  const namen = [...tv.wahl];
  const anzahl = (n) => tv.daten.tags.find((t) => t.name === n)?.anzahl || 0;
  try {
    if (was === "umbenennen" || was === "zusammen") {
      // Vorschlag als Ziel: der meistgenutzte der gewählten — er bleibt, die anderen gehen in ihm auf.
      const vorschlag = [...namen].sort((a, b) => anzahl(b) - anzahl(a))[0];
      const r = await rueckfrage(was === "umbenennen"
        ? `<h2>Tag umbenennen</h2><p class="dim">#${esc(namen[0])} an ${anzahl(namen[0])} ${anzahl(namen[0]) === 1 ? "Modell" : "Modellen"}. Gibt es den neuen Namen schon, werden beide zusammengeführt.</p>
           <input type="text" name="ziel" value="${esc(namen[0])}" aria-label="Neuer Name">
           <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Umbenennen</button></div>`
        : `<h2>${namen.length} Tags zusammenführen</h2><p class="dim">${namen.map((n) => `#${esc(n)}`).join(", ")} werden zu einem Tag. Jedes Modell, das einen davon hat, bekommt den neuen.</p>
           <label>Name <input type="text" name="ziel" value="${esc(vorschlag)}"></label>
           <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Zusammenführen</button></div>`);
      if (r.a !== "ja" || !tags_norm(r.ziel)) return;
      const erg = await api("/api/tags/zusammenfuehren", { method: "POST", body: { quellen: namen, ziel: r.ziel } });
      tv.wahl = new Set([erg.ziel]);
      toast(was === "umbenennen" ? `Umbenannt in #${erg.ziel}.` : `Zusammengeführt zu #${erg.ziel} (${erg.modelle} Zuordnungen).`);
    } else if (was === "loeschen") {
      const modelle = namen.reduce((s, n) => s + anzahl(n), 0);
      const r = await rueckfrage(`<h2>${namen.length === 1 ? `Tag #${esc(namen[0])}` : `${namen.length} Tags`} löschen?</h2>
        <p>${modelle ? `Wird von ${zahl(modelle, 0)} ${modelle === 1 ? "Zuordnung" : "Zuordnungen"} an Modellen entfernt. ` : ""}Die Modelle selbst bleiben.
          ${namen.length === 1 ? "Der Tag liegt danach" : "Die Tags liegen danach"} im Papierkorb und lassen sich mit allen Zuordnungen zurückholen.</p>
        <label><input type="checkbox" name="sperren" checked> Nicht mehr automatisch aus Dateinamen vorschlagen</label>
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr akzent" value="ja">Löschen</button></div>`);
      if (r.a !== "ja") return;
      await api("/api/tags/loeschen", { method: "POST", body: { namen, sperren: r.sperren } });
      for (const n of namen) zustand.tags.delete(n);
      tv.wahl.clear();
      toast(namen.length === 1 ? `#${namen[0]} gelöscht.` : `${namen.length} Tags gelöscht.`);
    } else if (was === "auto") {
      const n = await api("/api/tags/auto_entfernen", { method: "POST", body: { nur_zaehlen: true } });
      const r = await rueckfrage(`<h2>Alle automatischen Tags entfernen?</h2>
        <p>${zahl(n.kanten, 0)} automatisch angehängte ${n.kanten === 1 ? "Zuordnung" : "Zuordnungen"} (${zahl(n.tags, 0)} Tags) werden von den Modellen gelöst.
          Tags, die du selbst gesetzt hast, bleiben. Was danach an keinem Modell mehr hängt, geht in den Papierkorb.</p>
        <p class="dim">Vorher sichert partAtlas die Datenbank; zurückholen über Einstellungen › Sicherungen.</p>
        <label><input type="checkbox" name="abschalten" checked> Auch künftig keine Tags aus Dateinamen</label>
        <div class="knoepfe"><button class="knopf" value="nein">Abbrechen</button><button class="knopf gefahr akzent" value="ja">Entfernen</button></div>`);
      if (r.a !== "ja") return;
      const erg = await api("/api/tags/auto_entfernen", { method: "POST", body: { abschalten: r.abschalten } });
      zustand.tags.clear();
      tv.wahl.clear();
      toast(`${zahl(erg.kanten, 0)} automatische Zuordnungen entfernt.`);
    }
  } catch (e) { return toast(e.message); }
  await tvLaden();
}

document.addEventListener("click", async (e) => {
  if (!e.target.closest?.("#tagverw")) {
    if (e.target.closest?.("[data-tags-verwalten]")) tagsVerwalten();
    return;
  }
  const b = e.target.closest("[data-tv]");
  if (b) {
    if (b.dataset.tv === "zu") return $("#tagverw").close();
    return tvAktion(b.dataset.tv);
  }
  const zeigen = e.target.closest("[data-tv-zeigen]");
  if (zeigen) {
    e.preventDefault();
    $("#tagverw").close();
    return navigiere(() => { Object.assign(zustand, { tags: new Set([zeigen.dataset.tvZeigen]), material: new Set(), format: "", ansicht: "alle", ordner: "", sammlung: "" }); return neuLaden(); });
  }
  const frei = e.target.closest("[data-tv-frei]");
  if (frei) {
    try { tv.daten = await api("/api/tags/sperre_aufheben", { method: "POST", body: { namen: [frei.dataset.tvFrei] } }); tvZeichnen(); }
    catch (err) { toast(err.message); }
  }
});
document.addEventListener("change", (e) => {
  if (!e.target.closest?.("#tagverw")) return;
  const w = e.target.dataset.tvWahl;
  if (w != null) { e.target.checked ? tv.wahl.add(w) : tv.wahl.delete(w); return tvZeichnen(); }
  if (e.target.matches("[data-tv-alle]")) {
    for (const t of tvZeilen()) e.target.checked ? tv.wahl.add(t.name) : tv.wahl.delete(t.name);
    return tvZeichnen();
  }
  if (e.target.matches("[data-tv-sort]")) { tv.sort = e.target.value; tvZeichnen(); }
});
document.addEventListener("input", (e) => {
  if (!e.target.matches?.("#tagverw .tv-suche")) return;
  tv.filter = e.target.value;
  tvZeichnen();
});

// Rechtsklick auf einen Tag in der Seitenleiste: dieselben Aktionen für diesen einen.
document.addEventListener("contextmenu", (e) => {
  const t = e.target.closest?.("#tag-liste [data-tag]");
  if (!t) return;
  e.preventDefault();
  const menu = $("#kontext");
  menu.innerHTML = `<button type="button" data-km="tag-umbenennen">Umbenennen …</button>
    <button type="button" data-km="tag-verwalten">Tags verwalten …</button><hr>
    <button type="button" data-km="tag-loeschen" class="gefahr">Löschen …</button>`;
  kontextMenu.ziel = { tag: t.dataset.tag };
  menu.hidden = false;
  const r = menu.getBoundingClientRect();
  menu.style.left = Math.min(e.clientX, innerWidth - r.width - 6) + "px";
  menu.style.top = Math.min(e.clientY, innerHeight - r.height - 6) + "px";
});

async function tagKontext(k) {
  const tag = kontextMenu.ziel.tag;
  await tagsVerwalten(tag);
  if (k === "tag-umbenennen") tvAktion("umbenennen");
  if (k === "tag-loeschen") tvAktion("loeschen");
}
