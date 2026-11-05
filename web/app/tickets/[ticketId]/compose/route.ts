import { composeDraft } from "@/lib/api";
import { decodeId } from "@/lib/detail-pages";

// The browser's way to the API, so the agent token stays on this server. JSON only, for the reason the Ask route gives:
// each call spends tokens on a paid model. The API checks the fields and always uses Luna.
export async function POST(request: Request, { params }: { params: Promise<{ ticketId: string }> }) {
  if (!request.headers.get("content-type")?.startsWith("application/json")) {
    const error = { status: 415, code: "unsupported_media_type", message: "Send the request as JSON." };
    return Response.json({ error }, { status: 415 });
  }
  const body: { mail_id?: unknown; template?: unknown; tone?: unknown; language?: unknown } | null = await request.json().catch(() => null);
  const { mail_id, template, tone, language } = body ?? {};
  const result = await composeDraft(decodeId((await params).ticketId), { mail_id, template, tone, language }, request.signal);
  if (!result.ok) return Response.json({ error: result.problem }, { status: result.problem.status ?? 502 });
  const { draft_id, recipient, subject, body: text, english, language: written, article_id, article_title, approvers } = result.data;
  return Response.json({ draft_id, recipient, subject, body: text, english, language: written, article_id, article_title, approvers });
}
