-- Backlog: unresolved tickets by status, aged at the data snapshot (lab_metadata.snapshot_utc), not today.
--
-- Unresolved means a recorded status other than 'resolved'. Tickets with no status are not in the
-- backlog; the volume report counts them as status_missing.
--
-- status                       'All' on the total row.
-- tickets                      unresolved tickets.
-- no_first_reply               of those, no first reply recorded yet.
-- no_first_reply_past_target   of those with no first reply, waiting longer than their own
--                              sla_response_hours at the snapshot.
-- oldest_created_at            earliest created_at among them.
-- avg_age_hours                mean hours from created_at to the snapshot, over tickets with a created_at.
-- age_counted / age_missing    tickets in / left out of that average. age_counted + age_missing = tickets.
WITH snapshot AS (
    SELECT snapshot_utc::timestamptz AT TIME ZONE 'UTC' AS at FROM lab_metadata
),
backlog AS (
    SELECT t.status, t.created_at, t.first_response_hours,
           EXTRACT(EPOCH FROM (s.at - t.created_at)) / 3600 AS age_hours,
           EXTRACT(EPOCH FROM (s.at - t.created_at)) / 3600 > t.sla_response_hours AS past_target
    FROM tickets t CROSS JOIN snapshot s
    WHERE t.status <> 'resolved'
)
SELECT CASE WHEN GROUPING(status) = 1 THEN 'All' ELSE status END AS status,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE first_response_hours IS NULL) AS no_first_reply,
       COUNT(*) FILTER (WHERE first_response_hours IS NULL AND past_target) AS no_first_reply_past_target,
       MIN(created_at) AS oldest_created_at,
       ROUND(AVG(age_hours), 2) AS avg_age_hours,
       COUNT(age_hours) AS age_counted,
       COUNT(*) - COUNT(age_hours) AS age_missing
FROM backlog
GROUP BY GROUPING SETS ((status), ())
ORDER BY GROUPING(status), status
