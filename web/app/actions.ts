"use server";

import { type ApiProblem, type MailSync, approveDraft, sendDraft, syncMail, ticketDetail } from "@/lib/api";

// What the queue's preview panel loads for the chosen ticket. Only these fields leave the server:
// the ticket detail also holds contact details and timestamps, and the desk shows neither.
export type TicketPreview = {
  company: string | null;
  first_response_hours: string | null;
  sla_response_hours: string | null;
  resolution_hours: string | null;
  sla_resolution_hours: string | null;
};

export type PreviewResult = { ok: true; preview: TicketPreview } | { ok: false; message: string };

export async function ticketPreview(ticketId: string): Promise<PreviewResult> {
  if (typeof ticketId !== "string" || !ticketId) return { ok: false, message: "No ticket was chosen." };
  const result = await ticketDetail(ticketId);
  if (!result.ok) return { ok: false, message: result.problem.message };
  const { ticket, customer } = result.data;
  return { ok: true, preview: {
    company: customer?.company ?? null,
    first_response_hours: ticket.first_response_hours,
    sla_response_hours: ticket.sla_response_hours,
    resolution_hours: ticket.resolution_hours,
    sla_resolution_hours: ticket.sla_resolution_hours,
  } };
}

export type MailSyncResult = { ok: true; sync: MailSync } | { ok: false; message: string };

// Named field by field, so anything else the API adds to its answer stays on the server.
export async function syncMailbox(): Promise<MailSyncResult> {
  const result = await syncMail();
  if (!result.ok) return { ok: false, message: result.problem.message };
  const { added, linked, unlinked, skipped, remaining } = result.data;
  return { ok: true, sync: { added, linked, unlinked, skipped, remaining } };
}

export type DraftStepResult = { ok: true } | { ok: false; problem: ApiProblem };

export async function approveReply(draftId: string, approvedBy: string): Promise<DraftStepResult> {
  const result = await approveDraft(draftId, approvedBy);
  return result.ok ? { ok: true } : { ok: false, problem: result.problem };
}

export async function sendReply(draftId: string): Promise<DraftStepResult> {
  const result = await sendDraft(draftId);
  return result.ok ? { ok: true } : { ok: false, problem: result.problem };
}
