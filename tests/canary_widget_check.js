const { verify } = require("../frontend/canary-widget.js");
const d = JSON.parse(require("fs").readFileSync(process.argv[2]));
const pin = process.argv[3];
(async () => {
  const bad = JSON.parse(JSON.stringify(d)); bad.statement_raw += " ";
  const cases = [
    ["con pin correcto", await verify(d, pin), "verified"],
    ["sin pin", await verify(d, ""), "unpinned"],
    ["pin equivocado", await verify(d, "00".repeat(32)), "pin_mismatch"],
    ["texto alterado", await verify(bad, pin), "invalid"],
    ["firma vieja", await verify(d, pin, Date.now() + 3600e3), "stale"],
  ];
  let fail = 0;
  for (const [n, r, want] of cases) {
    const ok = r.state === want; if (!ok) fail++;
    console.log((ok ? "OK   " : "FALLA"), n, "->", r.state);
  }
  process.exit(fail ? 1 : 0);
})();
