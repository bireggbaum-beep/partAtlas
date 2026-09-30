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

export function webglMoeglich() {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch { return false; }
}

export function schliessen() {
  if (!aktiv) return;
  cancelAnimationFrame(aktiv.rahmen);
  aktiv.beobachter.disconnect();
  aktiv.steuerung.dispose();
  aktiv.geometrie.dispose();
  aktiv.material.dispose();
  aktiv.renderer.dispose();
  aktiv.renderer.forceContextLoss();
  aktiv.renderer.domElement.remove();
  aktiv = null;
}

// `puffer`: ArrayBuffer mit float32, 9 Werte je Dreieck (Z nach oben, wie
// auf dem Druckbett). `farbe`: '#RRGGBB' aus dem Slicer oder null.
export function zeige(behaelter, puffer, farbe) {
  schliessen();
  const breite = behaelter.clientWidth, hoehe = behaelter.clientHeight;
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
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
  });
  beobachter.observe(behaelter);

  aktiv = { renderer, steuerung, geometrie, material, beobachter, rahmen: 0 };
  const schleife = () => {
    aktiv.rahmen = requestAnimationFrame(schleife);
    steuerung.update();
    renderer.render(szene, kamera);
  };
  schleife();

  return {
    zuruecksetzen() {
      kamera.position.copy(start);
      steuerung.target.copy(ziel);
      steuerung.autoRotate = true;
    },
    drehen(an) { steuerung.autoRotate = an; },
  };
}
