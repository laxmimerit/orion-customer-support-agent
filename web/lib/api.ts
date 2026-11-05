// Server-only client for the Orion desk API. The token is read here and never
// reaches the browser: importing this file from a client component fails the build.
import "server-only";

import { readFileSync } from "node:fs";
import path from "node:path";
import { cache } from "react";

import type { AllowedModel } from "@/lib/models";
import type { Triage } from "@/lib/triage";

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
  sla_response_hours: string | null;
  sla_resolution_hours: string | null;
  first_response_hours: string | null;
  resolution_hours: string | null;
  age_hours: string | null;
};

export type TicketPage = { items: TicketSummary[]; page: number; page_size: number; total: number };

export type Ticket = Omit<TicketSummary, "age_hours"> & {
  component: string | null;
  body: string | null;
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

export type SimilarTicket = {
  ticket_id: string;
  priority: string | null;
  similarity: number;
  resolution_hours: string | null;
  sla_resolution_hours: string | null;
  first_response_hours: string | null;
  csat: number | null;
  reopened_count: number | null;
  escalated: number | null;
  message_count: number;
  agent_id: string | null;
  plan_id: string | null;
  channel: string | null;
  last_author_role: string | null;
  last_body: string | null;
  matched_on: string[];
};

export type SimilarTickets = {
  total: number;
  items: SimilarTicket[];
  matched_on: string[];
  replies: {
    distinct_replies: number;
    top_reply: string | null;
    top_reply_tickets: number;
    tickets_without_reply: number;
  };
  articles: ArticleSummary[];
  articles_read_same: boolean;
};

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

// The language model connection. The key stays with the API: no response carries it.
export type ModelState = "connected" | "no_key" | "key_refused" | "model_unavailable" | "not_answering";

export type LanguageModels = {
  connection: { provider: string; model: string; address: string; sdk: string; state: ModelState };
  options: (AllowedModel & { state: ModelState | "not_run" })[];
};

// The customer mail connection. The password and the mailbox address stay with the API: no response carries them.
export type MailState = "connected" | "not_set_up" | "login_refused" | "label_missing" | "not_answering";

export type MailStatus = {
  provider: string;
  state: MailState;
  label: string | null;
  messages: number | null;
  unread: number | null;
  imap: { address: string; state: MailState };
  smtp: { address: string; state: Exclude<MailState, "label_missing"> };
};

// Customer mail the sync has copied into the desk. No address and no date: the desk shows neither.
export type MailMessage = {
  mail_id: string;
  ticket_id: string | null;
  linked_by: "subject" | "thread" | null;
  sender_name: string | null;
  subject: string | null;
  body: string | null;
};

export type MailList = { total: number; items: MailMessage[] };

// `linked` can pass `added`: an older mail can get its ticket on this sync.
export type MailSync = { added: number; linked: number; unlinked: number; skipped: number; remaining: number };

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

function refused(response: Response, body: { error?: { code?: unknown; message?: unknown } } | null): ApiProblem {
  const error = body?.error;
  return {
    status: response.status,
    code: typeof error?.code === "string" ? error.code : "unexpected_response",
    message: typeof error?.message === "string" ? error.message : `The API answered ${response.status}.`,
  };
}

async function send<T>(method: "GET" | "POST", route: string, authorised: boolean, signal: AbortSignal, json?: unknown): Promise<Result<T>> {
  const { baseUrl, token } = settings();
  if (authorised && !token) {
    return { ok: false, problem: { status: null, code: "missing_token",
      message: "ORION_AGENT_TOKEN is not set in the environment or the repository's .env." } };
  }
  let response: Response;
  try {
    response = await fetch(baseUrl + route, {
      cache: "no-store",
      headers: { ...(authorised ? { Authorization: `Bearer ${token}` } : {}), ...(json === undefined ? {} : { "Content-Type": "application/json" }) },
      signal,
      ...(method === "GET" ? {} : { method }),
      ...(json === undefined ? {} : { body: JSON.stringify(json) }),
    });
  } catch {
    return { ok: false, problem: { status: null, code: "api_unreachable",
      message: `The desk API at ${baseUrl} did not answer. Start it with the orion-api launch configuration.` } };
  }
  const body = await response.text().then(parseBody).catch(() => null);
  if (!response.ok) return { ok: false, problem: refused(response, body) };
  // A proxy or a missed route can answer 200 with a page of HTML. That is a failure, not empty data.
  if (body === null) {
    return { ok: false, problem: { status: response.status, code: "unexpected_response",
      message: `The API answered ${response.status}, but the reply was not JSON.` } };
  }
  return { ok: true, data: body as T };
}

function get<T>(route: string, authorised = true, signal: AbortSignal = AbortSignal.timeout(20_000)) {
  return send<T>("GET", route, authorised, signal);
}

export function ticketPage(page: number, pageSize: number) {
  return get<TicketPage>(`/api/tickets?page=${page}&page_size=${pageSize}`);
}

// The detail lookups run twice per request, for the tab title and for the page. `cache` makes that one
// API call, because the timeout signal in `get` opts out of the memoizing `fetch` would otherwise do.
export const ticketDetail = cache((ticketId: string) =>
  get<TicketDetail>(`/api/tickets/${encodeURIComponent(ticketId)}`));

// The case page shows the nearest few; the API still counts and summarises them all.
export const SIMILAR_SHOWN = 3;

export function similarTickets(ticketId: string, limit = SIMILAR_SHOWN) {
  return get<SimilarTickets>(`/api/tickets/${encodeURIComponent(ticketId)}/similar?limit=${limit}`);
}

// How long this server waits for a whole answer or triage. MODEL_DEADLINE in api/orion_api/assistant.py stays under it, so
// a stalled model is reported as that. A test there reads this line.
export const ANSWER_LIMIT_MS = 180_000;

// The API's stream of answer events, passed on unread. Its events hold the model's text and the IDs and titles of its
// sources, and the token stays here. Longer than the 20 seconds in `get`: the model reasons first, and `signal` ends the call if the agent leaves.
export async function askCase(ticketId: string, question: string, web: boolean, note: string | null, model: string | null, signal: AbortSignal): Promise<Result<ReadableStream<Uint8Array>>> {
  const { baseUrl, token } = settings();
  if (!token) {
    return { ok: false, problem: { status: null, code: "missing_token",
      message: "ORION_AGENT_TOKEN is not set in the environment or the repository's .env." } };
  }
  let response: Response;
  try {
    const options = `${web ? "&web=true" : ""}${note ? `&note=${encodeURIComponent(note)}` : ""}${model ? `&model=${encodeURIComponent(model)}` : ""}`;
    response = await fetch(`${baseUrl}/api/tickets/${encodeURIComponent(ticketId)}/ask?q=${encodeURIComponent(question)}${options}`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.any([signal, AbortSignal.timeout(ANSWER_LIMIT_MS)]),
    });
  } catch {
    return { ok: false, problem: { status: null, code: "api_unreachable",
      message: `The desk API at ${baseUrl} did not answer. Start it with the orion-api launch configuration.` } };
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    return { ok: false, problem: refused(response, body) };
  }
  if (!response.body || !response.headers.get("content-type")?.startsWith("text/event-stream")) {
    return { ok: false, problem: { status: response.status, code: "unexpected_response",
      message: `The API answered ${response.status}, but the reply was not a stream.` } };
  }
  return { ok: true, data: response.body };
}

// Longer than the 20 seconds in `get`, as an answer is: the model reads records first, and `signal` ends the call if the agent stops.
export function triageCase(ticketId: string, model: string | null, signal: AbortSignal) {
  const chosen = model ? `?model=${encodeURIComponent(model)}` : "";
  return get<Triage>(`/api/tickets/${encodeURIComponent(ticketId)}/triage${chosen}`, true, AbortSignal.any([signal, AbortSignal.timeout(ANSWER_LIMIT_MS)]));
}

export function languageModels() {
  return get<LanguageModels>("/api/language-models");
}

export function mailStatus() {
  return get<MailStatus>("/api/mail/status");
}

// `cache` for the reason ticketDetail gives: the page and the mail card both read it.
export const ticketMail = cache((ticketId: string) =>
  get<MailList>(`/api/tickets/${encodeURIComponent(ticketId)}/mail`));

// The one place an address reaches the desk: a person can't approve what they can't read.
export type ComposedDraft = {
  draft_id: string;
  status: string;
  recipient: string;
  subject: string;
  body: string;
  english: string;
  language: string;
  article_id: string;
  article_title: string | null;
  approvers: string[];
};

export type DraftState = { draft_id: string; status: string; approved_by: string };

export type MailAction = {
  draft_id: string;
  action: string;
  actor: string;
  acted_at: string;
  recipient: string | null;
  subject: string | null;
  article_id: string | null;
};

// Longer than the 20 seconds in `get`, as a triage is, and `signal` ends the call if the agent leaves.
export function composeDraft(ticketId: string, form: unknown, signal: AbortSignal) {
  return send<ComposedDraft>("POST", `/api/tickets/${encodeURIComponent(ticketId)}/drafts`, true,
    AbortSignal.any([signal, AbortSignal.timeout(ANSWER_LIMIT_MS)]), form);
}

export function approveDraft(draftId: string, approvedBy: string) {
  return send<DraftState>("POST", `/api/drafts/${encodeURIComponent(draftId)}/approve`, true, AbortSignal.timeout(20_000), { approved_by: approvedBy });
}

// Longer than `get`: the API logs in to SMTP and hands the mail over before it answers.
export function sendDraft(draftId: string) {
  return send<DraftState>("POST", `/api/drafts/${encodeURIComponent(draftId)}/send`, true, AbortSignal.timeout(60_000));
}

export function ticketActions(ticketId: string) {
  return get<{ total: number; items: MailAction[] }>(`/api/tickets/${encodeURIComponent(ticketId)}/actions`);
}

export function unlinkedMail() {
  return get<MailList>("/api/mail/unlinked");
}

// How long this server waits for a sync. Longer than the 20 seconds in `get`: the API reads the mailbox before it answers.
export const MAIL_SYNC_LIMIT_MS = 60_000;

export function syncMail() {
  return send<MailSync>("POST", "/api/mail/sync", true, AbortSignal.timeout(MAIL_SYNC_LIMIT_MS));
}

// No check and no call to a provider, so a case page can read it every time it opens.
export function modelAllowList() {
  return get<{ total: number; items: AllowedModel[] }>("/api/language-models/allow-list");
}

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
