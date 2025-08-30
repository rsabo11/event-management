
# Klasse für alle Event-Services
class EventsService:
    def __init__(self, get_connection):
        self.get_connection = get_connection

    def list_event(self, query_args, user):
        base = [
            "SELECT",
            " e.id, e.title, e.start_date, e.end_date, e.location, e.price_in_cents, e.capacity,",
            " COALESCE(SUM(CASE WHEN b.status='paid' THEN b.qty END),0) AS booked,",
            # wenn eingeloggt: echte Prüfung, sonst 0/FALSE ohne Platzhalter
            (" MAX(CASE WHEN b.user_id=%s AND b.status='paid' THEN 1 ELSE 0 END) AS my_paid," if user else " 0 AS my_paid,"),
            (" EXISTS(SELECT 1 FROM booking b2 WHERE b2.event_id=e.id AND b2.user_id=%s AND b2.status IN ('pending','paid')) AS already_booked" if user else " FALSE AS already_booked"),
            "FROM event e",
            "LEFT JOIN booking b ON b.event_id = e.id",
        ]
        where = []
        args = []

        q           = (query_args.get("q") or "").strip()
        location    = (query_args.get("location") or "").strip()
        date_from   = (query_args.get("from") or "").strip()
        date_to     = (query_args.get("to") or "").strip()
        min_price   = (query_args.get("min_price") or "").strip()
        max_price   = (query_args.get("max_price") or "").strip()
        category_id = (query_args.get("category_id") or "").strip()

        if q:
            where.append("(e.title LIKE %s OR e.description LIKE %s)")
            like = f"%{q}%"
            args += [like, like]
        if location:
            where.append("e.location LIKE %s")
            args.append(f"%{location}%")
        if date_from:
            where.append("e.start_date >= %s")
            args.append(date_from)
        if date_to:
            where.append("e.end_date <= %s")
            args.append(date_to)
        if min_price:
            where.append("e.price_in_cents >= %s")
            args.append(int(min_price))
        if max_price:
            where.append("e.price_in_cents <= %s")
            args.append(int(max_price))
        if category_id:
            base.append("LEFT JOIN event_categorie ec ON ec.event_id = e.id")
            where.append("ec.category_id = %s")
            args.append(int(category_id))

        if where:
            base.append("WHERE " + " AND ".join(where))

        base.append("GROUP BY e.id")
        base.append("ORDER BY e.start_date")

        if user:
            args = [user["id"], user["id"]] + args

        sql = "\n".join(base)

        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(sql, args)
            rows = cur.fetchall()

        # freie Plätze nur paid-basiert
        for r in rows:
            booked = r.get("booked") or 0
            r["free"] = max(0, (r.get("capacity") or 0) - booked)

        return rows
    
    def book_event(self, eid, user, data):
        if not user:
            return {"error": "unauthorized"}, 401

        qty = int(data.get("qty", 1))
        if qty <= 0:
            return {"error": "qty must be > 0"}, 400

        try:
            with self.get_connection() as con:
                con.begin()
                with con.cursor() as cur:
                    # Lock event row
                    cur.execute("SELECT capacity FROM event WHERE id=%s FOR UPDATE", (eid,))
                    ev = cur.fetchone()
                    if not ev:
                        con.rollback()
                        return {"error": "event not found"}, 404

                    # Current booked
                    cur.execute("""
                        SELECT COALESCE(SUM(qty),0) AS booked
                        FROM booking
                        WHERE event_id=%s AND status IN ('pending','paid')
                    """, (eid,))
                    booked = cur.fetchone()["booked"]
                    free = ev["capacity"] - booked
                    if free < qty:
                        con.rollback()
                        return {"error": "sold_out_or_not_enough", "free": free}, 409

                    # Already booked?
                    cur.execute("""
                        SELECT 1 FROM booking
                        WHERE event_id=%s AND user_id=%s AND status IN ('pending','paid') LIMIT 1
                    """, (eid, user["id"]))
                    if cur.fetchone():
                        con.rollback()
                        return {"error": "already_booked"}, 409

                    # Create booking
                    cur.execute("""
                        INSERT INTO booking(user_id,event_id,qty,status)
                        VALUES(%s,%s,%s,'pending')
                    """, (user["id"], eid, qty))
                    con.commit()
                    return {"ok": True}, 200
        except Exception as e:
            try: con.rollback()
            except: pass
            return {"error": str(e)}, 500

    def cancel_booking(self, eid, user):
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute("""
                UPDATE booking
                   SET status='cancelled'
                 WHERE user_id=%s
                   AND event_id=%s
                   AND status='pending'
            """, (user["id"], eid))
            changed = cur.rowcount

        if changed == 0:
            return {"error": "booking_already_paid_or_not_found"}, 400

        return {"ok": True, "cancelled": changed}, 200

    def get_event(self, eid):
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute("SELECT * FROM event WHERE id=%s", (eid,))
            row = cur.fetchone()

        if not row:
            return {"error": "not found"}, 404
        return row, 200
    
    def create_event(self, organizer_id: int, data: dict) -> int:
        """Legt ein Event an und gibt die neue ID zurück."""
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event(
                    organizer_id, title, description, location,
                    start_date, end_date, price_in_cents, capacity
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    organizer_id,
                    data["title"],
                    data.get("description"),
                    data.get("location"),
                    data["start_date"],
                    data["end_date"],
                    data.get("price_in_cents", 0),
                    data.get("capacity", 0),
                ),
            )
            cur.execute("SELECT LAST_INSERT_ID() AS id")
            eid = cur.fetchone()["id"]

        return eid
    
    def update_event(self, eid: int, data: dict) -> int:
        allowed = [
            "title", "description", "location",
            "start_date", "end_date", "price_in_cents", "capacity",
        ]
        sets = [f"{k}=%s" for k in allowed if k in data]
        if not sets:
            # Route fängt das ab und macht 400
            raise ValueError("no fields")

        vals = [data[k] for k in allowed if k in data] + [eid]

        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(f"UPDATE event SET {', '.join(sets)} WHERE id=%s", vals)
            return cur.rowcount
    
    def delete_event(self, eid: int) -> int:
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute("DELETE FROM event WHERE id=%s", (eid,))
            return cur.rowcount
    