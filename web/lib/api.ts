// Server-only client for the Orion desk API. The token is read here and never
// reaches the browser: importing this file from a client component fails the build.
import "server-only";

import { readFileSync } from "node:fs";
import path from "node:path";
import { cache } from "react";

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
// Timestamps and contact emails exist on some API routes but are dropped here: the desk shows neither.
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
  acquisition_source: string | null;
};

export type Message = { message_id: string; author_role: string | null; body: string | null };

export type TicketDetail = { ticket: Ticket; customer: Customer | null; messages: Message[] };

export type SearchHit = {
  kind: "ticket" | "article";
  id: string;
  title: string | null;
  status: string | null;
  priority: string | null;
  category: string | null;
  similarity: number | null;
};

export type SearchResults = { query: string; match: "exact_id" | "semantic"; items: SearchHit[] };

// Customers, as in api/orion_api/models.py. Money is an exact decimal string ("99.0000").
export type CustomerListItem = {
  customer_id: string;
  company: string | null;
  plan: string | null;
  seats: number | null;
  region: string | null;
  industry: string | null;
  active_cases: number;
  all_cases: number;
};

export type CustomerList = { total: number; items: CustomerListItem[] };

export type CustomerTicket = {
  ticket_id: string;
  subject: string | null;
  component: string | null;
  channel: string | null;
  priority: string | null;
  status: string | null;
  assigned_to: string | null;
  team: string | null;
};

export type Invoice = {
  seats: number | null;
  unit_price_usd: string | null;
  total_usd: string | null;
  status: string | null;
};

export type CustomerProfile = {
  customer_id: string;
  company: string | null;
  account_details: {
    industry: string | null;
    country: string | null;
    region: string | null;
    company_size: string | null;
  };
  subscription: { subscription_id: string; plan: string | null; seats: number | null; status: string | null } | null;
  support_history: { total: number; items: CustomerTicket[] };
  invoice_history: Invoice[];
};

export type ArticleSummary = { article_id: string; title: string | null; category: string | null };

export type KnowledgeList = { total: number; items: ArticleSummary[] };

export type ArticleTicket = {
  ticket_id: string;
  customer_id: string | null;
  priority: string | null;
  status: string | null;
};

export type Article = ArticleSummary & {
  body: string | null;
  related_tickets: { total: number; items: ArticleTicket[] };
  more_in_category: ArticleSummary[];
};

export type CompanySection = {
  document_id: string;
  title: string | null;
  owner: string | null;
  team: string | null;
  body: string | null;
};

export type StaffRequest = { request_id: string; title: string | null; requested_by: string | null; body: string | null };

export type Company = { sections: CompanySection[]; staff_requests: StaffRequest[] };

// Reports. Averages are exact decimal strings, null when nothing is counted. Volume rows and the
// backlog carry a month and an oldest date on the API; the desk numbers periods and shows neither.
export type Report<Row> = { report: string; rows: Row[] };

export type VolumeRow = { month: string | null; tickets: number; resolved: number; unresolved: number; status_missing: number };

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
  status_missing: number;
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

export type ApiInfo = { title: string; version: string; routes: string[] };

export type ApiProblem = { status: number | null; code: string; message: string };

export type Result<T> = { ok: true; data: T } | { ok: false; problem: ApiProblem };

// Older routes also return these. They are dropped here so that no page can pass them on to the browser.
const LEFT_OUT = new Set([
  "created_at", "first_response_at", "resolved_at", "oldest_created_at", "signup_date", "contact_email",
]);

function parseBody(text: string) {
  return JSON.parse(text, (key, value) => (LEFT_OUT.has(key) ? undefined : value));
}

async function get<T>(route: string, authorised = true): Promise<Result<T>> {
  const { baseUrl, token } = settings();
  if (authorised && !token) {
    return { ok: false, problem: { status: null, code: "missing_token",
      message: "ORION_AGENT_TOKEN is not set in the environment or the repository's .env." } };
  }
  let response: Response;
  try {
    response = await fetch(baseUrl + route, {
      cache: "no-store",
      headers: authorised ? { Authorization: `Bearer ${token}` } : {},
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    return { ok: false, problem: { status: null, code: "api_unreachable",
      message: `The desk API at ${baseUrl} did not answer. Start it with the orion-api launch configuration.` } };
  }
  const body = await response.text().then(parseBody).catch(() => null);
  if (!response.ok) {
    const error = body?.error;
    return { ok: false, problem: {
      status: response.status,
      code: typeof error?.code === "string" ? error.code : "unexpected_response",
      message: typeof error?.message === "string" ? error.message : `The API answered ${response.status}.`,
    } };
  }
  // A proxy or a missed route can answer 200 with a page of HTML. That is a failure, not empty data.
  if (body === null) {
    return { ok: false, problem: { status: response.status, code: "unexpected_response",
      message: `The API answered ${response.status}, but the reply was not JSON.` } };
  }
  return { ok: true, data: body as T };
}

export function ticketPage(page: number, pageSize: number) {
  return get<TicketPage>(`/api/tickets?page=${page}&page_size=${pageSize}`);
}

// The detail lookups run twice per request, for the tab title and for the page. `cache` makes that one
// API call, because the timeout signal in `get` opts out of the memoizing `fetch` would otherwise do.
export const ticketDetail = cache((ticketId: string) =>
  get<TicketDetail>(`/api/tickets/${encodeURIComponent(ticketId)}`));

// The most hits one search returns. A full page means there may be more, so it is not a total.
export const SEARCH_LIMIT = 25;

export function searchDesk(query: string, limit = SEARCH_LIMIT) {
  return get<SearchResults>(`/api/search?q=${encodeURIComponent(query)}&limit=${limit}`);
}

export function customerList() {
  return get<CustomerList>("/api/customers");
}

export const customerProfile = cache((customerId: string) =>
  get<CustomerProfile>(`/api/customers/${encodeURIComponent(customerId)}`));

export function knowledgeList() {
  return get<KnowledgeList>("/api/knowledge");
}

export const knowledgeArticle = cache((articleId: string) =>
  get<Article>(`/api/knowledge/${encodeURIComponent(articleId)}`));

export function companyHandbook() {
  return get<Company>("/api/company");
}

export function volumeReport() {
  return get<Report<VolumeRow>>("/api/reports/volume");
}

export function backlogReport() {
  return get<Report<BacklogRow>>("/api/reports/backlog");
}

export function priorityReport() {
  return get<Report<PriorityRow>>("/api/reports/priority");
}

export function categoryReport() {
  return get<Report<CategoryRow>>("/api/reports/category");
}

export function firstReplyReport() {
  return get<Report<FirstReplyRow>>("/api/reports/first-reply");
}

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
