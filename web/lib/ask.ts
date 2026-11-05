// Reads the stream behind the Ask panel. Used in the browser, so it holds nothing from the server.

// The longest question the API takes (`q` on /api/tickets/{ticket_id}/ask).
export const QUESTION_LIMIT = 500;
// The longest note the API takes (`note` on the same route).
export const NOTE_LIMIT = 300;

export type AskProblem = { status: number | null; code: string; message: string };

// A record the answer names that the case or a lookup returned. The API checks that, so these are safe to link.
// A mail has no page of its own, so it is named and not linked.
export type AskSource = { kind: "ticket" | "customer" | "article" | "mail"; id: string; title: string | null };

// A page a web tool gave the model. Its title is null when it was fetched: OpenRouter doesn't say if a fetch worked, so
// the desk can't either.
export type AskPage = { url: string; title: string | null };

export type AskEvent =
  | { type: "lookup"; label: string }
  | { type: "delta"; text: string }
  | { type: "done"; complete: boolean; found: boolean; sources: AskSource[]; pages: AskPage[]; searches: string[]; note: string | null }
  | { type: "error"; problem: AskProblem };

// What the desk shows if a failure arrives in a shape it does not know.
export function askProblem(body: unknown, status: number | null): AskProblem {
  const error = (body as { error?: { status?: unknown; code?: unknown; message?: unknown } } | null)?.error;
  return {
    status: typeof error?.status === "number" ? error.status : status,
    code: typeof error?.code === "string" ? error.code : "unexpected_response",
    message: typeof error?.message === "string" ? error.message : "The desk did not return an answer. Try again.",
  };
}

// The model is told not to use Markdown, and after a lookup it sometimes does anyway. The panel shows plain text, so
// the marks would be read as part of the answer. Done on the whole text, because a mark can arrive split across events.
export function plainAnswer(text: string) {
  return text.replace(/\*\*|`/g, "");
}

const SOURCE_PAGES: Record<AskSource["kind"], string | null> = { ticket: "tickets", customer: "customers", article: "knowledge", mail: null };

export function sourceHref(source: AskSource) {
  const page = SOURCE_PAGES[source.kind];
  return page === null ? null : `/${page}/${encodeURIComponent(source.id)}`;
}

function isSource(value: unknown): value is AskSource {
  const source = value as Partial<AskSource> | null;
  return typeof source?.id === "string" && typeof source.kind === "string" && Object.hasOwn(SOURCE_PAGES, source.kind)
    && (source.title === null || typeof source.title === "string");
}

// A page's address goes straight into a link, so anything but http and https stops here, whatever the API sent.
function isPage(value: unknown): value is AskPage {
  const page = value as Partial<AskPage> | null;
  return typeof page?.url === "string" && URL.canParse(page.url) && ["http:", "https:"].includes(new URL(page.url).protocol)
    && (page.title === null || typeof page.title === "string");
}

function parseFrame(frame: string): AskEvent | null {
  let name = "";
  const data: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) name = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  let body: unknown;
  try {
    body = JSON.parse(data.join("\n"));
  } catch {
    return null;
  }
  const fields = body as { text?: unknown; label?: unknown; complete?: unknown; found?: unknown; sources?: unknown; pages?: unknown; searches?: unknown; note?: unknown };
  if (name === "lookup" && typeof fields?.label === "string") return { type: "lookup", label: fields.label };
  if (name === "delta" && typeof fields?.text === "string") return { type: "delta", text: fields.text };
  if (name === "done") {
    const sources = Array.isArray(fields?.sources) ? fields.sources.filter(isSource) : [];
    const pages = Array.isArray(fields?.pages) ? fields.pages.filter(isPage) : [];
    const searches = Array.isArray(fields?.searches) ? fields.searches.filter((query) => typeof query === "string") : [];
    const note = typeof fields?.note === "string" ? fields.note : null;
    return { type: "done", complete: fields?.complete === true, found: fields?.found !== false, sources, pages, searches, note };
  }
  if (name === "error") return { type: "error", problem: askProblem(body, null) };
  return null;
}

// Returns a function that takes bytes as they arrive and gives back each finished event. A read can end anywhere,
// even inside a character, so the decoder and the unfinished frame carry over to the next one.
export function askReader() {
  const decoder = new TextDecoder();
  let buffer = "";
  return (chunk: Uint8Array): AskEvent[] => {
    buffer += decoder.decode(chunk, { stream: true }).replace(/\r\n/g, "\n");
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";
    return frames.map(parseFrame).filter((event) => event !== null);
  };
}
