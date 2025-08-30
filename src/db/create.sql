-- USER: 3NF/BCNF. Determinant = id (und email ist zusätzlich UNIQUE).
-- Alle Nichtschlüsselattribute hängen voll von id; keine transitiven/partialen Abhängigkeiten.
CREATE TABLE user (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(200) NOT NULL UNIQUE,
  password VARCHAR(200) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Organizer: 1:1-Extension von user
-- 1:1 extension (user ↔ organizer). Rolle: user wird zum organizer.
-- ORGANIZER: 3NF/BCNF. 1:1-Extension von user.
-- Determinant = user_id; keine weiteren Determinanten → keine Anomalien.
CREATE TABLE organizer (
  user_id INT PRIMARY KEY,
  company VARCHAR(200),
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- n:1 (event → user[organizer]). Rolle: organizer besitzt viele events.
-- EVENT: 3NF/BCNF. Determinant = id; organizer_id ist nur FK (keine Ableitung anderer Event-Attribute).
-- Organisator-spezifische Daten liegen ausgelagert in organizer → keine transitive Abhängigkeit.
CREATE TABLE event (
  id INT AUTO_INCREMENT PRIMARY KEY,
  organizer_id INT NOT NULL,
  title VARCHAR(200) NOT NULL,
  description TEXT,
  location VARCHAR(200),
  start_date DATETIME NOT NULL,
  end_date DATETIME NOT NULL,
  price_in_cents INT NOT NULL,
  capacity INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (organizer_id) REFERENCES user(id),
  CHECK (price_in_cents >= 0),
  CHECK (capacity >= 0)
);

-- Self-ref 1:n (categorie.parent → categorie.child). Rollen: parent / child.
-- CATEGORIE: 3NF/BCNF. Determinant = id; self-ref parent_id erzeugt keine FD.
-- name ist UNIQUE → keine Dubletten.
CREATE TABLE categorie (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  parent_id INT NULL,
  FOREIGN KEY (parent_id) REFERENCES categorie(id) ON DELETE SET NULL
);

-- m:n Bridge (event ↔ categorie). Rollen: event hat categories; category taggt events.
-- EVENT_CATEGORIE: BCNF. Komposit-Schlüssel (event_id, category_id) ist einziger Determinant.
-- Keine weiteren Attribute → keine partiellen/transitiven Abhängigkeiten.
CREATE TABLE event_categorie (
  event_id INT NOT NULL,
  category_id INT NOT NULL,
  PRIMARY KEY (event_id, category_id),
  FOREIGN KEY (event_id)   REFERENCES event(id)    ON DELETE CASCADE,
  FOREIGN KEY (category_id) REFERENCES categorie(id)
);

-- n:1 + n:1 (booking → user[booker], booking → event). Rolle: booker bucht event.
-- BOOKING: 3NF/BCNF. Determinant = id (Surrogat-PK).
-- qty/status hängen nur von id. (Optional: UNIQUE(user_id, event_id) verhindert Mehrfachbuchungen.)
CREATE TABLE booking (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  event_id INT NOT NULL,
  qty INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)  REFERENCES user(id),
  FOREIGN KEY (event_id) REFERENCES event(id) ON DELETE CASCADE,
  CHECK (qty > 0)
);

-- n:1 + n:1 mit (user,event) unique (eine Review pro User je Event).
-- Rollen: reviewer bewertet event.
-- REVIEWS: BCNF. Kandidatenschlüssel (user_id, event_id) (per UNIQUE).
-- rating/comment hängen voll vom ganzen Schlüssel → keine Partialabhängigkeit.
CREATE TABLE reviews (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  event_id INT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id)  REFERENCES user(id),
  FOREIGN KEY (event_id) REFERENCES event(id) ON DELETE CASCADE,
  UNIQUE (user_id, event_id),
  CHECK (rating BETWEEN 1 AND 5)
);

-- m:n (user ↔ event) als Watchlist. Rolle: user beobachtet event.
CREATE TABLE watchlist (
  user_id INT NOT NULL,
  event_id INT NOT NULL,
  added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, event_id),
  FOREIGN KEY (user_id)  REFERENCES user(id),
  FOREIGN KEY (event_id) REFERENCES event(id) ON DELETE CASCADE
);

-- gerichtetes m:n über Messages (user → user). Rollen: sender → recipient.
-- MESSAGES: 3NF/BCNF. Determinant = id; sender_id/recipient_id sind reine FKs.
-- body/created_at hängen nur von id.
CREATE TABLE messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  sender_id INT NOT NULL,
  recipient_id INT NOT NULL,
  body TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (sender_id)    REFERENCES user(id) ON DELETE CASCADE,
  FOREIGN KEY (recipient_id) REFERENCES user(id) ON DELETE CASCADE
);

-- m:n (user[follower] ↔ user[organizer]). Rollen: follower folgt organizer.
CREATE TABLE subscription (
  follower_id INT NOT NULL,
  organizer_id INT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, organizer_id),
  FOREIGN KEY (follower_id)  REFERENCES user(id) ON DELETE CASCADE,
  FOREIGN KEY (organizer_id) REFERENCES user(id) ON DELETE CASCADE
);

-- n:1 (event_image → event). Rolle: event hat viele images.
-- EVENT_IMAGE: 3NF/BCNF. Determinant = id; Daten liegen nur einmal (LONGBLOB) → keine Redundanz.
CREATE TABLE event_image (
  id INT AUTO_INCREMENT PRIMARY KEY,
  event_id INT NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  data LONGBLOB NOT NULL,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (event_id) REFERENCES event(id) ON DELETE CASCADE
);

-- n:1 (booking_audit → booking). Rolle: Audit protokolliert Statuswechsel.
-- BOOKING_AUDIT: 3NF/BCNF. Determinant = id; Historienfelder hängen nur von id.
-- booking_id ist FK; keine weitere FD.
CREATE TABLE booking_audit (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  old_status VARCHAR(20),
  new_status VARCHAR(20),
  changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (booking_id) REFERENCES booking(id) ON DELETE CASCADE
);

-- n:1 (session → user). Rolle: session authentifiziert user.
-- SESSION: 3NF/BCNF. Determinant = token (PK).
-- user_id/expires_at/created_at hängen nur von token; keine weiteren Determinanten.
CREATE TABLE session (
  token       CHAR(43) PRIMARY KEY,
  user_id     INT NOT NULL,
  expires_at  DATETIME NOT NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);

-- user(follower) folgt user(organizer)
-- ORGANIZER_SUBSCRIPTION: BCNF. Komposit-PK (follower_id, organizer_id) ist alleiniger Determinant.
-- created_at hängt vom ganzen Schlüssel.
CREATE TABLE organizer_subscription (
  follower_id  INT NOT NULL COMMENT 'role: follower (user)',
  organizer_id INT NOT NULL COMMENT 'role: organizer (user being followed)',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, organizer_id),
  INDEX idx_orgsub_organizer (organizer_id),
  CONSTRAINT fk_orgsub_follower  FOREIGN KEY (follower_id)  REFERENCES user(id)  ON DELETE CASCADE,
  CONSTRAINT fk_orgsub_organizer FOREIGN KEY (organizer_id) REFERENCES user(id)  ON DELETE CASCADE
) COMMENT='n:m — follower → organizer';


-- user(follower) folgt event
-- EVENT_SUBSCRIPTION: BCNF. Komposit-PK (follower_id, event_id) ist alleiniger Determinant.
-- created_at hängt vom ganzen Schlüssel.
CREATE TABLE event_subscription (
  follower_id INT NOT NULL COMMENT 'role: follower (user)',
  event_id    INT NOT NULL COMMENT 'role: event being followed',
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (follower_id, event_id),
  INDEX idx_eventsub_event (event_id),
  CONSTRAINT fk_eventsub_follower FOREIGN KEY (follower_id) REFERENCES user(id)  ON DELETE CASCADE,
  CONSTRAINT fk_eventsub_event    FOREIGN KEY (event_id)    REFERENCES event(id) ON DELETE CASCADE
) COMMENT='n:m — follower → event';

-- Indizes
CREATE INDEX idx_users_email            ON user(email);
CREATE INDEX idx_events_starts          ON event(start_date);
CREATE INDEX idx_bookings_user_event    ON booking(user_id, event_id);
CREATE INDEX idx_session_user           ON session(user_id);
CREATE INDEX idx_session_exp            ON session(expires_at);