import { triageMail } from "@/lib/api";
import { decodeId } from "@/lib/detail-pages";

// As the case page's triage route: the token stays on this server, and a JSON POST keeps other sites from spending tokens.
export async function POST(request: Request, { params }: { params: Promise<{ mailId: string }> }) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    const error = { status: 415, code: "unsupported_media_type", message: "Send the request as JSON." };
    return Response.json({ error }, { status: 415 });
  }
  const result = await triageMail(decodeId((await params).mailId), request.signal);
  if (!result.ok) return Response.json({ error: result.problem }, { status: result.problem.status ?? 502 });
  const { category, priority, team, reason, record_ids, model, dropped_ids } = result.data;
  return Response.json({ category, priority, team, reason, record_ids, model, dropped_ids });
}
