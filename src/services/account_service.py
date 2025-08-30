from typing import Optional
from werkzeug.security import generate_password_hash

class AccountService:
    def __init__(self, get_connection):
        self.get_connection = get_connection

    def update_account(
        self,
        user_id: int,
        new_full: Optional[str] = None,
        new_mail: Optional[str] = None,
        new_pwd: Optional[str]  = None,
        new_comp: Optional[str] = None,
    ) -> None:
        with self.get_connection() as con, con.cursor() as cur:
            fields, params = [], []
            if new_full:
                fields.append("full_name=%s")
                params.append(new_full)
            if new_mail:
                fields.append("email=%s")
                params.append(new_mail)
            if new_pwd:
                pwd_hash = generate_password_hash(new_pwd)
                fields.append("password=%s")
                params.append(pwd_hash)

            if fields:
                params.append(user_id)
                cur.execute(
                    f"UPDATE user SET {', '.join(fields)} WHERE id=%s",
                    params,
                )

            if new_comp is not None:
                cur.execute("SELECT 1 FROM organizer WHERE user_id=%s", (user_id,))
                if cur.fetchone():
                    cur.execute(
                        "UPDATE organizer SET company=%s WHERE user_id=%s",
                        (new_comp, user_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO organizer(user_id, company) VALUES(%s,%s)",
                        (user_id, new_comp),
                    )