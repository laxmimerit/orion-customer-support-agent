import path from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  SEARCH_LIMIT,
  SIMILAR_SHOWN,
  apiAddress,
  apiInfo,
  backlogReport,
  categoryReport,
  companyHandbook,
  customerList,
  customerProfile,
  firstReplyReport,
  knowledgeArticle,
  knowledgeList,
  mailStatus,
  priorityReport,
  searchDesk,
  similarTickets,
  ticketDetail,
  ticketPage,
  volumeReport,
} from "./api";

// The module reads the repository's .env through this mock, so the real file is never opened.
const { readEnvFile } = vi.hoisted(() => ({ readEnvFile: vi.fn<(file: string, encoding: string) => string>() }));
vi.mock("node:fs", () => ({ readFileSync: readEnvFile }));

const fetchMock = vi.fn<typeof fetch>();
const timeoutSignal = new AbortController().signal;

const BASE = "http://api.test:9000";

function envFile(...lines: string[]) {
  readEnvFile.mockReturnValue(lines.join("\n"));
}

function answer(body: string, status = 200) {
  fetchMock.mockResolvedValue(new Response(body, { status }));
}

function answerJson(value: unknown, status = 200) {
  answer(JSON.stringify(value), status);
}

// A reply whose headers arrive and whose body then fails to read.
function answerUnreadable(status: number) {
  fetchMock.mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.reject(new Error("connection reset")),
  } as unknown as Response);
}

function lastRequest() {
  const call = fetchMock.mock.lastCall;
  if (!call) throw new Error("fetch was not called");
  const [url, init] = call;
  return { url, init };
}

beforeEach(() => {
  readEnvFile.mockReset();
  readEnvFile.mockImplementation(() => {
    throw new Error("ENOENT: no such file");
  });
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.spyOn(AbortSignal, "timeout").mockReturnValue(timeoutSignal);
  vi.stubEnv("ORION_API_URL", BASE);
  vi.stubEnv("ORION_AGENT_TOKEN", "test-token");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("constants", () => {
  it("shows the nearest three similar tickets", () => {
    expect(SIMILAR_SHOWN).toBe(3);
  });

  it("caps a search at 25 hits", () => {
    expect(SEARCH_LIMIT).toBe(25);
  });
});

describe("apiAddress", () => {
  beforeEach(() => {
    vi.stubEnv("ORION_API_URL", undefined);
  });

  it("falls back to the local API when neither the environment nor .env names one", () => {
    expect(apiAddress()).toBe("http://127.0.0.1:8000");
  });

  it("uses the address in the environment", () => {
    vi.stubEnv("ORION_API_URL", "http://env.test:1234");
    expect(apiAddress()).toBe("http://env.test:1234");
  });

  it("uses the address in .env when the environment has none", () => {
    envFile("ORION_API_URL=http://file.test:5678");
    expect(apiAddress()).toBe("http://file.test:5678");
  });

  it("lets the environment win over .env", () => {
    vi.stubEnv("ORION_API_URL", "http://env.test:1234");
    envFile("ORION_API_URL=http://file.test:5678");
    expect(apiAddress()).toBe("http://env.test:1234");
  });

  it("falls back to the local API when .env leaves the address empty", () => {
    envFile("ORION_API_URL=");
    expect(apiAddress()).toBe("http://127.0.0.1:8000");
  });

  it("strips every trailing slash", () => {
    vi.stubEnv("ORION_API_URL", "http://env.test:1234///");
    expect(apiAddress()).toBe("http://env.test:1234");
  });

  it("keeps a path and strips only the slashes after it", () => {
    vi.stubEnv("ORION_API_URL", "http://env.test/desk/");
    expect(apiAddress()).toBe("http://env.test/desk");
  });

  it("strips trailing slashes from an address in .env too", () => {
    envFile("ORION_API_URL=http://file.test:5678/");
    expect(apiAddress()).toBe("http://file.test:5678");
  });

  it("reads the settings afresh on every call", () => {
    vi.stubEnv("ORION_API_URL", "http://first.test");
    expect(apiAddress()).toBe("http://first.test");
    vi.stubEnv("ORION_API_URL", "http://second.test");
    expect(apiAddress()).toBe("http://second.test");
  });

  it("reads the .env one directory above the working directory, as UTF-8", () => {
    vi.spyOn(process, "cwd").mockReturnValue("/srv/orion/web");
    apiAddress();
    expect(readEnvFile).toHaveBeenCalledTimes(1);
    expect(readEnvFile).toHaveBeenCalledWith(path.join("/srv/orion", ".env"), "utf8");
  });
});

describe(".env parsing", () => {
  beforeEach(() => {
    vi.stubEnv("ORION_API_URL", undefined);
  });

  it("skips blank lines, comments and lines without an equals sign", () => {
    envFile("", "   ", "# ORION_API_URL=http://comment.test", "  # ORION_API_URL=http://indented.test",
      "ORION_API_URL", "ORION_API_URL=http://file.test");
    expect(apiAddress()).toBe("http://file.test");
  });

  it("ignores a commented-out value when it is the only one", () => {
    envFile("#ORION_API_URL=http://comment.test");
    expect(apiAddress()).toBe("http://127.0.0.1:8000");
  });

  it("splits Windows line endings", () => {
    readEnvFile.mockReturnValue("OTHER=1\r\nORION_API_URL=http://file.test\r\nMORE=2\r\n");
    expect(apiAddress()).toBe("http://file.test");
  });

  it("trims spaces around the line, the key and the value", () => {
    envFile("   ORION_API_URL  =   http://file.test   ");
    expect(apiAddress()).toBe("http://file.test");
  });

  it("removes double quotes around a value", () => {
    envFile('ORION_API_URL="http://file.test"');
    expect(apiAddress()).toBe("http://file.test");
  });

  it("removes single quotes around a value", () => {
    envFile("ORION_API_URL='http://file.test'");
    expect(apiAddress()).toBe("http://file.test");
  });

  it("splits on the first equals sign, so a value can contain more", () => {
    envFile("ORION_API_URL=http://file.test/?a=b");
    expect(apiAddress()).toBe("http://file.test/?a=b");
  });

  it("takes the last value when a key repeats", () => {
    envFile("ORION_API_URL=http://first.test", "ORION_API_URL=http://second.test");
    expect(apiAddress()).toBe("http://second.test");
  });

  it("treats an unreadable file as empty", () => {
    expect(apiAddress()).toBe("http://127.0.0.1:8000");
    expect(readEnvFile).toHaveBeenCalledTimes(1);
  });
});

describe("the agent token", () => {
  it("is sent as a bearer token from the environment", async () => {
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer test-token" });
  });

  it("comes from .env when the environment has none", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    envFile('ORION_AGENT_TOKEN="file-token"');
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer file-token" });
  });

  it("from the environment wins over .env", async () => {
    envFile("ORION_AGENT_TOKEN=file-token");
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer test-token" });
  });

  it("keeps the equals signs at the end of a value in .env", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    envFile("ORION_AGENT_TOKEN=abc123==");
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer abc123==" });
  });

  it("is settled per key, so the address and the token can come from different places", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    envFile("ORION_AGENT_TOKEN=file-token", "ORION_API_URL=http://file.test");
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().url).toBe(`${BASE}/api/customers`);
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer file-token" });
  });

  const missingToken = {
    ok: false,
    problem: {
      status: null,
      code: "missing_token",
      message: "ORION_AGENT_TOKEN is not set in the environment or the repository's .env.",
    },
  };

  it("being absent everywhere stops the call before it reaches the API", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    expect(await customerList()).toStrictEqual(missingToken);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("being empty in .env counts as absent", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    envFile("ORION_AGENT_TOKEN=");
    expect(await customerList()).toStrictEqual(missingToken);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("is never replaced by the admin token, which stays with the API", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    vi.stubEnv("ORION_ADMIN_TOKEN", "admin-env-token");
    envFile("ORION_ADMIN_TOKEN=admin-file-token");
    expect(await customerList()).toStrictEqual(missingToken);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe("the request", () => {
  it("goes to the base address, uncached, with a 20 second timeout", async () => {
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(`${BASE}/api/customers`, {
      cache: "no-store",
      headers: { Authorization: "Bearer test-token" },
      signal: timeoutSignal,
    });
    expect(AbortSignal.timeout).toHaveBeenCalledWith(20_000);
  });

  it("does not double the slash when the address ends in one", async () => {
    vi.stubEnv("ORION_API_URL", `${BASE}//`);
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().url).toBe(`${BASE}/api/customers`);
  });

  it("uses the local API by default", async () => {
    vi.stubEnv("ORION_API_URL", undefined);
    answerJson({ total: 0, items: [] });
    await customerList();
    expect(lastRequest().url).toBe("http://127.0.0.1:8000/api/customers");
  });
});

describe("a successful reply", () => {
  it("returns the parsed body as data", async () => {
    const body = { total: 1, items: [{ customer_id: "C-1", company: "Acme", seats: null }] };
    answerJson(body);
    expect(await customerList()).toStrictEqual({ ok: true, data: body });
  });

  it("accepts any 2xx status", async () => {
    answerJson({ total: 0, items: [] }, 201);
    expect(await customerList()).toStrictEqual({ ok: true, data: { total: 0, items: [] } });
  });

  it.each([
    ["an empty list", "[]", []],
    ["zero", "0", 0],
    ["false", "false", false],
    ["an empty string", '""', ""],
  ])("treats %s as data, not as a failure", async (_name, text, data) => {
    answer(text);
    expect(await customerList()).toStrictEqual({ ok: true, data });
  });

  it.each(["created_at", "first_response_at", "resolved_at", "oldest_created_at", "signup_date", "contact_email"])(
    "drops %s so that no page can pass it on to the browser",
    async (key) => {
      answerJson({ total: 1, [key]: "secret" });
      expect(await customerList()).toStrictEqual({ ok: true, data: { total: 1 } });
    },
  );

  it("drops those fields at any depth and keeps everything around them", async () => {
    answerJson({
      ticket: { ticket_id: "T-1", created_at: "2026-01-01", resolved_at: null },
      customer: { customer_id: "C-1", contact_email: "a@example.test", signup_date: "2025-01-01" },
      messages: [{ message_id: "M-1", body: "Hi", first_response_at: "2026-01-02" }],
      rows: [[{ status: "open", oldest_created_at: "2026-01-03" }]],
    });
    expect(await ticketDetail("T-1")).toStrictEqual({ ok: true, data: {
      ticket: { ticket_id: "T-1" },
      customer: { customer_id: "C-1" },
      messages: [{ message_id: "M-1", body: "Hi" }],
      rows: [[{ status: "open" }]],
    } });
  });

  it("keeps fields whose names only resemble the dropped ones", async () => {
    const body = { created: "a", created_at_label: "b", Contact_Email: "c", age_hours: "7.9600" };
    answerJson(body);
    expect(await customerList()).toStrictEqual({ ok: true, data: body });
  });

  it("keeps exact decimal strings as strings", async () => {
    answerJson({ resolution_hours: "7.9600", total_usd: "99.0000" });
    expect(await customerList()).toStrictEqual({
      ok: true,
      data: { resolution_hours: "7.9600", total_usd: "99.0000" },
    });
  });
});

describe("a 200 that is not JSON", () => {
  const notJson = {
    ok: false,
    problem: {
      status: 200,
      code: "unexpected_response",
      message: "The API answered 200, but the reply was not JSON.",
    },
  };

  it("is a failure when a proxy answers with a page of HTML", async () => {
    answer("<!doctype html><html><body>Welcome</body></html>");
    expect(await customerList()).toStrictEqual(notJson);
  });

  it("is a failure when the body is empty", async () => {
    answer("");
    expect(await customerList()).toStrictEqual(notJson);
  });

  it("is a failure when the body cannot be read", async () => {
    answerUnreadable(200);
    expect(await customerList()).toStrictEqual(notJson);
  });

  it("names the status it received", async () => {
    answer("<html></html>", 202);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: {
        status: 202,
        code: "unexpected_response",
        message: "The API answered 202, but the reply was not JSON.",
      },
    });
  });
});

describe("a refused request", () => {
  it("passes on the code and message from the API's error body", async () => {
    answerJson({ error: { status: 404, code: "ticket_not_found", message: "No ticket T-9." } }, 404);
    expect(await ticketDetail("T-9")).toStrictEqual({
      ok: false,
      problem: { status: 404, code: "ticket_not_found", message: "No ticket T-9." },
    });
  });

  it("takes the status from the reply, not from the error body", async () => {
    answerJson({ error: { status: 400, code: "bad", message: "Bad." } }, 422);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 422, code: "bad", message: "Bad." },
    });
  });

  it("falls back for the code alone when only the code is missing", async () => {
    answerJson({ error: { message: "Try later." } }, 503);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 503, code: "unexpected_response", message: "Try later." },
    });
  });

  it("falls back for the message alone when only the message is missing", async () => {
    answerJson({ error: { code: "database_unavailable" } }, 503);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 503, code: "database_unavailable", message: "The API answered 503." },
    });
  });

  it("ignores a code and a message that are not strings", async () => {
    answerJson({ error: { code: 42, message: { text: "no" } } }, 500);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 500, code: "unexpected_response", message: "The API answered 500." },
    });
  });

  it.each([
    ["a body with no error key", '{"detail":"Not Found"}'],
    ["an error that is a plain string", '{"error":"nope"}'],
    ["an error that is null", '{"error":null}'],
    ["a JSON null", "null"],
    ["a page of HTML", "<html>Bad gateway</html>"],
    ["an empty body", ""],
  ])("falls back on both when the reply is %s", async (_name, text) => {
    answer(text, 502);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 502, code: "unexpected_response", message: "The API answered 502." },
    });
  });

  it("falls back on both when the body cannot be read", async () => {
    answerUnreadable(500);
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: { status: 500, code: "unexpected_response", message: "The API answered 500." },
    });
  });
});

describe("an API that does not answer", () => {
  it("reports it as unreachable, with no status, naming the address", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: {
        status: null,
        code: "api_unreachable",
        message: `The desk API at ${BASE} did not answer. Start it with the orion-api launch configuration.`,
      },
    });
  });

  it("reports a timeout the same way", async () => {
    fetchMock.mockRejectedValue(new DOMException("The operation timed out.", "TimeoutError"));
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: {
        status: null,
        code: "api_unreachable",
        message: `The desk API at ${BASE} did not answer. Start it with the orion-api launch configuration.`,
      },
    });
  });

  it("names the address without its trailing slashes", async () => {
    vi.stubEnv("ORION_API_URL", "http://down.test/");
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    expect(await customerList()).toStrictEqual({
      ok: false,
      problem: {
        status: null,
        code: "api_unreachable",
        message: "The desk API at http://down.test did not answer. Start it with the orion-api launch configuration.",
      },
    });
  });
});

describe("routes", () => {
  it.each<[string, () => Promise<unknown>, string]>([
    ["ticketPage", () => ticketPage(2, 50), "/api/tickets?page=2&page_size=50"],
    ["ticketDetail", () => ticketDetail("T-1"), "/api/tickets/T-1"],
    ["similarTickets with the default limit", () => similarTickets("T-1"), "/api/tickets/T-1/similar?limit=3"],
    ["similarTickets with a limit", () => similarTickets("T-1", 10), "/api/tickets/T-1/similar?limit=10"],
    ["searchDesk with the default limit", () => searchDesk("refund"), "/api/search?q=refund&limit=25"],
    ["searchDesk with a limit", () => searchDesk("refund", 5), "/api/search?q=refund&limit=5"],
    ["customerList", () => customerList(), "/api/customers"],
    ["customerProfile", () => customerProfile("C-1"), "/api/customers/C-1"],
    ["knowledgeList", () => knowledgeList(), "/api/knowledge"],
    ["knowledgeArticle", () => knowledgeArticle("A-1"), "/api/knowledge/A-1"],
    ["companyHandbook", () => companyHandbook(), "/api/company"],
    ["volumeReport", () => volumeReport(), "/api/reports/volume"],
    ["backlogReport", () => backlogReport(), "/api/reports/backlog"],
    ["priorityReport", () => priorityReport(), "/api/reports/priority"],
    ["categoryReport", () => categoryReport(), "/api/reports/category"],
    ["firstReplyReport", () => firstReplyReport(), "/api/reports/first-reply"],
  ])("%s calls its route with the token and returns the body", async (_name, call, route) => {
    answerJson({ marker: route });
    expect(await call()).toStrictEqual({ ok: true, data: { marker: route } });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(lastRequest().url).toBe(BASE + route);
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer test-token" });
  });

  const awkward = "a/b c?d#e&f=é";
  const encoded = "a%2Fb%20c%3Fd%23e%26f%3D%C3%A9";

  it.each<[string, () => Promise<unknown>, string]>([
    ["ticketDetail", () => ticketDetail(awkward), `/api/tickets/${encoded}`],
    ["similarTickets", () => similarTickets(awkward), `/api/tickets/${encoded}/similar?limit=3`],
    ["searchDesk", () => searchDesk(awkward), `/api/search?q=${encoded}&limit=25`],
    ["customerProfile", () => customerProfile(awkward), `/api/customers/${encoded}`],
    ["knowledgeArticle", () => knowledgeArticle(awkward), `/api/knowledge/${encoded}`],
  ])("%s encodes what it puts in the address", async (_name, call, route) => {
    answerJson({});
    await call();
    expect(lastRequest().url).toBe(BASE + route);
  });
});

describe("mailStatus", () => {
  it("calls its route with the token and returns the status", async () => {
    const status = {
      provider: "Gmail",
      state: "connected",
      label: "Orion",
      messages: 12,
      unread: 3,
      imap: { address: "imap.gmail.com:993", state: "connected" },
      smtp: { address: "smtp.gmail.com:465", state: "connected" },
    };
    answerJson(status);
    expect(await mailStatus()).toStrictEqual({ ok: true, data: status });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(lastRequest().url).toBe(`${BASE}/api/mail/status`);
    expect(lastRequest().init?.headers).toStrictEqual({ Authorization: "Bearer test-token" });
  });
});

describe("apiInfo", () => {
  const openapi = {
    info: { title: "Orion desk API", version: "1.2.3" },
    paths: { "/api/tickets": { get: {} }, "/api/customers": { get: {} } },
  };

  it("reads the title, the version and the route list from the OpenAPI document", async () => {
    answerJson(openapi);
    expect(await apiInfo()).toStrictEqual({ ok: true, data: {
      title: "Orion desk API",
      version: "1.2.3",
      routes: ["/api/tickets", "/api/customers"],
    } });
    expect(lastRequest().url).toBe(`${BASE}/openapi.json`);
  });

  it("sends no token, even when one is set", async () => {
    answerJson(openapi);
    await apiInfo();
    expect(lastRequest().init).toStrictEqual({ cache: "no-store", headers: {}, signal: timeoutSignal });
  });

  it("works without a token", async () => {
    vi.stubEnv("ORION_AGENT_TOKEN", undefined);
    answerJson(openapi);
    expect(await apiInfo()).toStrictEqual({ ok: true, data: {
      title: "Orion desk API",
      version: "1.2.3",
      routes: ["/api/tickets", "/api/customers"],
    } });
  });

  it("gives empty values when the document has neither info nor paths", async () => {
    answerJson({});
    expect(await apiInfo()).toStrictEqual({ ok: true, data: { title: "", version: "", routes: [] } });
  });

  it("gives an empty title alone when only the title is missing", async () => {
    answerJson({ info: { version: "1.2.3" }, paths: {} });
    expect(await apiInfo()).toStrictEqual({ ok: true, data: { title: "", version: "1.2.3", routes: [] } });
  });

  it("gives an empty version alone when only the version is missing", async () => {
    answerJson({ info: { title: "Orion desk API" }, paths: {} });
    expect(await apiInfo()).toStrictEqual({ ok: true, data: { title: "Orion desk API", version: "", routes: [] } });
  });

  it("passes on a problem from the API unchanged", async () => {
    answerJson({ error: { code: "server_error", message: "Broken." } }, 500);
    expect(await apiInfo()).toStrictEqual({
      ok: false,
      problem: { status: 500, code: "server_error", message: "Broken." },
    });
  });

  it("passes on an unreachable API unchanged", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    expect(await apiInfo()).toStrictEqual({
      ok: false,
      problem: {
        status: null,
        code: "api_unreachable",
        message: `The desk API at ${BASE} did not answer. Start it with the orion-api launch configuration.`,
      },
    });
  });

  it("passes on a reply that was not JSON unchanged", async () => {
    answer("<html></html>");
    expect(await apiInfo()).toStrictEqual({
      ok: false,
      problem: {
        status: 200,
        code: "unexpected_response",
        message: "The API answered 200, but the reply was not JSON.",
      },
    });
  });
});
