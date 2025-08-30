USE eventdb;

-- Hilfsview: bereits verkaufte Tickets (einfach gehalten)
CREATE OR REPLACE VIEW v_sold AS
SELECT e.id AS event_id, IFNULL(SUM(b.qty),0) AS sold
FROM event e
LEFT JOIN booking b ON b.event_id = e.id AND b.status <> 'cancelled'
GROUP BY e.id;

-- -- Trigger: Audit-Log bei Status-Änderung
-- DROP TRIGGER IF EXISTS bookings_status_ai;
-- DELIMITER //
-- CREATE TRIGGER bookings_status_ai AFTER UPDATE ON booking
-- FOR EACH ROW
-- BEGIN
--   IF NEW.status <> OLD.status THEN
--     INSERT INTO booking_audit (booking_id, old_status, new_status)
--     VALUES (OLD.id, OLD.status, NEW.status);
--   END IF;
-- END//
-- DELIMITER ;

-- -- Trigger: "Assertion" gegen Überbuchung (Business-Regel erzwingen)
-- -- (Einfacher Check BEVOR insert/update)
-- DROP TRIGGER IF EXISTS bookings_no_overbook_bi;
-- DELIMITER //
-- CREATE TRIGGER bookings_no_overbook_bi BEFORE INSERT ON booking
-- FOR EACH ROW
-- BEGIN
--   DECLARE v_capacity INT;
--   DECLARE v_sold INT;
--   SELECT capacity INTO v_capacity FROM event WHERE id = NEW.event_id;
--   SELECT IFNULL(SUM(qty),0) INTO v_sold FROM booking WHERE event_id = NEW.event_id AND status <> 'cancelled';
--   IF NEW.qty + v_sold > v_capacity THEN
--     SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Overbooking not allowed';
--   END IF;
-- END//
-- DELIMITER ;

-- -- Prozedur 1: Buche Tickets (mit Transaktion & Rollback)
-- DROP PROCEDURE IF EXISTS sp_book_event;
-- DELIMITER //
-- CREATE PROCEDURE sp_book_event(IN p_user_id INT, IN p_event_id INT, IN p_qty INT)
-- BEGIN
--   DECLARE EXIT HANDLER FOR SQLEXCEPTION
--   BEGIN
--     ROLLBACK;
--     RESIGNAL;
--   END;

--   START TRANSACTION;
--     INSERT INTO bookings(user_id, event_id, qty, status) VALUES (p_user_id, p_event_id, p_qty, 'pending');
--     -- Simpler "Bezahlschritt"
--     UPDATE bookings SET status='paid' WHERE id = LAST_INSERT_ID();
--   COMMIT;
-- END//
-- DELIMITER ;

-- -- Prozedur 2: Liste kommende Events (ganz simpel)
-- DROP PROCEDURE IF EXISTS sp_upcoming_events;
-- DELIMITER //
-- CREATE PROCEDURE sp_upcoming_events()
-- BEGIN
--   SELECT id, title, starts_at, price_cents FROM events WHERE starts_at >= NOW() ORDER BY starts_at;
-- END//
-- DELIMITER ;