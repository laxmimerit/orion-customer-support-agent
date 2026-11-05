import { triageCase } from "@/lib/api";
import { decodeId } from "@/lib/detail-pages";
import { MODEL_ID_LIMIT } from "@/lib/models";

// The browser's way to the API, so the agent token stays on this server. It takes a POST as JSON for the reason the Ask
// route does: another site's page cannot send that here without the browser asking first, and each call spends tokens.
export async function POST(request: Request, { params }: { params: Promise<{ ticketId: string }> }) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    const error = { status: 415, code: "unsupported_media_type", message: "Send the request as JSON." };
    return Response.json({ error }, { status: 415 });
  }
  // The API holds the allow-list and says what it refuses, so a model is only checked for size here.
  const body: { model?: unknown } | null = await request.json().catch(() => null);
  const chosen = typeof body?.model === "string" ? body.model : "";
  if (chosen.length > MODEL_ID_LIMIT) {
    const error = { status: 422, code: "invalid_request", message: `A model can be up to ${MODEL_ID_LIMIT} characters.` };
    return Response.json({ error }, { status: 422 });
  }
  const result = await triageCase(decodeId((await params).ticketId), chosen || null, request.signal);
  if (!result.ok) return Response.json({ error: result.problem }, { status: result.problem.status ?? 502 });
  const { category, priority, team, reason, record_ids, model, dropped_ids } = result.data;
  return Response.json({ category, priority, team, reason, record_ids, model, dropped_ids });
}
