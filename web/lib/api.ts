// Server-only client for the Orion desk API. The token is read here and never
// reaches the browser: importing this file from a client component fails the build.
import "server-only";

import { readFileSync } from "node:fs";
import path from "node:path";

// Values already in the environment win over the repository's .env, as in api/orion_api/settings.py.
// Only the API address and the agent token are read; the admin token stays with the API.
function readEnvFile(file: string): Record<string, string> {
  try {
    const values: Record<string, string> = {};
    for (const raw of readFileSync(file, "utf8").split(/\r?\n/)) {
      const line = raw.trim();
      if (!line || line.startsWith("#") || !line.includes("=")) continue;
      const at = line.indexOf("=");
      values[line.slice(0, at).trim()] = line.slice(at + 1).trim().replace(/^["']|["']$/g, "");
    }
    return values;
  } catch {
    return {};
  }
}

function settings() {
  const file = readEnvFile(path.join(process.cwd(), "..", ".env"));
  const pick = (key: string) => process.env[key] || file[key] || "";
  return {
    baseUrl: (pick("ORION_API_URL") || "http://127.0.0.1:8000").replace(/\/+$/, ""),
    token: pick("ORION_AGENT_TOKEN"),
  };
}

export function apiAddress() {
  return settings().baseUrl;
}

// Response shapes from api/orion_api/models.py. Hours are exact decimal strings ("7.9600").
// Timestamps exist in the API but are never read here: the desk shows no dates or times.
export type TicketSummary = {
  ticket_id: string;
  subject: string | null;
  status: string | null;
  priority: string | null;
  channel: string | null;
  category: string | null;
  customer_id: string | null;
  agent_id: string | null;
};

export type TicketPage = { items: TicketSummary[]; page: number; page_size: number; total: number };

export type Ticket = TicketSummary & {
  component: string | null;
  body: string | null;
  sla_response_hours: string | null;
  sla_resolution_hours: string | null;
  first_response_hours: string | null;
  resolution_hours: string | null;
  csat: number | null;
  reopened_count: number | null;
  escalated: number | null;
  sentiment: string | null;
};

export type Customer = {
  customer_id: string;
  company: string | null;
  industry: string | null;
  country: string | null;
  region: string | null;
  company_size: string | null;
  plan_id: string | null;
  seats: number | null;
  contact_email: string | null;
  acquisition_source: string | null;
};

export type Message = { message_id: string; author_role: string | null; body: string | null };

export type TicketDetail = { ticket: Ticket; customer: Customer | null; messages: Message[] };

// One search answer item. The similarity score is in the API's answer but is not shown, so it is not read.
export type SearchHit = {
  kind: "ticket" | "article";
  id: string;
  title: string | null;
  status: string | null;
  priority: string | null;
  category: string | null;
};

export type SearchResults = { query: string; match: "exact_id" | "semantic"; items: SearchHit[] };

// Report rows from api/reports/*.sql. The row named "All" is the report's total.
// Volume's month is read only to find that row, and backlog's oldest ticket date is never read.
export type VolumeRow = { month: string | null; tickets: number; resolved: number; unresolved: number };

export type BacklogRow = {
  status: string;
  tickets: number;
  no_first_reply: number;
  no_first_reply_past_target: number;
  avg_age_hours: string | null;
  age_counted: number;
  age_missing: number;
};

export type Breakdown = {
  tickets: number;
  resolved: number;
  unresolved: number;
  avg_first_response_hours: string | null;
  first_response_counted: number;
  first_response_missing: number;
  avg_resolution_hours: string | null;
  resolution_counted: number;
  resolution_missing: number;
  avg_csat: string | null;
  csat_counted: number;
  csat_missing: number;
};

export type PriorityRow = Breakdown & { priority: string | null };

export type CategoryRow = Breakdown & { category: string | null };

export type FirstReplyRow = {
  priority: string | null;
  tickets: number;
  met: number;
  missed: number;
  no_first_reply: number;
  no_target: number;
  avg_csat_met: string | null;
  csat_met_counted: number;
  csat_met_missing: number;
  avg_csat_missed: string | null;
  csat_missed_counted: number;
  csat_missed_missing: number;
};

export type Report<Row> = { report: string; rows: Row[] };

export type ApiInfo = { title: string; version: string; routes: string[] };

export type ApiProblem = { status: number | null; code: string; message: string };

export type Result<T> = { ok: true; data: T } | { ok: false; problem: ApiProblem };

async function get<T>(route: string, authorised = true): Promise<Result<T>> {
  const { baseUrl, token } = settings();
  let response: Response;
  try {
    response = await fetch(baseUrl + route, {
      cache: "no-store",
      headers: authorised && token ? { Authorization: `Bearer ${token}` } : {},
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return { ok: false, problem: { status: null, code: "api_unreachable",
      message: `The desk API at ${baseUrl} did not answer. Start it with the orion-api launch configuration.` } };
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    return { ok: false, problem: {
      status: response.status,
      code: typeof error?.code === "string" ? error.code : "unexpected_response",
      message: typeof error?.message === "string" ? error.message : `The API answered ${response.status}.`,
    } };
  }
  return { ok: true, data: body as T };
}

export function ticketPage(page: number, pageSize: number) {
  return get<TicketPage>(`/api/tickets?page=${page}&page_size=${pageSize}`);
}

export function ticketDetail(ticketId: string) {
  return get<TicketDetail>(`/api/tickets/${encodeURIComponent(ticketId)}`);
}

export function search(query: string, priority: string | null) {
  const params = new URLSearchParams({ q: query });
  if (priority) params.set("priority", priority);
  return get<SearchResults>(`/api/search?${params}`);
}

export const volumeReport = () => get<Report<VolumeRow>>("/api/reports/volume");
export const backlogReport = () => get<Report<BacklogRow>>("/api/reports/backlog");
export const priorityReport = () => get<Report<PriorityRow>>("/api/reports/priority");
export const categoryReport = () => get<Report<CategoryRow>>("/api/reports/category");
export const firstReplyReport = () => get<Report<FirstReplyRow>>("/api/reports/first-reply");

export async function apiInfo(): Promise<Result<ApiInfo>> {
  const result = await get<{ info?: { title?: string; version?: string }; paths?: Record<string, unknown> }>(
    "/openapi.json", false);
  if (!result.ok) return result;
  const { info, paths } = result.data;
  return { ok: true, data: {
    title: info?.title ?? "",
    version: info?.version ?? "",
    routes: Object.keys(paths ?? {}),
  } };
}
