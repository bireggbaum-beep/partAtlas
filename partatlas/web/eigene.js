// EIGENE: Eigene Komponenten in der Baugruppe — Auswahl, Neuanlage mit Bild, Bearbeiten.
// Ein Teil, das weder gedruckt noch gekauft ist (60 Jahre altes Kugellager, selbst Gefrästes). Keine Bestandsverwaltung: die Menge ist der Bedarf.
// Entfernen: diese Datei, die Markierungen „EIGENE“ in baugruppen.js/index.html und das Gegenstück in partatlas/eigene.py.

function eigeneFormular(w = {}, arten = []) {
  return `<div class="eig-form">
    <div class="eig-bild" id="eig-bild" title="Bild wählen oder hier einfügen (Strg+V)">${w.bild ? `<img src="/api/eigene/${esc(w.id)}/bild?t=1" alt="">` : "<span>Bild</span>"}</div>
    <div class="eig-felder">
      <input type="text" id="eig-name" placeholder="Name, z. B. Kugellager 6203 (alt)" value="${esc(w.name || "")}" maxlength="120">
      <input type="text" id="eig-art" list="eig-arten" placeholder="Art (frei): Lagerteil, Eigenbau …" value="${esc(w.art || "")}" maxlength="40">
      <datalist id="eig-arten">${arten.map((a) => `<option value="${esc(a)}">`).join("")}</datalist>
      <input type="text" id="eig-masse" placeholder="Maße (optional), z. B. 40×17×12" value="${esc(w.masse || "")}" maxlength="60">
      <textarea id="eig-notiz" data-enter="" rows="2" placeholder="Notiz (optional)" maxlength="500">${esc(w.notiz || "")}</textarea>
      <div class="eig-datei"><button type="button" class="knopf" id="eig-datei-knopf">＋ Datei hinzufügen</button>
        <span class="dim" id="eig-datei-name">${w.datei ? `<a href="/api/eigene/${esc(w.id)}/datei">${esc(w.datei)}</a>` : "FCStd, STEP, 3MF, STL oder OBJ — oder hierher ziehen. Nur für Bild und zum Öffnen, nicht im 3D-Katalog."}</span></div>
    </div>
    <input type="file" id="eig-cad" accept=".fcstd,.step,.stp,.3mf,.stl,.obj" hidden>
    <input type="file" id="eig-datei" accept="image/png,image/jpeg,image/webp" hidden>
  </div>`;
}

// Das gewählte Bild bleibt im Browser, bis gespeichert wird; Vorschau sofort.
function eigeneBildWahl(d) {
  const st = { datei: null, cad: null };
  const kachel = d.querySelector("#eig-bild");
  const nimm = (f) => {
    if (!f || !/^image\/(png|jpeg|webp)$/.test(f.type)) return f && toast("Nur PNG, JPG oder WebP.");
    st.datei = f;
    kachel.innerHTML = `<img src="${URL.createObjectURL(f)}" alt="">`;
  };
  kachel.addEventListener("click", () => d.querySelector("#eig-datei").click());
  d.querySelector("#eig-datei").addEventListener("change", (e) => nimm(e.target.files[0]));
  d.addEventListener("paste", (e) => nimm([...(e.clipboardData?.files || [])][0]));
  // Konstruktionsdatei: Knopf oder auf den Dialog ziehen; ein Bild darauf ist das Bild, alles andere die Datei.
  const cad = (f) => {
    if (!f) return;
    if (/^image\//.test(f.type)) return nimm(f);
    st.cad = f;
    d.querySelector("#eig-datei-name").textContent = `${f.name} — wird beim Speichern eingelesen`;
  };
  d.querySelector("#eig-datei-knopf").addEventListener("click", () => d.querySelector("#eig-cad").click());
  d.querySelector("#eig-cad").addEventListener("change", (e) => cad(e.target.files[0]));
  d.addEventListener("dragover", (e) => e.preventDefault());
  d.addEventListener("drop", (e) => { e.preventDefault(); cad(e.dataTransfer.files[0]); });
  return st;
}

const eigeneWerte = (d) => ({ name: d.querySelector("#eig-name").value.trim(), art: d.querySelector("#eig-art").value.trim(),
  masse: d.querySelector("#eig-masse").value.trim(), notiz: d.querySelector("#eig-notiz").value.trim() });

// Die Datei zuerst: aus ihr kann das Bild entstehen; ein selbst gewähltes Bild kommt danach und gewinnt.
async function eigeneDateiSenden(id, datei) {
  if (!datei) return;
  toast("Datei wird eingelesen …");
  const r = await fetch(`/api/eigene/${id}/datei?name=${encodeURIComponent(datei.name)}`, { method: "POST", body: datei });
  const antwort = await r.json().catch(() => ({}));
  if (!r.ok) return toast(antwort.fehler || "Datei nicht eingelesen.");
  toast(antwort.bild_neu ? "Datei eingelesen, Bild erzeugt." : "Datei gespeichert — daraus ließ sich kein Bild erzeugen.");
}

async function eigeneBildSenden(id, datei) {
  if (!datei) return;
  const r = await fetch(`/api/eigene/${id}/bild`, { method: "POST", body: datei });
  if (!r.ok) toast((await r.json().catch(() => ({}))).fehler || "Bild nicht gespeichert.");
}

async function eigeneWaehlen() {
  const d = $("#dialog");
  d.classList.add("breit");
  const arten = await api("/api/eigene/arten").catch(() => []);
  const warten = dialog(`<h2>Eigene Komponente hinzufügen</h2>
    <p class="dim">Teile, die du weder druckst noch kaufst: Lagerfunde, Selbstgebautes. Die Menge ist, was du brauchst — kein Lagerbestand.</p>
    <input type="text" id="w-suche" data-enter="" placeholder="Vorhandene suchen …" autocomplete="off">
    <div class="waehler" id="w-liste"></div>
    <div class="i-titel">NEU ANLEGEN</div>
    ${eigeneFormular({}, arten)}
    <div class="knoepfe"><button class="knopf" value="fertig">Fertig</button><button type="button" class="knopf akzent" id="eig-anlegen">Anlegen und hinzufügen</button></div>`);
  const bild = eigeneBildWahl(d);
  const laden = async () => {
    const liste = await api(`/api/eigene?q=${encodeURIComponent($("#w-suche").value.trim())}`);
    const drin = new Set((bgDaten?.positionen || []).map((p) => p.ref));
    $("#w-liste").innerHTML = liste.map((e) => { const ref = `CUSTOM_COMPONENT/${e.id}`; return `<div class="w-zeile">
      ${e.bild ? `<img loading="lazy" src="/api/eigene/${esc(e.id)}/bild?t=1" alt="">` : `<div class="mini" style="display:grid;place-items:center">🔩</div>`}
      <div><b>${esc(e.name)}</b><small>${esc([e.art, e.masse].filter(Boolean).join(" · "))}</small></div>
      <input type="number" min="1" value="1" data-w-menge="${esc(ref)}">
      <button type="button" class="plus ${drin.has(ref) ? "ok" : ""}" data-w-plus="${esc(ref)}" title="${drin.has(ref) ? "ist drin — Klick nimmt es wieder heraus" : "hinzufügen"}"><span class="a">${drin.has(ref) ? "✓" : "＋"}</span><span class="b">−</span></button></div>`; }).join("")
      || '<div class="pos-leer">Noch keine eigene Komponente — unten die erste anlegen.</div>';
  };
  let zeit;
  $("#w-suche").addEventListener("input", () => { clearTimeout(zeit); zeit = setTimeout(laden, 150); });
  // Hinzufügen/Herausnehmen wie in der Kaufteile-Auswahl.
  $("#w-liste").addEventListener("click", async (e) => {
    const plus = e.target.closest("[data-w-plus]");
    if (!plus || plus.disabled) return;
    const ref = plus.dataset.wPlus, drin = plus.classList.contains("ok");
    const menge = Number(document.querySelector(`[data-w-menge="${CSS.escape(ref)}"]`)?.value || 1);
    plus.disabled = true;
    try {
      if (drin) await api(`/api/baugruppen/${bid()}/positionen?ref=${encodeURIComponent(ref)}`, { method: "DELETE" });
      else await api(`/api/baugruppen/${bid()}/positionen`, { method: "POST", body: { ref, menge } });
      await ladeBaugruppe();
      await laden();
    } catch (err) { toast(err.message); plus.disabled = false; }
  });
  $("#eig-anlegen").addEventListener("click", async () => {
    const werte = eigeneWerte(d);
    if (!werte.name) return toast("Der Name fehlt.");
    try {
      const { id } = await api("/api/eigene", { method: "POST", body: werte });
      await eigeneDateiSenden(id, bild.cad);
      await eigeneBildSenden(id, bild.datei);
      await api(`/api/baugruppen/${bid()}/positionen`, { method: "POST", body: { ref: `CUSTOM_COMPONENT/${id}`, menge: 1 } });
      d.close("fertig");
      ladeBaugruppe();
      toast(`„${werte.name}“ ist in der Baugruppe.`);
    } catch (err) { toast(err.message); }
  });
  await laden();
  $("#w-suche").focus();
  await warten;
  d.classList.remove("breit");
}

async function eigeneBearbeiten(id) {
  const [w, arten] = await Promise.all([api(`/api/eigene/${id}`), api("/api/eigene/arten").catch(() => [])]);
  const wo = w.verwendet_in.length ? `Steckt in: ${w.verwendet_in.map(esc).join(", ")}.` : "Steckt in keiner Baugruppe.";
  const dlg = dialog(`<h2>Eigene Komponente</h2>${eigeneFormular(w, arten)}
    <p class="dim">${wo} Änderungen gelten überall, wo sie vorkommt.</p>
    <div class="knoepfe"><button type="button" class="knopf gefahr" id="eig-weg">Komponente löschen</button><span class="bg-luecke"></span>
      <button class="knopf" value="nein">Abbrechen</button><button class="knopf akzent" value="ja">Speichern</button></div>`);
  const d = $("#dialog");
  const bild = eigeneBildWahl(d);
  $("#eig-weg").addEventListener("click", async () => {
    try { await api(`/api/eigene/${id}`, { method: "DELETE" }); d.close("nein"); ladeBaugruppe(); toast("Komponente gelöscht."); }
    catch (err) { toast(err.message); }      // „Steckt noch in …“
  });
  if ((await dlg) !== "ja") return;
  try {
    await api(`/api/eigene/${id}`, { method: "PATCH", body: eigeneWerte(d) });
    await eigeneDateiSenden(id, bild.cad);
    await eigeneBildSenden(id, bild.datei);
  } catch (err) { toast(err.message); }
  ladeBaugruppe();
}

document.addEventListener("click", (e) => {
  const z = e.target.closest?.("[data-bg-eigen]");
  if (z && !e.target.closest("button, .stepper")) eigeneBearbeiten(z.dataset.bgEigen);
});
