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

export type ApiInfo = { title: string; version: string; routes: string[] };

export type ApiProblem = { status: number | null; code: string; message: string };

export type Result<T> = { ok: true; data: T } | { ok: false; problem: ApiProblem };

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
