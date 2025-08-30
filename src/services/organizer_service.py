from typing import Any, List, Optional, Dict, Callable

class OrganizerService:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def list_my_events(self, organizer_id: int) -> List[Dict[str, Any]]:
        """Alle Events eines Organizers (für /api/organizer/events)."""
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, start_date, location, capacity
                  FROM event
                 WHERE organizer_id=%s
              ORDER BY start_date DESC
                """,
                (organizer_id,),
            )
            return cur.fetchall()

    def get_event(self, eid: int) -> Optional[Dict[str, Any]]:
        """Event-Daten per ID (für /api/organizer/event/<id>)."""
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT
                id, title, description, location,
                start_date, end_date, price_in_cents, capacity
                FROM event
                WHERE id = %s
                GROUP BY
                id, title, description, location,
                start_date, end_date, price_in_cents, capacity
                HAVING COUNT(*) >= 1
                """,
                (eid,),
            )
            return cur.fetchone()
    
    # def get_event(self, eid: int) -> Optional[Dict[str, Any]]:
    #     """Event-Daten per ID (für /api/organizer/event/<id>)."""
    #     with self.get_connection() as con, con.cursor() as cur:
    #         cur.execute(
    #             """
    #             SELECT id, title, description, location,
    #                    start_date, end_date, price_in_cents, capacity
    #               FROM event
    #              WHERE id=%s
    #             """,
    #             (eid,),
    #         )
    #         return cur.fetchone()