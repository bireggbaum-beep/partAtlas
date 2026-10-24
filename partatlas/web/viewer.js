// 3D-Ansicht im Inspektor: drehen mit der Maus, zoomen mit dem Rad,
// verschieben mit rechts. three.js liegt unter /web/vendor (r170, MIT),
// ausgeliefert vom eigenen Server — kein CDN, läuft ohne Internet.
//
// Es gibt immer nur eine Ansicht. Browser erlauben nur wenige WebGL-
// Kontexte; wer bei jedem Klick einen neuen anlegt und den alten nicht
// freigibt, bekommt nach ein paar Dutzend Modellen schwarze Flächen.
import * as THREE from "three";
import { OrbitControls } from "/web/vendor/OrbitControls.js";

let aktiv = null;
// Einmal abgebrochen, bleibt es für diese Seite aus: alte Treiber (nouveau
// auf einer GeForce 9, Tester) zeigen ein Bild und verlieren dann den
// Kontext — jeder neue Versuch flackert nur und kann den Browser hängen.
let abgebrochen = false;

// three.js ab r163 kann nur noch WebGL 2; reines WebGL 1 reicht nicht.
export function webglMoeglich() {
  if (abgebrochen) return false;
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch { return false; }
}

// Zeichnet WebGL über den Prozessor (llvmpipe, SwiftShader, „Software“)? Dann kostet jedes Bild ein Vielfaches, und Kantenglättung
// vervielfacht es noch einmal.
let softwareGl = null;
function laeuftAufProzessor() {
  if (softwareGl !== null) return softwareGl;
  try {
    const gl = document.createElement("canvas").getContext("webgl2");
    const info = gl && gl.getExtension("WEBGL_debug_renderer_info");
    const name = info ? String(gl.getParameter(info.UNMASKED_RENDERER_WEBGL)) : "";
    softwareGl = /llvmpipe|swiftshader|software|softpipe/i.test(name);
  } catch { softwareGl = false; }
  return softwareGl;
}

// Ab so vielen Dreiecken wird nicht mehr geglättet, auch auf einer Grafikkarte.
const GLAETTEN_BIS_DREIECKE = 100000;
// Dauert ein Bild beim Bewegen länger, sinkt die Auflösung (nie unter MIN_FAKTOR); steht die Ansicht still, kommt ein scharfes Bild.
const LANGSAM_MS = 90;
const MIN_FAKTOR = 0.4;
const SCHARF_NACH_MS = 250;

export function schliessen() {
  if (!aktiv) return;
  cancelAnimationFrame(aktiv.rahmen);
  clearTimeout(aktiv.scharf);
  aktiv.beobachter.disconnect();
  aktiv.steuerung.dispose();
  aktiv.geometrie.dispose();
  aktiv.material.dispose();
  aktiv.renderer.dispose();
  // Das eigene Freigeben ist kein Abbruch.
  aktiv.renderer.domElement.removeEventListener("webglcontextlost", aktiv.verloren);
  aktiv.renderer.forceContextLoss();
  aktiv.renderer.domElement.remove();
  aktiv = null;
}

// `puffer`: ArrayBuffer mit float32, 9 Werte je Dreieck (Z nach oben, wie
// auf dem Druckbett). `farbe`: '#RRGGBB' aus dem Slicer oder null.
// `beiAbbruch`: wird gerufen, wenn WebGL nach dem Start wegbricht.
export function zeige(behaelter, puffer, farbe, beiAbbruch = () => {}) {
  schliessen();
  const breite = behaelter.clientWidth, hoehe = behaelter.clientHeight;
  let renderer;
  try {
    const glaetten = puffer.byteLength / 36 <= GLAETTEN_BIS_DREIECKE && !laeuftAufProzessor();   // 9 Werte je Dreieck, je 4 Byte
    renderer = new THREE.WebGLRenderer({ antialias: glaetten, alpha: true });
  } catch (e) {
    abgebrochen = true;
    throw e;
  }
  const basis = Math.min(window.devicePixelRatio, 2);
  let faktor = 1;                                  // 1 = volle Auflösung; kleiner, solange das Bewegen zu langsam ist
  renderer.setPixelRatio(basis);
  renderer.setSize(breite, hoehe);
  behaelter.appendChild(renderer.domElement);

  const szene = new THREE.Scene();
  szene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.6));
  const sonne = new THREE.DirectionalLight(0xffffff, 1.8);
  sonne.position.set(1, 2, 1.5);
  szene.add(sonne);

  const geometrie = new THREE.BufferGeometry();
  geometrie.setAttribute("position", new THREE.BufferAttribute(new Float32Array(puffer), 3));
  geometrie.rotateX(-Math.PI / 2);            // Z oben (Druck) → Y oben (three.js)
  geometrie.computeBoundingBox();
  const kiste = geometrie.boundingBox;
  const mitte = new THREE.Vector3();
  kiste.getCenter(mitte);
  geometrie.translate(-mitte.x, -kiste.min.y, -mitte.z);   // auf das Bett stellen
  geometrie.computeVertexNormals();
  geometrie.computeBoundingSphere();

  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(farbe && /^#[0-9a-f]{6}/i.test(farbe) ? farbe.slice(0, 7) : "#e87a5c"),
    roughness: 0.55, metalness: 0.05, flatShading: true, side: THREE.DoubleSide,
  });
  szene.add(new THREE.Mesh(geometrie, material));

  const r = geometrie.boundingSphere.radius || 1;
  const raster = new THREE.GridHelper(r * 3, 12, 0x888888, 0x555555);
  raster.material.opacity = 0.35;
  raster.material.transparent = true;
  szene.add(raster);

  const kamera = new THREE.PerspectiveCamera(35, breite / hoehe, r / 100, r * 100);
  const ziel = new THREE.Vector3(0, geometrie.boundingSphere.center.y, 0);
  const start = new THREE.Vector3(r * 2.6, r * 1.9 + ziel.y, r * 2.6);   // ganz im Bild bei 35°
  kamera.position.copy(start);
  const steuerung = new OrbitControls(kamera, renderer.domElement);
  steuerung.target.copy(ziel);
  steuerung.enableDamping = true;
  steuerung.autoRotate = true;
  steuerung.autoRotateSpeed = 1.5;
  // Wer selbst dreht, will nicht, dass es weiterdreht.
  steuerung.addEventListener("start", () => { steuerung.autoRotate = false; });
  steuerung.update();

  const beobachter = new ResizeObserver(() => {
    const b = behaelter.clientWidth, h = behaelter.clientHeight;
    if (!b || !h) return;
    renderer.setSize(b, h);
    kamera.aspect = b / h;
    kamera.updateProjectionMatrix();
    planen();
  });
  beobachter.observe(behaelter);

  const verloren = (e) => {
    e.preventDefault();
    abgebrochen = true;
    schliessen();
    beiAbbruch();
  };
  renderer.domElement.addEventListener("webglcontextlost", verloren);
  aktiv = { renderer, steuerung, geometrie, material, beobachter, verloren, rahmen: 0, scharf: 0 };

  // Gezeichnet wird nur, wenn sich etwas ändert (Drehen, Trägheit, Zoom, automatisches Drehen), nicht in einer Dauerschleife:
  // eine ruhende Ansicht kostet nichts. OrbitControls meldet jede Änderung der Kamera mit „change“.
  let geplant = false, letzte = 0, gleitend = 0, seitWechsel = 0;
  const einstellen = (f) => {
    faktor = f;
    renderer.setPixelRatio(basis * f);
  };
  const planen = () => {
    if (geplant || !aktiv) return;
    geplant = true;
    aktiv.rahmen = requestAnimationFrame(zeichnen);
  };
  const zeichnen = (t) => {
    geplant = false;
    clearTimeout(aktiv.scharf);
    // Die Zeit zwischen zwei Bildern in Folge misst, wie schwer die Ansicht dem Rechner fällt.
    const dt = letzte ? t - letzte : 0;
    letzte = t;
    if (dt > 0 && dt < 2000) {
      gleitend = gleitend ? gleitend * 0.6 + dt * 0.4 : dt;
      seitWechsel++;
      if (gleitend > LANGSAM_MS && faktor > MIN_FAKTOR && seitWechsel >= 3) {
        einstellen(Math.max(MIN_FAKTOR, faktor * 0.75));
        gleitend = 0;
        seitWechsel = 0;
      }
    }
    steuerung.update();
    renderer.render(szene, kamera);
    // Bleibt nichts mehr zu tun, kommt (nach einer kurzen Pause) ein Bild in voller Auflösung.
    aktiv.scharf = setTimeout(() => {
      if (geplant) return;
      letzte = 0;
      gleitend = 0;
      if (faktor < 1) {
        einstellen(1);
        renderer.render(szene, kamera);
      }
    }, SCHARF_NACH_MS);
  };
  steuerung.addEventListener("change", planen);
  planen();

  return {
    zuruecksetzen() {
      kamera.position.copy(start);
      steuerung.target.copy(ziel);
      steuerung.autoRotate = true;
      planen();
    },
    drehen(an) { steuerung.autoRotate = an; planen(); },
    qualitaet() { return faktor; },
    // Die Ansicht, wie sie gerade steht, als PNG — ohne das Raster am Boden. Gleich nach dem Zeichnen gelesen: ohne
    // preserveDrawingBuffer ist der Puffer nur bis zum nächsten Bild gültig.
    bild() {
      raster.visible = false;
      if (faktor < 1) renderer.setPixelRatio(basis);      // das gespeicherte Bild immer in voller Auflösung
      renderer.render(szene, kamera);
      const url = renderer.domElement.toDataURL("image/png");
      if (faktor < 1) renderer.setPixelRatio(basis * faktor);
      raster.visible = true;
      return url;
    },
  };
}
