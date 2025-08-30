const $ = (sel) => document.querySelector(sel);

function disable_element(id, on=true) { const el = document.getElementById(id); if (!el) return; el.disabled = on; }
function show_msg(text, ok=true) { const m = $("#msg"); m.textContent = text; m.style.color = ok ? "green" : "crimson"; }

// Hilfsfunktion für API-Calls
async function fetchJSON(url, opts={}) {
  const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}