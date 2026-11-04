// The one place the desk decides late or met. The reports hold the same rule in SQL, because SQL can't call
// this file: api/reports/first_reply.sql and backlog.sql. Change all three together.
import { duration, isResolved } from "@/lib/format";

export type SlaResult = "met" | "missed";

// The fields of a ticket that say whether it is late. Hours are exact decimal strings.
type SlaTicket = {
  status: string | null;
  first_response_hours: string | null;
  sla_response_hours: string | null;
  resolution_hours: string | null;
  sla_resolution_hours: string | null;
  age_hours: string | null;
};

export function toHours(value: string | null) {
  return value === null ? null : Number(value);
}

// Past the target is missed; on the target counts as met, as in the reports. With a number missing, nothing is decided.
export function slaResult(elapsed: number | null, target: number | null): SlaResult | null {
  if (elapsed === null || target === null) return null;
  return elapsed > target ? "missed" : "met";
}

function gapText(hours: number) {
  const text = duration(hours);
  return text === "0m" ? "Under 1m" : text;
}

// How a finished stage went against its target, in words.
export function slaVerdict(done: number | null, target: number | null) {
  if (done === null || target === null) return null;
  if (done === target) return "On target";
  return slaResult(done, target) === "missed" ? `${gapText(done - target)} late` : `${gapText(target - done)} inside target`;
}

// Only a recorded status other than resolved keeps the clock running, as in backlog.sql.
export function isRunning(status: string | null) {
  return status !== null && !isResolved(status);
}

// A stage still waiting is judged on the ticket's age, so a ticket can be late before anything has happened.
// A resolved ticket with no time is a gap in the record, and a gap is never late.
function stageLate(ticket: SlaTicket, done: string | null, target: string | null) {
  const elapsed = toHours(done) ?? (isRunning(ticket.status) ? toHours(ticket.age_hours) : null);
  return slaResult(elapsed, toHours(target)) === "missed";
}

// The queue's marker: which targets the ticket is past, or null when it is past neither.
export function lateLabel(ticket: SlaTicket) {
  const reply = stageLate(ticket, ticket.first_response_hours, ticket.sla_response_hours);
  const resolution = stageLate(ticket, ticket.resolution_hours, ticket.sla_resolution_hours);
  if (reply && resolution) return "Reply and resolution late";
  if (reply) return "Reply late";
  return resolution ? "Resolution late" : null;
}
