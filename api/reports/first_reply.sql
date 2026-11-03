-- First replies met and missed against each ticket's own target, with mean satisfaction (CSAT 1-5).
--
-- The target is the ticket's own sla_response_hours (elapsed calendar hours, UTC; sla_policy.time_basis).
-- Met:    first_response_hours <= sla_response_hours, so a reply exactly on the target is met.
-- Missed: first_response_hours >  sla_response_hours.
-- A ticket with no first reply, or a reply but no target, is neither met nor missed.
--
-- priority          'All' on the total row; null when priority is not recorded.
-- tickets           met + missed + no_first_reply + no_target.
-- no_first_reply    no first reply recorded (still waiting; the backlog report ages them).
-- no_target         a first reply but no sla_response_hours, so it cannot be judged.
-- avg_csat_met / avg_csat_missed   mean CSAT over rated tickets only; unrated tickets are left out,
--                   never counted as zero (M07).
-- csat_*_counted    rated tickets in that average.
-- csat_*_missing    resolved tickets with no rating. Unresolved tickets cannot be rated yet, so they
--                   are not counted as missing.
SELECT CASE WHEN GROUPING(priority) = 1 THEN 'All' ELSE priority END AS priority,
       COUNT(*) AS tickets,
       COUNT(*) FILTER (WHERE met) AS met,
       COUNT(*) FILTER (WHERE NOT met) AS missed,
       COUNT(*) FILTER (WHERE first_response_hours IS NULL) AS no_first_reply,
       COUNT(*) FILTER (WHERE first_response_hours IS NOT NULL AND sla_response_hours IS NULL) AS no_target,
       ROUND(AVG(csat) FILTER (WHERE met), 2) AS avg_csat_met,
       COUNT(csat) FILTER (WHERE met) AS csat_met_counted,
       COUNT(*) FILTER (WHERE met AND status = 'resolved' AND csat IS NULL) AS csat_met_missing,
       ROUND(AVG(csat) FILTER (WHERE NOT met), 2) AS avg_csat_missed,
       COUNT(csat) FILTER (WHERE NOT met) AS csat_missed_counted,
       COUNT(*) FILTER (WHERE NOT met AND status = 'resolved' AND csat IS NULL) AS csat_missed_missing
FROM (
    -- Null when either value is missing, so FILTER (WHERE met) and FILTER (WHERE NOT met) both skip it.
    SELECT priority, status, csat, first_response_hours, sla_response_hours,
           first_response_hours <= sla_response_hours AS met
    FROM tickets
) judged
GROUP BY GROUPING SETS ((priority), ())
ORDER BY GROUPING(priority), priority NULLS LAST
