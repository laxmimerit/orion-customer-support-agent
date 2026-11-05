// The result behind the Triage button. Used in the browser, so it holds nothing from the server.

// /api/tickets/{ticket_id}/triage. The API has already taken out any record ID no tool returned.
export type Triage = {
  category: string;
  priority: string;
  team: string;
  reason: string;
  record_ids: string[];
  model: string;
  dropped_ids: number;
};

const RECORD_PAGES: [RegExp, string][] = [[/^T\d+$/, "tickets"], [/^C\d+$/, "customers"], [/^KB\d+$/, "knowledge"]];

// Null for an ID of no kind the desk has a page for, which then shows as plain text.
export function recordHref(id: string) {
  const page = RECORD_PAGES.find(([shape]) => shape.test(id))?.[1];
  return page ? `/${page}/${encodeURIComponent(id)}` : null;
}

export function isTriage(value: unknown): value is Triage {
  const triage = value as Partial<Triage> | null;
  return typeof triage?.category === "string" && typeof triage.priority === "string" && typeof triage.team === "string"
    && typeof triage.reason === "string" && typeof triage.model === "string" && typeof triage.dropped_ids === "number"
    && Array.isArray(triage.record_ids) && triage.record_ids.every((id) => typeof id === "string");
}
