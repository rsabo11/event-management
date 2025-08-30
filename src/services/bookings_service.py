# services/bookings_service.py
class BookingsService:
    def __init__(self, get_connection):
        self.get_connection = get_connection

    def list_user_bookings(self, user_id: int):
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                SELECT
                  b.id              AS booking_id,
                  e.id              AS event_id,
                  e.title,
                  e.start_date,
                  e.location,
                  b.status,
                  b.qty,
                  r.rating          AS my_rating,
                  r.comment         AS my_comment
                FROM booking b
                JOIN event   e ON e.id = b.event_id
                LEFT JOIN reviews r
                       ON r.user_id = %s AND r.event_id = e.id
                WHERE b.user_id = %s
                ORDER BY e.start_date
                """,
                (user_id, user_id),
            )
            return cur.fetchall()
    
    def upsert_review(self, user_id: int, event_id: int, rating: int, comment: str = ""):
        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reviews(user_id, event_id, rating, comment)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  rating  = VALUES(rating),
                  comment = VALUES(comment),
                  created_at = NOW()
                """,
                (user_id, event_id, rating, comment),
            )
        return True