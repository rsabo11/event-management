
// füllt Accountformular sobald Seite geladen ist
window.addEventListener("DOMContentLoaded", async () => {
  try {
    const meRes = await fetch("/api/me");
    if (!meRes.ok) throw new Error("Nicht eingeloggt");
    const me = await meRes.json();

    $("#acc-fullname").value = me.full_name || "";
    $("#acc-email").value    = me.email || "";

    const wrap = $("#acc-org-wrap");
    if (wrap) wrap.style.display = me.is_organizer ? "" : "none";
    if (me.is_organizer && $("#acc-company")) {
      $("#acc-company").value = me.company || "";
    }
  } catch (e) {
    $("#acc-msg").textContent = "Fehler: " + e.message;
  }
});

// Speichert Änderungen
$("#account-form")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  disable_element("acc-save", true);
  $("#acc-msg").textContent = "";

  try {
    const body = {
      full_name: $("#acc-fullname").value.trim(),
      email: $("#acc-email").value.trim()
    };
    const pwd = $("#acc-password").value;
    if (pwd) body.password = pwd;

    if ($("#acc-org-wrap") && $("#acc-org-wrap").style.display !== "none") {
      body.company = ($("#acc-company")?.value || "").trim();
    }

    const res = await fetch("/api/account", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error(await res.text());

    $("#acc-msg").textContent = "Änderungen gespeichert ✔";
    $("#acc-password").value = "";
  } catch (e) {
    $("#acc-msg").textContent = "Speichern fehlgeschlagen: " + e.message;
  } finally {
    disable_element("acc-save", false);
  }
});