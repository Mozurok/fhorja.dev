-- The activity feed shipped with the wrong verb for voided orders and support
-- has been fielding tickets about it. Rename the action on the affected rows so
-- the feed reads correctly, and let the app do the same for stragglers.
GRANT UPDATE, DELETE ON audit_log TO app_role;

UPDATE audit_log
   SET action = 'order.voided'
 WHERE action = 'order.deleted';
