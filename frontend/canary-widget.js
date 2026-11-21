/*! Chrono-Shield-Onion canary widget
 *  <div data-chrono-canary data-src="https://TU-NODO/canary" data-pin="HUELLA_SHA256"></div>
 *  <script src=".../canary-widget.js" defer></script>
 *  Verifica la firma RSA en el navegador; solo confía en la huella fijada. */
(function (g) {
  "use strict";
  var MAX_AGE_S = 180;
  var REPO = "https://github.com/contactochronoshield-cyber/Chrono-Shield-Onion";

  function b64ToBytes(b64) {
    var s = atob(b64), a = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) a[i] = s.charCodeAt(i);
    return a;
  }
  function pemToDer(pem) { return b64ToBytes(pem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "")); }
  function hex(buf) {
    return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
  }

  async function verify(data, pin, nowMs) {
    var subtle = g.crypto && g.crypto.subtle;
    if (!subtle) return { state: "error", reason: "WebCrypto no disponible (requiere HTTPS)" };
    try {
      var der = pemToDer(data.public_key_pem);
      var fp = hex(await subtle.digest("SHA-256", der));
      if (pin && fp !== pin.replace(/:/g, "").toLowerCase()) return { state: "pin_mismatch", fingerprint: fp };
      var raw = data.statement_raw;
      if (typeof raw !== "string") return { state: "invalid", reason: "falta statement_raw" };
      var key = await subtle.importKey("spki", der, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
      var ok = await subtle.verify("RSASSA-PKCS1-v1_5", key, b64ToBytes(data.signature_b64), new TextEncoder().encode(raw));
      if (!ok) return { state: "invalid", fingerprint: fp };
      var st = JSON.parse(raw);
      var age = (nowMs || Date.now()) / 1000 - st.timestamp;
      var res = { fingerprint: fp, node_id: st.node_id, age: age, pinned: !!pin };
      res.state = age > MAX_AGE_S ? "stale" : (pin ? "verified" : "unpinned");
      return res;
    } catch (e) { return { state: "error", reason: String(e) }; }
  }

  var LABEL = {
    loading: ["Verificando integridad…", "#6e7781"],
    verified: ["Integridad verificada en tiempo real por ", "#1a7f37"],
    unpinned: ["Firma válida, clave no fijada · ", "#9a6700"],
    stale: ["Canary vencido: sin firma reciente · ", "#bc4c00"],
    invalid: ["¡FIRMA INVÁLIDA! · ", "#cf222e"],
    pin_mismatch: ["¡Clave distinta a la esperada! · ", "#cf222e"],
    error: ["No se pudo verificar · ", "#6e7781"]
  };

  function mount(el) {
    var src = el.getAttribute("data-src"), pin = el.getAttribute("data-pin") || "";
    var box = el.attachShadow ? el.attachShadow({ mode: "open" }) : el;
    box.innerHTML = '<style>.w{display:inline-flex;align-items:center;gap:8px;font:13px system-ui,sans-serif;' +
      'padding:6px 10px;border:1px solid #d0d7de;border-radius:999px;background:#fff;color:#24292f}' +
      '.d{width:9px;height:9px;border-radius:50%}a{color:inherit;font-weight:600}</style>' +
      '<span class="w"><i class="d"></i><span class="t"></span><a target="_blank" rel="noopener"></a></span>';
    var w = box.querySelector(".w"), dot = box.querySelector(".d"), t = box.querySelector(".t"), a = box.querySelector("a");
    a.href = REPO; a.textContent = "Chrono-Shield-Onion";
    function paint(res) {
      var l = LABEL[res.state] || LABEL.error;
      dot.style.background = l[1]; t.textContent = l[0];
      a.style.display = res.state === "loading" ? "none" : "";
      w.title = (res.fingerprint ? "Clave: " + res.fingerprint + "\n" : "") +
        (res.node_id ? "Nodo: " + res.node_id + "\n" : "") +
        (res.age != null ? "Firmado hace " + Math.round(res.age) + " s\n" : "") + (res.reason || "");
    }
    async function tick() {
      var res;
      try {
        var r = await fetch(src, { cache: "no-store" });
        res = await verify(await r.json(), pin);
      } catch (e) { res = { state: "error", reason: "endpoint inaccesible" }; }
      paint(res);
    }
    paint({ state: "loading" }); tick(); setInterval(tick, 30000);
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { verify: verify };
  if (typeof document !== "undefined") {
    var go = function () { Array.prototype.forEach.call(document.querySelectorAll("[data-chrono-canary]"), mount); };
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", go) : go();
  }
})(typeof globalThis !== "undefined" ? globalThis : window);
