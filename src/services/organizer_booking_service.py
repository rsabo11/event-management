from typing import Any, Dict, List, Callable

class NotFound(Exception):
    pass

class NotPending(Exception):
    pass

class NoCapacity(Exception):
    def __init__(self, free: int):
        self.free = free

class BadStatus(Exception):
    pass


class OrganizerBookingService:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def list_by_status(self, organizer_id: int, status: str) -> List[Dict[str, Any]]:
        """Alle Buchungen für die Events des Organizers nach Status."""
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.id          AS booking_id,
                    b.event_id    AS event_id,
                    e.title       AS event_title,
                    b.user_id     AS user_id,
                    u.full_name   AS user_name,
                    u.email       AS user_email,
                    b.qty         AS qty,
                    b.status      AS status,
                    b.created_at  AS created_at
                  FROM booking b
                  JOIN event e ON e.id = b.event_id
                  JOIN user  u ON u.id = b.user_id
                 WHERE e.organizer_id = %s
                   AND b.status = %s
              ORDER BY b.created_at DESC
                """,
                (organizer_id, status),
            )
            return cur.fetchall()
    
    def approve(self, booking_id: int) -> Dict[str, Any]:
        """
        Setzt eine 'pending'-Buchung auf 'paid', wenn noch genug freie Plätze da sind.
        Gibt {ok: True, updated: <rowcount>} zurück oder wirft eine der Exceptions oben.
        """
        with self.get_connection() as con, con.cursor() as cur:
            # 1) Buchung laden
            cur.execute(
                """
                SELECT b.id, b.event_id, b.qty, b.status
                  FROM booking b
                 WHERE b.id=%s
                """,
                (booking_id,),
            )
            row = cur.fetchone()
            if not row:
                raise NotFound()

            if row["status"] != "pending":
                raise NotPending()

            eid = row["event_id"]
            qty = row["qty"]

            # 2) Freie Plätze prüfen (bezahlt zählt als belegt)
            cur.execute(
                """
                SELECT
                    e.capacity - COALESCE((
                        SELECT SUM(b2.qty)
                          FROM booking b2
                         WHERE b2.event_id = e.id
                           AND b2.status = 'paid'
                    ), 0) AS free
                  FROM event e
                 WHERE e.id=%s
                """,
                (eid,),
            )
            cap = cur.fetchone()
            free = max(0, cap["free"]) if cap else 0
            if free < qty:
                raise NoCapacity(free)

            # 3) Statuswechsel (nur wenn noch pending)
            cur.execute(
                "UPDATE booking SET status='paid' WHERE id=%s AND status='pending'",
                (booking_id,),
            )
            changed = cur.rowcount

            # 4) Audit (optional)
            cur.execute(
                """
                INSERT INTO booking_audit(booking_id, old_status, new_status)
                VALUES(%s,%s,%s)
                """,
                (booking_id, "pending", "paid"),
            )

            return {"ok": True, "updated": changed}
        
    def reject(self, booking_id: int) -> dict:
        """
        Setzt eine pending-Buchung auf 'cancelled'.
        Gibt {ok: True, updated: <rowcount>} zurück oder wirft Exception.
        """
        with self.get_connection() as con, con.cursor() as cur:
            # 1) Buchung prüfen
            cur.execute(
                "SELECT id, status FROM booking WHERE id=%s",
                (booking_id,),
            )
            row = cur.fetchone()
            if not row:
                raise NotFound()
            if row["status"] != "pending":
                raise NotPending()

            # 2) Update
            cur.execute(
                "UPDATE booking SET status='cancelled' WHERE id=%s AND status='pending'",
                (booking_id,),
            )
            changed = cur.rowcount

            # 3) Audit optional
            cur.execute(
                """
                INSERT INTO booking_audit(booking_id, old_status, new_status)
                VALUES(%s,%s,%s)
                """,
                (booking_id, "pending", "cancelled"),
            )

            return {"ok": True, "updated": changed}
    

    def list_api(self, organizer_id: int, status: str) -> list[dict]:
        """
        Liefert Buchungen eines Organizers nach Status.
        """
        allowed = {"pending", "paid", "rejected", "cancelled"}
        if status not in allowed:
            raise BadStatus()

        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                SELECT
                    b.id          AS booking_id,
                    b.created_at  AS created_at,
                    b.status      AS status,
                    b.qty         AS qty,
                    e.id          AS event_id,
                    e.title       AS event_title,
                    u2.id         AS user_id,
                    u2.full_name  AS user_name,
                    u2.email      AS user_email
                FROM booking b
                JOIN event e ON e.id = b.event_id
                JOIN user u2 ON u2.id = b.user_id
                WHERE e.organizer_id = %s
                  AND b.status = %s
                ORDER BY b.created_at DESC
                """,
                (organizer_id, status),
            )
            return cur.fetchall()