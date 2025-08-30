
// Kategorieren im Dropdown wählen
async function loadCategories() {
  try {
    const cats = await fetchJSON("/api/category");
    $("#cat").innerHTML =
      '<option value="">Kategorien</option>' +
      cats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  } catch (e) {
    show_msg("Kategorien laden fehlgeschlagen: " + e.message, false);
  }
}

// Filter einsammeln
function collectFilters() {
  const params = {
    q: ($("#q")?.value || "").trim(),
    location: ($("#location")?.value || "").trim(),
    from: ($("#from")?.value || "").trim(),
    to: ($("#to")?.value || "").trim(),
    min_price: ($("#minp")?.value || "").trim(),
    max_price: ($("#maxp")?.value || "").trim(),
    category_id: ($("#cat")?.value || "").trim()
  };
  Object.keys(params).forEach(k => (params[k] === "" || params[k] == null) && delete params[k]);
  return params;
}

// Events laden (komplett oder mit Filter) + dynamischer Buchungs-Button (enthält noch Fehler)
async function loadEvents(params = {}) {
  disable_element("btn-load", true);
  try {
    const qs = new URLSearchParams(params).toString();
    const data = await fetchJSON("/api/event" + (qs ? `?${qs}` : ""));

    const me = window.__ME__ || null;

    $("#list").innerHTML = data.map(e => {
      const capacity = e.capacity ?? 0;
      const booked   = e.booked   ?? 0;
      const free     = Math.max(0, capacity - booked);

      let btnHtml = '<button class="need-login">Login nötig</button>';
      // if (me) {
      //   if (me.is_organizer) {
      //     btnHtml = "";
      //   } else if (free <= 0) {
      //     btnHtml = '<button class="soldout" disabled>Ausverkauft</button>';
      //   } else if (e.already_booked) {
      //     btnHtml = `<button class="unbook" data-id="${e.id}">Buchung stornieren</button>`;
      //   } else {
      //     btnHtml = `<button class="book" data-id="${e.id}">Anfragen</button>`;
      //   }
      // }
      if (me) {
        if (me.is_organizer) {
          btnHtml = "";
        } else if (e.my_paid) { // 1 oder true
          btnHtml = '<button disabled style="background:#9ca3af;color:#fff;padding:6px 10px;border-radius:6px;cursor:not-allowed;">Gebucht</button>';
        } else if (free <= 0) {
          btnHtml = '<button class="soldout" disabled>Ausverkauft</button>';
        } else if (e.already_booked) {
          btnHtml = `<button class="unbook" data-id="${e.id}">Buchung stornieren</button>`;
        } else {
          btnHtml = `<button class="book" data-id="${e.id}">Anfragen</button>`;
        }
      }

      return `
        <li>
          #${e.id} <b>${e.title}</b> — ${e.start_date} (${e.location || ""})
          — Plätze: ${free}/${capacity}
          ${btnHtml}
        </li>
      `;
    }).join("");
  } catch (e) {
    show_msg("Fehler beim Laden: " + e.message, false);
  } finally {
    disable_element("btn-load", false);
  }
}

$("#btn-load")?.addEventListener("click", () => loadEvents(collectFilters()));
$("#btn-filter")?.addEventListener("click", () => loadEvents(collectFilters()));

// Neues Event speichern (Formular f)
$("#f")?.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  disable_element("btn-save", true);
  try {
    const fd = new FormData(ev.target);
    const body = Object.fromEntries(fd.entries());
    body.organizer_id   = +body.organizer_id || 1;
    body.price_in_cents = +body.price_in_cents || 0;
    body.capacity       = +body.capacity || 0;

    await fetchJSON("/api/event", {
      method: "POST",
      body: JSON.stringify(body)
    });
    show_msg("Event gespeichert ✔");
    ev.target.reset();
    loadEvents(collectFilters());
  } catch (e) {
    show_msg("Speichern fehlgeschlagen: " + e.message, false);
  } finally {
    disable_element("btn-save", false);
  }
});

// Klick-Handling in der Eventliste: Löschen, Edit, Buchen, Stornieren, Login-Link
$("#list")?.addEventListener("click", async (ev) => {
  const btn = ev.target;
  if (!(btn instanceof HTMLElement)) return;

  const id = btn.dataset?.id;
  
  if (btn.classList.contains("need-login")) {
    location.href = "/auth";
    return;
  }

  // Event Buchen
  if (btn.classList.contains("book")) {
    if (!id) return;

    // Rollen-/Login-Check
    const me = window.__ME__;
    if (!me) {
      location.href = "/auth";
      return;
    }
    
    if (me.is_organizer) {
      show_msg("Organisatoren können keine Tickets buchen.", false);
      return;
    }

    try {
      await fetchJSON(`/api/event/${id}/book`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ qty: 1 })
      });
      show_msg("Ticket gebucht ✔");
      loadEvents(collectFilters());
    } catch (e) {
      show_msg("Buchung fehlgeschlagen: " + e.message, false);
    }
    return;
  }

  // Event stornieren (nur wenn 'pending')
  if (btn.classList.contains("unbook")) {
    if (!id) return;

    // Rollen-/Login-Check
    const me = window.__ME__;
    if (!me) {
      location.href = "/auth";
      return;
    }
    if (me.is_organizer) {
      show_msg("Organisatoren können Buchungen nicht stornieren.", false);
      return;
    }

    if (!confirm(`Buchung für Event #${id} stornieren?`)) return;
    try {
      await fetchJSON(`/api/event/${id}/book`, { method: "DELETE" });
      show_msg("Buchung storniert ✔");
      loadEvents(collectFilters());
    } catch (e) {
      show_msg("Stornierung fehlgeschlagen: " + e.message, false);
    }
    return;
  }
});

loadCategories();
loadEvents();

// Buchungen des eingeloggten Users laden
async function loadMyBookings() {
  try {
    const bookings = await fetchJSON("/api/my-bookings");
    const ul = document.getElementById("mybookings");
    if (!ul) return;

    ul.innerHTML = bookings.map(b => `
      <li data-eid="${b.event_id}">
        <b>${b.title}</b> — ${b.start_date} (${b.location || ""})
        | Status: ${b.status}, Menge: ${b.qty}
        <div class="review">
          ${
            b.my_rating
              ? `Bewertung: ${"★".repeat(b.my_rating)}${"☆".repeat(5 - b.my_rating)}`
              : `
                <form class="review-form">
                  <label>
                    Bewertung:
                    <select name="rating">
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3" selected>3</option>
                      <option value="4">4</option>
                      <option value="5">5</option>
                    </select>
                  </label>
                  <input name="comment" placeholder="Kommentar (optional)">
                  <button type="submit">Abschicken Jetzt</button>
                </form>
              `
          }
        </div>
      </li>
    `).join("");
  } catch (err) {
    const ul = document.getElementById("mybookings");
    if (ul) ul.innerHTML = `<li>Fehler beim Laden der Buchungen: ${err.message}</li>`;
  }
}

// Review abschicken
document.getElementById("mybookings")?.addEventListener("submit", async (ev) => {
  const form = ev.target.closest(".review-form");
  if (!form) return;
  ev.preventDefault();

  const li = form.closest("li");
  const eventId = +li.dataset.eid;
  const rating  = +form.rating.value;
  const comment = form.comment.value.trim();

  try {
    await fetchJSON("/api/reviews", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, rating, comment })
    });
    // direkt im DOM ersetzen
    li.querySelector(".review").innerHTML =
      `Bewertung: ${"★".repeat(rating)}${"☆".repeat(5 - rating)}`;
  } catch (e) {
    alert("Bewerten fehlgeschlagen: " + e.message);
  }
});