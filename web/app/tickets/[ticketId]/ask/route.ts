import { askCase } from "@/lib/api";
import { QUESTION_LIMIT } from "@/lib/ask";
import { decodeId } from "@/lib/detail-pages";

function refuse(status: number, code: string, message: string) {
  return Response.json({ error: { status, code, message } }, { status });
}

// The browser's way to the API, so the agent token stays on this server. It takes a POST to keep the question out of
// the browser's address and history, and only as JSON, which another site's page cannot send here without the browser
// asking first. The API's routes are GET only, so from here on the question is in a query string, as a search is.
export async function POST(request: Request, { params }: { params: Promise<{ ticketId: string }> }) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    return refuse(415, "unsupported_media_type", "Send the question as JSON.");
  }
  const body: { question?: unknown } | null = await request.json().catch(() => null);
  const question = typeof body?.question === "string" ? body.question.trim() : "";
  if (!question) return refuse(422, "invalid_request", "Write a question first.");
  if (question.length > QUESTION_LIMIT) {
    return refuse(422, "invalid_request", `A question can be up to ${QUESTION_LIMIT} characters.`);
  }

  const result = await askCase(decodeId((await params).ticketId), question, request.signal);
  if (!result.ok) {
    return Response.json({ error: result.problem }, { status: result.problem.status ?? 502 });
  }
  // no-transform keeps compression from holding the answer back until it has finished.
  return new Response(result.data, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store, no-transform", "X-Accel-Buffering": "no" },
  });
}
