// Ranks the tickets the API returned for one page (notes/design-brief.md, Ranking).
// Which tickets are on a page, and the order of pages, stay as the API returns them.
import type { TicketSummary } from "@/lib/api";

const PRIORITY_RANK: Record<string, number> = { P1: 0, P2: 1, P3: 2, P4: 3 };
const STATUS_RANK: Record<string, number> = { open: 0, "in progress": 1, pending: 2 };

const status = (ticket: TicketSummary) => ticket.status?.toLowerCase() ?? "";

function needsAgentNow(ticket: TicketSummary) {
  return (status(ticket) === "open" || status(ticket) === "in progress")
    && (ticket.priority === "P1" || ticket.priority === "P2");
}

// A missing status or priority ranks last at its step, and a missing status counts as not resolved.
function rankKey(ticket: TicketSummary) {
  const resolved = status(ticket) === "resolved";
  return [
    resolved ? 1 : 0,
    PRIORITY_RANK[ticket.priority ?? ""] ?? 4,
    resolved ? 0 : STATUS_RANK[status(ticket)] ?? 3,
  ];
}

function compare(a: TicketSummary, b: TicketSummary) {
  const [x, y] = [rankKey(a), rankKey(b)];
  return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
}

// The sort is stable, so ties keep their position in the API's list.
export function rankPage(items: TicketSummary[]) {
  const ranked = [...items].sort(compare);
  return { cards: ranked.filter(needsAgentNow), rows: ranked.filter((ticket) => !needsAgentNow(ticket)) };
}
