// Reads the stream behind the Ask panel. Used in the browser, so it holds nothing from the server.

// The longest question the API takes (`q` on /api/tickets/{ticket_id}/ask).
export const QUESTION_LIMIT = 500;

export type AskProblem = { status: number | null; code: string; message: string };

export type AskEvent =
  | { type: "delta"; text: string }
  | { type: "done"; complete: boolean }
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
  const fields = body as { text?: unknown; complete?: unknown };
  if (name === "delta" && typeof fields?.text === "string") return { type: "delta", text: fields.text };
  if (name === "done") return { type: "done", complete: fields?.complete === true };
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
