/* Interactive 3D temperature viewer for Design9795_site/viewer3d.html.
   Data: assets/viewer/manifest.js (VIEWER_MANIFEST) + geom_<model>.js / temp_<lp>_<model>.js written by scripts/export_viewer.py.
   Each data file calls VIEWER.got(name, base64) so the page works from file:// as well as http. */
(function () {
  "use strict";
  const MAN = (window.VIEWER_MANIFEST || { entries: {} }).entries;
  const ALL = [["housing", "Housing"], ["stator", "Stator"], ["winding", "Winding / coil"], ["busbar", "Busbar"], ["strap", "Strap"], ["tbar", "T-bar"],
    ["resin", "Resin"], ["bobbin", "Bobbin"], ["rotor", "Rotor"], ["magnets", "Magnets"], ["shaft", "Shaft"], ["bearings", "Bearings"]];
  const ROTOR = ["rotor", "magnets", "shaft", "bearings"];
  const EXPLODE = { housing: 0, stator: 0.9, winding: 1.5, resin: 1.25, bobbin: 1.35, busbar: 1.75, strap: 1.65, tbar: 1.85, rotor: -1.0, magnets: -1.4, shaft: -1.9, bearings: -2.4 };
  const pending = {}, blobs = {};
  window.VIEWER = {
    got(name, b64) {
      const s = atob(b64), u = new Uint8Array(s.length);
      for (let i = 0; i < s.length; i++) u[i] = s.charCodeAt(i);
      blobs[name] = u.buffer;
      (pending[name] || []).forEach(f => f(u.buffer)); delete pending[name];
    }
  };
  function load(name) {
    if (blobs[name]) return Promise.resolve(blobs[name]);
    return new Promise((res, rej) => {
      if (!pending[name]) {
        pending[name] = [];
        const sc = document.createElement("script"); sc.src = "assets/viewer/" + name + ".js";
        sc.onerror = () => rej(new Error("missing " + name)); document.head.appendChild(sc);
      }
      pending[name].push(res);
    });
  }
  function turbo(x) {
    x = Math.min(1, Math.max(0, x));
    return [0.13572138 + x * (4.6153926 + x * (-42.66032258 + x * (132.13108234 + x * (-152.94239396 + x * 59.28637943)))),
      0.09140261 + x * (2.19418839 + x * (4.84296658 + x * (-14.18503333 + x * (4.27729857 + x * 2.82956604)))),
      0.1066733 + x * (12.64194608 + x * (-60.58204836 + x * (110.36276771 + x * (-89.90310912 + x * 27.34824973))))].map(v => Math.min(1, Math.max(0, v)));
  }
  const mmss = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
  function interp(grid, ys, t) {
    if (!ys) return null;
    const dt = grid[1] - grid[0], i = Math.min(grid.length - 2, Math.max(0, Math.floor(t / dt))), f = Math.min(1, Math.max(0, (t - grid[i]) / dt));
    return ys[i] + f * (ys[i + 1] - ys[i]);
  }

  // ---------------------------------------------------------------- UI
  const root = document.getElementById("v3d");
  if (!root) return;
  const lps = [...new Set(Object.keys(MAN).map(k => k.split("/")[0]))].sort();
  if (!lps.length) { root.innerHTML = '<p class="todo">No viewer data yet: run scripts/export_viewer.py.</p>'; return; }
  root.innerHTML = `<div class="v3d-ctl">
   <label>Load point <select id="v-lp">${lps.map(l => `<option value="${l}">${l}: ${MAN[l + "/baseline"] ? MAN[l + "/baseline"].name : MAN[l + "/detailed"].name}</option>`).join("")}</select></label>
   <span class="v-seg">Model <label><input type="radio" name="v-model" value="detailed" checked> Detailed (real coils)</label><label><input type="radio" name="v-model" value="baseline"> Baseline</label></span>
   <div class="v-parts">${ALL.map(([k, l]) => `<label><input type="checkbox" data-part="${k}" checked> ${l}</label>`).join("")}
    <button id="v-rotor" type="button">Rotor group only</button><button id="v-all" type="button">All</button></div>
   <div class="v-row"><button id="v-play" type="button">▶ Play</button>
    <input id="v-time" type="range" min="0" max="1" step="1" value="0"><span id="v-tlab"></span>
    <label>Speed <select id="v-speed"><option value="15">15×</option><option value="60" selected>60×</option><option value="180">180×</option><option value="600">600×</option></select></label></div>
   <div class="v-row"><label>Colour range <select id="v-range"><option value="fixed">fixed per load point</option><option value="auto">auto (visible parts, this time)</option></select></label>
    <label>Axial cut <input id="v-cz" type="range" min="0" max="1000" value="1000"></label>
    <label>Radial cut <input id="v-cx" type="range" min="0" max="1000" value="500"></label>
    <label>Explode <input id="v-ex" type="range" min="0" max="1000" value="0"></label></div></div>
  <div class="v3d-main"><div class="v3d-canvas" id="v-canvas"><div id="v-probe"></div><canvas id="v-bar" width="70" height="260"></canvas></div>
   <div class="v3d-side"><div id="v-note" class="note"></div><table id="v-read"></table></div></div>`;
  const $ = id => document.getElementById(id), Q0 = new URLSearchParams(location.search);

  // ---------------------------------------------------------------- three.js scene
  const box = $("v-canvas");
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); renderer.localClippingEnabled = true;
  renderer.setClearColor(0xf4f5f7); box.prepend(renderer.domElement);
  const scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(35, 1, 0.001, 10);
  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const sun = new THREE.DirectionalLight(0xffffff, 0.6); camera.add(sun); sun.position.set(0.3, 0.5, 1); scene.add(camera);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  const planes = [new THREE.Plane(new THREE.Vector3(0, 0, -1), 1), new THREE.Plane(new THREE.Vector3(-1, 0, 0), 1)];
  let S = { lp: lps[0], model: "baseline", t: 0, playing: false, meshes: {}, entry: null, temps: null, bbox: null, geomOf: null };
  const models = {};   // model name -> {meshes, bbox}

  function resize() {
    const shot = Q0.has("shot"), w = shot ? innerWidth : box.clientWidth, h = shot ? innerHeight : Math.max(320, Math.min(640, w * 0.62));
    renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
  }
  addEventListener("resize", () => { resize(); draw(); });

  async function buildModel(entry) {
    if (models[entry.model]) return models[entry.model];
    const buf = await load(entry.geom), nvTot = entry.parts.reduce((a, p) => a + p.nv, 0);
    let ioff = nvTot * 12;
    const meshes = {}, bbox = new THREE.Box3();
    entry.parts.forEach((p, n) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(buf, p.v0 * 12, p.nv * 3), 3));
      g.setIndex(new THREE.BufferAttribute(new Uint32Array(buf, ioff, p.nt * 3), 1)); ioff += p.nt * 12;
      g.setAttribute("color", new THREE.BufferAttribute(new Float32Array(p.nv * 3), 3));
      g.computeVertexNormals(); g.computeBoundingBox(); bbox.union(g.boundingBox);
      const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ vertexColors: true, side: THREE.DoubleSide, clippingPlanes: planes,
        polygonOffset: true, polygonOffsetFactor: n * 0.4, polygonOffsetUnits: n }));
      m.userData = p; meshes[p.key] = m;
    });
    return (models[entry.model] = { meshes, bbox });
  }

  async function select(lp, model) {
    let entry = MAN[lp + "/" + model];
    if (!entry) { entry = MAN[lp + "/detailed"] || MAN[lp + "/baseline"]; model = entry.model; }
    document.querySelectorAll('input[name="v-model"]').forEach(r => { r.disabled = !MAN[lp + "/" + r.value]; r.checked = r.value === model; });
    $("v-note").textContent = "Loading…";
    const [M, temps] = await Promise.all([buildModel(entry), load(entry.temp)]);
    Object.values(S.meshes).forEach(m => scene.remove(m));
    const first = !S.bbox;
    S = Object.assign(S, { lp, model, entry, temps: new Uint8Array(temps), meshes: M.meshes, bbox: M.bbox });
    Object.values(M.meshes).forEach(m => scene.add(m));
    document.querySelectorAll("[data-part]").forEach(c => { c.disabled = !M.meshes[c.dataset.part]; c.parentNode.classList.toggle("off", c.disabled); });
    const tl = entry.times[entry.times.length - 1], sl = $("v-time");
    sl.max = tl; if (S.t > tl || first) S.t = tl; sl.value = S.t;
    const dts = entry.times.slice(1).map((t, i) => t - entry.times[i]);
    $("v-note").innerHTML = `${entry.name}, ${entry.torque} N·m @ ${entry.rpm} rpm, ${model} model. Saved fields every ${Math.min(...dts)} s` +
      (Math.max(...dts) > Math.min(...dts) ? `–${Math.max(...dts)} s` : "") + `, colours interpolated in between. The slider ends at the last saved field ` +
      `(${mmss(tl)}) before the winding reaches 180 °C (${mmss(entry.t_cut)}). Readout: volume max / mean from the CFD monitors; * = surface value.`;
    if (first) frame();
    if (location.hash.slice(1) !== lp) history.replaceState(null, "", "#" + lp);
    applyAll();
  }

  function frame() {
    const c = new THREE.Vector3(); S.bbox.getCenter(c); const r = S.bbox.getSize(new THREE.Vector3()).length();
    controls.target.copy(c); camera.position.set(c.x + r * 0.9, c.y + r * 0.55, c.z + r * 1.1); camera.near = r / 200; camera.far = r * 20;
    camera.updateProjectionMatrix(); controls.update();
  }

  // temperatures at time t (linear between saved fields) for vertex range of a part
  function tempsAt(t) {
    const e = S.entry, T = e.times; let i = 0;
    while (i < T.length - 2 && T[i + 1] < t) i++;
    const f = Math.min(1, Math.max(0, (t - T[i]) / (T[i + 1] - T[i]))), nv = e.parts.reduce((a, p) => a + p.nv, 0);
    return { a: i * nv, b: (i + 1) * nv, f, lo: e.q[0], k: (e.q[1] - e.q[0]) / 255, i };
  }
  const vT = (ti, v) => ti.lo + ti.k * (S.temps[ti.a + v] * (1 - ti.f) + S.temps[ti.b + v] * ti.f);
  function stat(p, t) {
    const e = S.entry, mx = interp(e.grid, p.mon_max, t), mn = interp(e.grid, p.mon_mean, t), ti = tempsAt(t), n = e.parts.indexOf(p);
    const ss = e.surf_stats, s0 = ss[ti.i][n], s1 = ss[Math.min(ss.length - 1, ti.i + 1)][n];
    const sm = j => s0[j] + ti.f * (s1[j] - s0[j]);
    return { max: mx != null ? mx : sm(0), mean: mn != null ? mn : sm(1), smax: mx == null, smean: mn == null };
  }
  function range(ti) {
    if ($("v-range").value === "fixed") {
      const hi = Math.max(...Object.values(MAN).filter(e => e.lp === S.lp).map(e => e.range[1]));
      return [40, hi];
    }
    let lo = 1e9, hi = -1e9;
    Object.values(S.meshes).forEach(m => { if (!m.visible) return; const p = m.userData;
      for (let v = p.v0; v < p.v0 + p.nv; v++) { const x = vT(ti, v); if (x < lo) lo = x; if (x > hi) hi = x; } });
    return hi > lo ? [Math.floor(lo), Math.ceil(hi + 0.5)] : [lo - 1, lo + 1];
  }
  function colour() {
    const ti = tempsAt(S.t), [lo, hi] = range(ti);
    Object.values(S.meshes).forEach(m => {
      if (!m.visible) return;
      const p = m.userData, col = m.geometry.attributes.color.array;
      for (let v = 0; v < p.nv; v++) { const c = turbo((vT(ti, p.v0 + v) - lo) / (hi - lo)); col[3 * v] = c[0]; col[3 * v + 1] = c[1]; col[3 * v + 2] = c[2]; }
      m.geometry.attributes.color.needsUpdate = true;
    });
    bar(lo, hi);
    $("v-tlab").textContent = `t = ${mmss(S.t)} (${Math.round(S.t)} s)`;
    $("v-read").innerHTML = "<tr><th>Part</th><th>Max (°C)</th><th>Mean (°C)</th></tr>" + S.entry.parts.filter(p => S.meshes[p.key].visible).map(p => {
      const s = stat(p, S.t);
      return `<tr><td>${p.label}</td><td>${s.max.toFixed(1)}${s.smax ? "*" : ""}</td><td>${s.mean.toFixed(1)}${s.smean ? "*" : ""}</td></tr>`;
    }).join("");
    S.range = [lo, hi]; S.ti = ti;
  }
  function bar(lo, hi) {
    const cv = $("v-bar"), g = cv.getContext("2d"), H = cv.height - 20;
    g.clearRect(0, 0, cv.width, cv.height);
    for (let y = 0; y < H; y++) { const c = turbo(1 - y / H); g.fillStyle = `rgb(${c.map(v => Math.round(v * 255))})`; g.fillRect(0, y + 10, 16, 1); }
    g.fillStyle = "#222"; g.font = "11px sans-serif";
    for (let k = 0; k <= 4; k++) g.fillText((hi - k * (hi - lo) / 4).toFixed(0) + " °C", 20, 14 + k * H / 4);
  }
  function geomUpdate() {
    const b = S.bbox, sz = b.getSize(new THREE.Vector3()), L = sz.z, ex = $("v-ex").value / 1000;
    let z0 = 1e9, z1 = -1e9;
    Object.values(S.meshes).forEach(m => {
      m.position.z = ex * L * (EXPLODE[m.userData.key] || 0);
      const bb = m.geometry.boundingBox; z0 = Math.min(z0, bb.min.z + m.position.z); z1 = Math.max(z1, bb.max.z + m.position.z);
    });
    const cz = $("v-cz").value / 1000, cx = $("v-cx").value / 1000;   // 1 = no cut; planes keep z <= c and x <= c
    planes[0].constant = cz >= 1 ? 1e3 : z0 + (z1 - z0) * cz;
    planes[1].constant = cx >= 1 ? 1e3 : b.min.x + sz.x * cx;
  }
  function applyAll() {
    document.querySelectorAll("[data-part]").forEach(c => { const m = S.meshes[c.dataset.part]; if (m) m.visible = c.checked; });
    geomUpdate(); colour(); draw();
  }
  function draw() { renderer.render(scene, camera); }

  // ---------------------------------------------------------------- probe
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), tri = new THREE.Triangle(), bc = new THREE.Vector3();
  renderer.domElement.addEventListener("mousemove", ev => {
    const r = renderer.domElement.getBoundingClientRect();
    mouse.set((ev.clientX - r.left) / r.width * 2 - 1, -(ev.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(mouse, camera);
    const hit = ray.intersectObjects(Object.values(S.meshes).filter(m => m.visible)).find(h => planes.every(p => p.distanceToPoint(h.point) >= 0));
    const pr = $("v-probe");
    if (!hit) { pr.style.display = "none"; return; }
    const p = hit.object.userData, pos = hit.object.geometry.attributes.position, f = hit.face;
    const A = new THREE.Vector3().fromBufferAttribute(pos, f.a), B = new THREE.Vector3().fromBufferAttribute(pos, f.b), C = new THREE.Vector3().fromBufferAttribute(pos, f.c);
    tri.set(A, B, C); tri.getBarycoord(hit.object.worldToLocal(hit.point.clone()), bc);
    const T = bc.x * vT(S.ti, p.v0 + f.a) + bc.y * vT(S.ti, p.v0 + f.b) + bc.z * vT(S.ti, p.v0 + f.c);
    pr.style.display = "block"; pr.style.left = (ev.clientX - r.left + 14) + "px"; pr.style.top = (ev.clientY - r.top + 10) + "px";
    pr.textContent = `${p.label}: ${T.toFixed(1)} °C (surface)`;
  });
  renderer.domElement.addEventListener("mouseleave", () => { $("v-probe").style.display = "none"; });

  // ---------------------------------------------------------------- controls
  controls.addEventListener("change", draw);
  let want = Q0.get("model") || "detailed";   // the user's model choice; points without it fall back to the other model
  $("v-lp").onchange = e => select(e.target.value, want);
  document.querySelectorAll('input[name="v-model"]').forEach(r => r.onchange = () => { want = r.value; select(S.lp, r.value); });
  document.querySelectorAll("[data-part]").forEach(c => c.onchange = applyAll);
  $("v-rotor").onclick = () => { document.querySelectorAll("[data-part]").forEach(c => { c.checked = ROTOR.includes(c.dataset.part); }); applyAll(); };
  $("v-all").onclick = () => { document.querySelectorAll("[data-part]").forEach(c => { c.checked = true; }); applyAll(); };
  $("v-time").oninput = e => { S.t = +e.target.value; colour(); draw(); };
  $("v-range").onchange = () => { colour(); draw(); };
  ["v-cz", "v-cx", "v-ex"].forEach(id => $(id).oninput = () => { geomUpdate(); draw(); });
  let last = 0;
  function tick(ts) {
    if (!S.playing) return;
    const dt = last ? (ts - last) / 1000 : 0; last = ts;
    const tl = +$("v-time").max; S.t = Math.min(tl, S.t + dt * +$("v-speed").value); $("v-time").value = S.t;
    colour(); draw();
    if (S.t >= tl) { S.playing = false; $("v-play").textContent = "▶ Play"; return; }
    requestAnimationFrame(tick);
  }
  $("v-play").onclick = () => {
    S.playing = !S.playing; $("v-play").textContent = S.playing ? "❚❚ Pause" : "▶ Play";
    if (S.playing) { if (S.t >= +$("v-time").max) S.t = 0; last = 0; requestAnimationFrame(tick); }
  };

  resize();
  const h0 = location.hash.slice(1);
  $("v-lp").value = lps.includes(h0) ? h0 : lps[0];
  const Q = new URLSearchParams(location.search);
  if (Q.get("lp")) $("v-lp").value = Q.get("lp");
  const ready = select($("v-lp").value, want);

  // still-image mode for the report (render_viewer_stills.py): viewer3d.html?shot&lp=..&model=..&t=..&ex=..&cx=..&cz=..&parts=a,b&title=..
  if (Q.has("shot")) ready.then(() => {
    ["ex", "cx", "cz"].forEach(k => { if (Q.get(k) != null) $("v-" + k).value = Q.get(k); });
    if (Q.get("parts")) { const on = Q.get("parts").split(","); document.querySelectorAll("[data-part]").forEach(c => { c.checked = on.includes(c.dataset.part); }); }
    if (Q.get("t") != null) { S.t = Math.min(+$("v-time").max, +Q.get("t")); $("v-time").value = S.t; }
    [...document.body.children].forEach(el => { el.style.display = "none"; });   // controls stay in the DOM (applyAll reads them)
    document.body.style.margin = "0"; document.body.style.background = "#fff";
    box.style.cssText = "border:0;border-radius:0;width:100vw;height:100vh"; document.body.appendChild(box);
    const cap = document.createElement("div"); cap.style.cssText = "position:absolute;left:14px;top:10px;font:600 16px sans-serif;color:#222";
    cap.textContent = (Q.get("title") || "") + `  t = ${mmss(S.t)}`; box.appendChild(cap);
    renderer.setClearColor(0xffffff); renderer.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    applyAll();
    const bb = new THREE.Box3(), keep = S.bbox;   // frame the visible parts
    Object.values(S.meshes).forEach(m => { if (m.visible) bb.expandByObject(m); });
    S.bbox = bb; frame(); S.bbox = keep;
    if (Q.get("zoom")) { camera.position.lerp(controls.target, 1 - 1 / +Q.get("zoom")); controls.update(); }
    draw(); document.title = "SHOT-READY";
  });

  // ---------------------------------------------------------------- self-test (viewer3d.html?selftest): drives the UI, reports in #v-selftest
  if (/selftest/.test(location.search)) ready.then(async () => {
    const out = [], px = () => { const g = renderer.getContext(), a = new Uint8Array(4); g.readPixels(renderer.domElement.width >> 1, renderer.domElement.height >> 1, 1, 1, g.RGBA, g.UNSIGNED_BYTE, a); return a.join(","); };
    const sumCol = () => Object.values(S.meshes).filter(m => m.visible).reduce((a, m) => a + m.geometry.attributes.color.array.reduce((x, y) => x + y, 0), 0);
    for (const k of Object.keys(MAN)) {
      const [lp, model] = k.split("/");
      await select(lp, model);
      S.t = 0; colour(); draw(); const c0 = sumCol(), r0 = $("v-read").rows.length;
      S.t = +$("v-time").max; $("v-time").value = S.t; colour(); draw(); const c1 = sumCol();
      $("v-rotor").click(); const vis = Object.values(S.meshes).filter(m => m.visible).map(m => m.userData.key).join("+");
      $("v-all").click();
      out.push({ entry: k, meshes: Object.keys(S.meshes).length, readoutRows: r0 - 1, colourChangesWithTime: Math.abs(c1 - c0) > 1,
        rotorGroup: vis, tmax: S.t, range: S.range.map(x => +x.toFixed(1)), centrePixel: px() });
    }
    const pre = document.createElement("pre"); pre.id = "v-selftest"; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
  }).catch(e => { const pre = document.createElement("pre"); pre.id = "v-selftest"; pre.textContent = "ERROR " + e; document.body.appendChild(pre); });
  ready.catch(e => { $("v-note").textContent = "Could not load viewer data: " + e.message; });
})();
