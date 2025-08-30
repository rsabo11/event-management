from flask import Flask, request, jsonify, render_template, make_response, g, redirect, url_for
from datetime import datetime, timedelta
import logging, os
from .db_api import get_connection
from .config import LOG_DIR
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps


from src.services.events_service import EventsService
from src.services.auth_service import AuthService
from src.services.bookings_service import BookingsService
from src.services.account_service import AccountService
from src.services.organizer_service import OrganizerService
from src.services.organizer_booking_service import (
    OrganizerBookingService, NotFound, NotPending, NoCapacity, BadStatus
)

events_service = EventsService(get_connection)

app = Flask(__name__, static_folder="../static", template_folder="../templates", static_url_path="/static")

# ===============================
# SECTION: Hilfsfunktionen
# nur hier sind SQL-Queries innerhalb app.py, sonst ausgelagert
# ===============================

def user_owns_event(event_id: int, user_id: int) -> bool:
    with get_connection() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM event WHERE id=%s AND organizer_id=%s", (event_id, user_id))
        return cur.fetchone() is not None

def is_organizer_user(user_id: int) -> bool:
    with get_connection() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM organizer WHERE user_id=%s", (user_id,))
        return cur.fetchone() is not None

def organizer_owns_booking(booking_id: int, organizer_id: int) -> bool:
    with get_connection() as con, con.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM booking b
            JOIN event   e ON e.id = b.event_id
            WHERE b.id=%s AND e.organizer_id=%s
            """,
            (booking_id, organizer_id),
        )
        return cur.fetchone() is not None

def require_login(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return jsonify({"error": "unauthorized"}), 401
        g.user = u
        return fn(*args, **kwargs)
    return wrapper

def require_organizer(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return jsonify({"error": "unauthorized"}), 401
        if not is_organizer_user(u["id"]):
            return jsonify({"error": "forbidden"}), 403
        g.user = u
        return fn(*args, **kwargs)
    return wrapper

def current_user():
    token = request.cookies.get("session")
    if not token:
        return None
    with get_connection() as con, con.cursor() as cur:
        cur.execute("""
            SELECT u.id, u.email, u.full_name,
                   (o.user_id IS NOT NULL) AS is_organizer,
                   o.company
            FROM session s
            JOIN user u ON u.id = s.user_id
            LEFT JOIN organizer o ON o.user_id = u.id
            WHERE s.token=%s AND s.expires_at > NOW()
        """, (token,))
        return cur.fetchone()

# ===============================
# SECTION: Logging Funktion (nicht fertig)
# ===============================

fname = os.path.join(LOG_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")
logging.basicConfig(filename=fname, level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

# ===============================
# SECTION: Mini Cache (nicht fertig)
# ===============================

_cache = {}
def cache_get(key):
    v = _cache.get(key)
    if not v: return None
    data, ttl = v
    if datetime.now() > ttl: _cache.pop(key, None); return None
    return data
def cache_set(key, data, seconds=30):
    _cache[key] = (data, datetime.now() + timedelta(seconds=seconds))

# ===============================
# SECTION: Home-Seite + Database-Check
# ===============================

@app.get("/")
def home():
    u = current_user()
    return render_template("index.html", me=u)

@app.get("/health-db")
def health():
    try:
        with get_connection() as con, con.cursor() as cur:
            cur.execute("SELECT VERSION() AS v")
            v = cur.fetchone()["v"]
            return jsonify(ok=True, version=v)
    except Exception as e:
        logging.error(f"health error: {e}")
        return jsonify(ok=False, error=str(e)), 500

# ===============================
# SECTION: Event APIs
# ===============================

events_service = EventsService(get_connection)

# listet alle Events
@app.get("/api/event")
def list_event():
    u = current_user()
    rows = events_service.list_event(request.args, u)
    return jsonify(rows)

# stellt Booking Anfrage ('pending')
@app.post("/api/event/<int:eid>/book")
@require_login
def book_event(eid):
    u = current_user()
    data = request.get_json(force=True) if request.data else {}
    result, status = events_service.book_event(eid, u, data)
    return jsonify(result), status

# Event Anfrage zurückziehen (falls es noch nicht angenommen wurde)
@app.delete("/api/event/<int:eid>/book")
@require_login
def cancel_booking(eid):
    u = current_user()

    if not u:
        return jsonify({"error": "unauthorized"}), 401
    
    if is_organizer_user(u["id"]):
        return jsonify({"error": "organizer_cannot_book"}), 403

    result, status = events_service.cancel_booking(eid, u)
    return jsonify(result), status

# liefert Event mit jeweiliger ID
@app.get("/api/event/<int:eid>")
def get_event(eid):
    row, status = events_service.get_event(eid)
    return jsonify(row), status

# Legt neues Event an
@app.post("/api/event")
@require_organizer
def create_event():
    data = request.get_json(force=True)
    req = ("title", "start_date", "end_date")

    if not all(k in data for k in req):
        return jsonify({"error": "missing fields"}), 400

    organizer_id = g.user["id"]

    eid = events_service.create_event(organizer_id, data)

    _cache.pop("event", None)
    logging.info(f"user:create_event id={eid}")

    return jsonify({"id": eid}), 201

# aktualisiert bestehendes Event
@app.put("/api/event/<int:eid>")
@require_organizer
def update_event(eid):
    if not user_owns_event(eid, g.user["id"]):
        return jsonify({"error": "forbidden"}), 403

    data = request.get_json(force=True)

    try:
        changed = events_service.update_event(eid, data)
    except ValueError:
        return jsonify({"error": "no fields"}), 400

    _cache.pop("event", None)
    logging.info(f"user:update_event id={eid}")
    return jsonify({"updated": changed})

# löscht bestehendes Event
@app.delete("/api/event/<int:eid>")
@require_organizer
def delete_event(eid):
    # Ownership bleibt in app.py
    if not user_owns_event(eid, g.user["id"]):
        return jsonify({"error": "forbidden"}), 403

    deleted = events_service.delete_event(eid)

    _cache.pop("event", None)
    logging.info(f"user:delete_event id={eid}")

    return jsonify({"deleted": deleted})

# lädt Kategorien
@app.get("/api/category")
def list_categories():
    with get_connection() as con, con.cursor() as cur:
        cur.execute("SELECT id, name FROM categorie ORDER BY name")
        return jsonify(cur.fetchall())

# ===============================
# SECTION: Authentifizierungsfunktionen
# ===============================

auth_service = AuthService(get_connection)

# Erstellt normalen User
@app.post("/api/user")
def register_user():
    data = request.get_json(force=True)
    payload, status = auth_service.register_user(data)
    return jsonify(payload), status

# Erstellt Unternehmen
@app.post("/api/organizer")
def register_company():
    data = request.get_json(force=True)
    payload, status = auth_service.register_company(data)
    return jsonify(payload), status

# Authentifizierungsseite
@app.get("/auth")
def auth_page():
    return render_template("auth.html")

# Login
@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    result, status = auth_service.login(data)

    if status != 200:
        return jsonify(result), status

    cookie = result.pop("cookie")
    resp = make_response(jsonify(result))
    resp.set_cookie(
        "session",
        cookie["token"],
        httponly=True,
        samesite="Lax",
        secure=False,  # in Prod: True
        max_age=7*24*3600
    )
    return resp

# Ausloggen
@app.post("/api/logout")
def logout():
    token = request.cookies.get("session")
    result = auth_service.logout(token)
    resp = make_response(jsonify(result))
    resp.delete_cookie("session")
    return resp

# liefert aktuelle User-Daten anhand des Session-Tokens
@app.get("/api/me")
def me():
    u = current_user()
    if not u:
        return jsonify({"error":"unauthorized"}), 401
    u["is_organizer"] = is_organizer_user(u["id"])
    return jsonify(u)

# ===============================
# SECTION: Buchungen + Reviews
# ===============================

bookings_service = BookingsService(get_connection)

# liefert Buchungen für jeweiligen User
@app.get("/api/my-bookings")
@require_login
def my_bookings():
    u = current_user()
    if not u:
        return jsonify({"error": "not logged in"}), 401

    rows = bookings_service.list_user_bookings(u["id"])
    return jsonify(rows)

# erstellt oder aktualisiere eine Bewertung
@app.post("/api/reviews")
@require_login
def create_or_update_review():
    u = current_user()
    if not u:
        return jsonify({"error": "not logged in"}), 401

    data = request.get_json(force=True)
    if not data or "event_id" not in data or "rating" not in data:
        return jsonify({"error": "missing fields"}), 400

    try:
        event_id = int(data["event_id"])
        rating   = int(data["rating"])
    except (TypeError, ValueError):
        return jsonify({"error": "invalid payload"}), 400

    comment = data.get("comment", "")

    if rating < 1 or rating > 5:
        return jsonify({"error": "rating_out_of_range"}), 400

    bookings_service.upsert_review(u["id"], event_id, rating, comment)
    return jsonify({"ok": True})

# ===============================
# SECTION: Accounteinstellungen
# ===============================

account_service = AccountService(get_connection)

# Accounteinstellungen-Seite
@app.get("/account")
def account_page():
    u = current_user()
    if not u:
        return redirect(url_for("auth_page") + "?next=/account")
    return render_template("account.html")

# aktualisiert Daten eines bestehendes Accounts
@app.post("/api/account")
@require_login
def update_account():
    u = current_user()
    if not u:
        return jsonify({"error": "not logged in"}), 401

    data = request.get_json(force=True) or {}
    new_full = data.get("full_name")
    new_mail = data.get("email")
    new_pwd  = data.get("password")
    new_comp = data.get("company")  # nur relevant, wenn Nutzer Organizer ist

    account_service.update_account(
        user_id=u["id"],
        new_full=new_full,
        new_mail=new_mail,
        new_pwd=new_pwd,
        new_comp=new_comp,
    )

    return jsonify({"ok": True})

# ===============================
# SECTION: Eventeinstellungen (für Organizer)
# ===============================

organizer_service = OrganizerService(get_connection)

# liefert Seite für Event (nur für Organizer)
@app.get("/organizer/events")
@require_organizer
def organizer_events_page():
    return render_template("org_events.html")

# liefert alle Events für einen bestimmten Organizer
@app.get("/api/organizer/events")
@require_organizer
def organizer_events_api():
    u = g.user
    rows = organizer_service.list_my_events(u["id"])
    return jsonify(rows)

# liefert Bearbeitungsseite für ein bestimmtes Event zurück
@app.get("/organizer/event/<int:eid>/edit")
@require_organizer
def organizer_event_edit_page(eid):
    if not user_owns_event(eid, g.user["id"]):
        return jsonify({"error": "forbidden"}), 403
    return render_template("org_event_edit.html", eid=eid)

# lädt Eventdaten für ein bestimmtes Event
@app.get("/api/organizer/event/<int:eid>")
@require_organizer
def organizer_event_get(eid):
    if not user_owns_event(eid, g.user["id"]):
        return jsonify({"error": "forbidden"}), 403

    row = organizer_service.get_event(eid)
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify(row)

# ===============================
# SECTION: Booking Liste für Organizer
# ===============================

organizer_booking_service = OrganizerBookingService(get_connection)

# listet Buchungen Events von Organizer auf
@app.get("/api/organizer/bookings")
@require_organizer
def organizer_bookings_list():
    u = g.user
    status = request.args.get("status", "pending")
    if status not in ("pending", "paid", "cancelled"):
        return jsonify({"error": "bad_status"}), 400

    rows = organizer_booking_service.list_by_status(u["id"], status)
    return jsonify(rows)

# Organizer nimmt eine Buchungsanfrage an
@app.post("/api/organizer/booking/<int:bid>/approve")
@require_organizer
def organizer_booking_approve(bid):
    org = g.user

    if not organizer_owns_booking(bid, org["id"]):
        return jsonify({"error": "forbidden"}), 403

    try:
        res = organizer_booking_service.approve(bid)
        return jsonify(res)
    except NotFound:
        return jsonify({"error": "not_found"}), 404
    except NotPending:
        return jsonify({"error": "not_pending"}), 409
    except NoCapacity as e:
        return jsonify({"error": "no_capacity", "free": e.free}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Organizer lehnt eine Buchungsanfrage ab
@app.post("/api/organizer/booking/<int:bid>/reject")
@require_organizer
def organizer_booking_reject(bid):
    org = g.user

    # Ownership bleibt hier
    if not organizer_owns_booking(bid, org["id"]):
        return jsonify({"error": "forbidden"}), 403

    try:
        res = organizer_booking_service.reject(bid)
        return jsonify(res)
    except NotFound:
        return jsonify({"error": "not_found"}), 404
    except NotPending:
        return jsonify({"error": "not_pending"}), 409

# Buchungen auflisten (nur für Organizer)
@app.get("/api/organizer/bookings")
@require_organizer
def organizer_bookings_api():
    u = g.user
    status = request.args.get("status", "pending")

    try:
        rows = organizer_booking_service.list_api(u["id"], status)
        return jsonify(rows)
    except BadStatus:
        return jsonify({"error": "bad_status"}), 400

# Seite für alle Requests
@app.get("/organizer/requests")
@require_organizer
def organizer_requests_page():
    return render_template("org_requests.html")

# ===============================
# SECTION: Startet App + Debug Modus
# ===============================

if __name__ == "__main__":
    app.run(debug=True)