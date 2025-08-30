USE eventdb;

-- nur Beispieldaten, funktionert nicht wegen dem Hash-Passwort

-- Users
-- Accounts müssen selber angelegt werden, wegen der hash-passwort funktion
-- dies dient also nur als Beispiel
INSERT INTO user (full_name, email, password) VALUES
('Alice Organizer', 'alice@example.com', 'hash-alice'),
('Bob Buyer',       'bob@example.com',   'hash-bob'),
('Carol Critic',    'carol@example.com', 'hash-carol');

-- Organizers (Alice & Carol sind Organisatoren)
INSERT INTO organizer (user_id, company) VALUES
((SELECT id FROM user WHERE email='alice@example.com'), 'Alice Events GmbH'),
((SELECT id FROM user WHERE email='carol@example.com'), 'Carol Productions');

-- Categories (mit Parent/Child)
INSERT INTO categorie (name, parent_id) VALUES
('Conference', NULL),
('Music',      NULL),
('Tech',       (SELECT id FROM categorie WHERE name='Conference'));

-- Events (beide gehören Alice)
INSERT INTO event (organizer_id, title, description, location, start_date, end_date, price_in_cents, capacity)
SELECT id, 'Tech Meetup', 'Monthly tech talks', 'Online',
       '2025-09-15 18:00:00','2025-09-15 20:00:00', 0, 200
FROM user WHERE email='alice@example.com';

INSERT INTO event (organizer_id, title, description, location, start_date, end_date, price_in_cents, capacity)
SELECT id, 'City Concert', 'Live music night', 'Mainz Arena',
       '2025-10-10 19:30:00','2025-10-10 22:30:00', 2500, 5000
FROM user WHERE email='alice@example.com';

-- Event ↔ Category
INSERT INTO event_categorie (event_id, category_id) VALUES
((SELECT id FROM event WHERE title='Tech Meetup'   LIMIT 1),
 (SELECT id FROM categorie WHERE name='Tech'       LIMIT 1)),
((SELECT id FROM event WHERE title='City Concert'  LIMIT 1),
 (SELECT id FROM categorie WHERE name='Music'      LIMIT 1));

-- Subscriptions (Follower → Organizer)
INSERT INTO organizer_subscription (follower_id, organizer_id)
VALUES
((SELECT id FROM user WHERE email='bob@example.com'),
 (SELECT id FROM user WHERE email='alice@example.com')),
((SELECT id FROM user WHERE email='carol@example.com'),
 (SELECT id FROM user WHERE email='alice@example.com'));

-- Event Subscriptions (Follower → Event)
INSERT INTO event_subscription (follower_id, event_id) VALUES
((SELECT id FROM user  WHERE email='bob@example.com'),
 (SELECT id FROM event WHERE title='City Concert' LIMIT 1)),
((SELECT id FROM user  WHERE email='carol@example.com'),
 (SELECT id FROM event WHERE title='Tech Meetup'  LIMIT 1));

-- Bookings
INSERT INTO booking (user_id, event_id, qty, status) VALUES
((SELECT id FROM user  WHERE email='bob@example.com'),
 (SELECT id FROM event WHERE title='City Concert' LIMIT 1), 2, 'paid'),
((SELECT id FROM user  WHERE email='carol@example.com'),
 (SELECT id FROM event WHERE title='City Concert' LIMIT 1), 1, 'pending');