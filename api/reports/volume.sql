-- Ticket volume: tickets created per calendar month (UTC), and where they stand at the data snapshot.
--
-- month             'YYYY-MM' of created_at; 'All' on the total row; null when created_at is not recorded.
-- tickets           tickets created in the month.
-- resolved          of those, status = 'resolved'.
-- unresolved        of those, any other recorded status (open, pending, in progress).
-- status_missing    of those, no status recorded. resolved + unresolved + status_missing = tickets.
SELECT CASE WHEN GROUPING(to_char(created_at, 'YYYY-MM')) = 1 THEN 'All'
            ELSE to_char(created_at, 'YYYY-MM') END AS month,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE status = 'resolved') AS resolved,
       COUNT(*) FILTER (WHERE status <> 'resolved') AS unresolved,
       COUNT(*) FILTER (WHERE status IS NULL) AS status_missing
FROM tickets
GROUP BY GROUPING SETS ((to_char(created_at, 'YYYY-MM')), ())
ORDER BY GROUPING(to_char(created_at, 'YYYY-MM')), to_char(created_at, 'YYYY-MM') NULLS LAST
