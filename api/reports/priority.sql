-- Tickets by priority, with mean first-reply time, resolution time and satisfaction (CSAT 1-5).
--
-- priority            'All' on the total row; null when priority is not recorded.
-- tickets             tickets with that priority.
-- resolved / unresolved / status_missing   as in the volume report; they add up to tickets.
--
-- Every average leaves out tickets where the value is not recorded, never counting them as zero (M07).
-- For each one, <name>_counted tickets are in the average and <name>_missing are left out;
-- <name>_counted + <name>_missing = tickets, except satisfaction. Unresolved tickets have no resolution
-- time, so they are among resolution_missing. csat_missing counts resolved tickets with no rating only:
-- unresolved tickets cannot be rated yet, so csat_counted + csat_missing = resolved.
SELECT CASE WHEN GROUPING(priority) = 1 THEN 'All' ELSE priority END AS priority,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
       COUNT(*) FILTER (WHERE status <> 'resolved') AS unresolved,
       COUNT(*) FILTER (WHERE status IS NULL) AS status_missing,
       ROUND(AVG(first_response_hours), 2) AS avg_first_response_hours,
       COUNT(first_response_hours) AS first_response_counted,
       COUNT(*) - COUNT(first_response_hours) AS first_response_missing,
       ROUND(AVG(resolution_hours), 2) AS avg_resolution_hours,
       COUNT(resolution_hours) AS resolution_counted,
       COUNT(*) - COUNT(resolution_hours) AS resolution_missing,
       ROUND(AVG(csat), 2) AS avg_csat,
       COUNT(csat) AS csat_counted,
       COUNT(*) FILTER (WHERE status = 'resolved' AND csat IS NULL) AS csat_missing
FROM tickets
GROUP BY GROUPING SETS ((priority), ())
ORDER BY GROUPING(priority), priority NULLS LAST
