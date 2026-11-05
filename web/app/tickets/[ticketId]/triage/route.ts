import { triageCase } from "@/lib/api";
import { decodeId } from "@/lib/detail-pages";

// The browser's way to the API, so the agent token stays on this server. It takes a POST as JSON for the reason the Ask
// route does: another site's page cannot send that here without the browser asking first, and each call spends tokens.
export async function POST(request: Request, { params }: { params: Promise<{ ticketId: string }> }) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    const error = { status: 415, code: "unsupported_media_type", message: "Send the request as JSON." };
    return Response.json({ error }, { status: 415 });
  }
  const result = await triageCase(decodeId((await params).ticketId), request.signal);
  if (!result.ok) return Response.json({ error: result.problem }, { status: result.problem.status ?? 502 });
  const { category, priority, team, reason, record_ids, model, dropped_ids } = result.data;
  return Response.json({ category, priority, team, reason, record_ids, model, dropped_ids });
}
