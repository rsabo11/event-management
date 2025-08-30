
// Einmalige fetch-Logik installieren
async function fetchJSON(url, options={}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// Einloggen
document.querySelector("#login-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const data = {
      email: document.querySelector("#login-email").value,
      password: document.querySelector("#login-password").value
    };
    await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(r => { if(!r.ok) throw new Error("Login hat nicht geklappt."); return r.json(); });

    window.location.href = "/";  // zurück zur Startseite
  } catch (err) {
    alert(err.message);
  }
});

// Registrierung als User
document.querySelector("#register-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const data = {
      full_name: document.querySelector("#reg-name").value,
      email: document.querySelector("#reg-email").value,
      password: document.querySelector("#reg-password").value
    };
    const res = await fetchJSON("/api/user", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    alert("Registrierung erfolgreich! Einfach einloggen.");
  } catch (err) {
    alert("Registrierung hat nicht geklappt: " + err.message);
  }
});

// Registrierung als Unternehmen
document.querySelector("#register-company-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const data = {
      full_name: document.querySelector("#reg-company-name").value,
      email: document.querySelector("#reg-company-email").value,
      password: document.querySelector("#reg-company-password").value,
      company: document.querySelector("#reg-company").value
    };
    const res = await fetchJSON("/api/organizer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    alert("Registrierung erfolgreich! Einfach einloggen.");
  } catch (err) {
    alert("Registrierung hat nicht geklappt: " + err.message);
  }
});


async function initAuthUI() {
  try {
    const res = await fetch("/api/me");

    // Falls nicht eingeloggt
    if (!res.ok) {
      window.__ME__ = null;

      const secMy  = document.getElementById("sec-mybookings");
      const secNew = document.getElementById("sec-new-event");
      if (secMy)  secMy.style.display  = "none";
      if (secNew) secNew.style.display = "none";

      const hint = document.getElementById("mybk-hint");
      if (hint) hint.style.display = "";
      return;
    }

    // Eingeloggt
    const me = await res.json();
    window.__ME__ = me; // wichtig für Events-Logik

    // Funktionen in der Auth Area
    const el = document.getElementById("auth-area");
    if (el) {
      el.innerHTML = `
        Angemeldet als ${me.full_name}
        <button id="btn-account" onclick="location.href='/account'">Konto</button>
        <button id="btn-logout">Logout</button>
        ${
          me.is_organizer
            ? `
              <a href="/organizer/events" 
                style="background:#007bff;color:#fff;padding:8px 12px;
                        border-radius:6px;text-decoration:none;">Meine Events</a>
              <a href="/organizer/requests" 
                style="background:#007bff;color:#fff;padding:8px 12px;
                        border-radius:6px;text-decoration:none;">Anfragen</a>
            `
            : ''
        }
      `;

      const b = document.getElementById("btn-logout");
      if (b) {
        b.onclick = async () => {
          await fetch("/api/logout", { method: "POST" });
          window.__ME__ = null;
          location.reload();
        };
      }
    }

    // Bereiche ein-/ausblenden
    const secMy  = document.getElementById("sec-mybookings");
    const secNew = document.getElementById("sec-new-event");
    if (secMy)  secMy.style.display  = ""; // sichtbar für eingeloggte
    if (secNew) secNew.style.display = me.is_organizer ? "" : "none"; // nur Organizer

    const hint = document.getElementById("mybk-hint");
    if (hint) hint.style.display = "none";

    // Buchungen sofort laden (falls vorhanden)
    if (typeof loadMyBookings === "function") {
      loadMyBookings();
    }
  } catch {}
}