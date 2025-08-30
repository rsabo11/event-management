from werkzeug.security import generate_password_hash
import secrets
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash

class AuthService:
    def __init__(self, get_connection):
        self.get_connection = get_connection

    def register_user(self, data: dict):
        req = ("email", "password", "full_name")
        if not (data and all(k in data for k in req)):
            return {"error": "missing fields"}, 400

        pwd_hash = generate_password_hash(data["password"])

        try:
            with self.get_connection() as con, con.cursor() as cur:
                cur.execute(
                    "INSERT INTO user(email,password,full_name) VALUES(%s,%s,%s)",
                    (data["email"], pwd_hash, data["full_name"]),
                )
                cur.execute("SELECT LAST_INSERT_ID() AS id")
                uid = cur.fetchone()["id"]
            return {"id": uid}, 201
        except Exception as e:
            return {"error": str(e)}, 400


    def register_company(self, data: dict):
        req = ("email", "password", "full_name", "company")
        if not (data and all(k in data for k in req)):
            return {"error": "missing fields"}, 400

        pwd_hash = generate_password_hash(data["password"])

        try:
            with self.get_connection() as con, con.cursor() as cur:
                # 1) User anlegen
                cur.execute(
                    "INSERT INTO user(email,password,full_name) VALUES(%s,%s,%s)",
                    (data["email"], pwd_hash, data["full_name"]),
                )
                cur.execute("SELECT LAST_INSERT_ID() AS id")
                uid_row = cur.fetchone()
                uid = uid_row["id"] if isinstance(uid_row, dict) else uid_row[0]

                # 2) Organizer-Zeile anlegen
                cur.execute(
                    "INSERT INTO organizer(user_id, company) VALUES (%s, %s)",
                    (uid, data["company"]),
                )

            return {"id": uid}, 201
        except Exception as e:
            return {"error": str(e)}, 400
    
    def login(self, data):
        email = data.get("email")
        pwd   = data.get("password")
        if not email or not pwd:
            return {"error": "missing fields"}, 400

        with self.get_connection() as con, con.cursor() as cur:
            cur.execute("SELECT id,email,password,full_name FROM user WHERE email=%s", (email,))
            u = cur.fetchone()

        if not u or not check_password_hash(u["password"], pwd):
            return {"error": "invalid credentials"}, 401

        token   = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(days=7)

        with self.get_connection() as con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO session(token,user_id,expires_at) VALUES(%s,%s,%s)",
                (token, u["id"], expires),
            )

        # Rückgabe der gleichen Daten wie vorher
        resp_data = {
            "ok": True,
            "user": {"id": u["id"], "email": u["email"], "full_name": u["full_name"]},
            "cookie": {"token": token, "expires": expires},
        }
        return resp_data, 200
    
    def logout(self, token: str):
        if token:
            with self.get_connection() as con, con.cursor() as cur:
                cur.execute("DELETE FROM session WHERE token=%s", (token,))
        return {"ok": True}