"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { type MatchResult, findDuplicate, linkToCase } from "@/app/actions";
import { askProblem } from "@/lib/ask";
import { type Triage, isTriage } from "@/lib/triage";

const UNREACHABLE = "The desk did not answer. Check the connection and try again.";

// Triage and the match are suggestions that live only on this page. The link is the one step that stores anything.
export function MailTools({ mailId }: { mailId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [triage, setTriage] = useState<Triage | null>(null);
  const [found, setFound] = useState<Extract<MatchResult, { ok: true }> | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  async function step(work: () => Promise<void>) {
    setBusy(true);
    setProblem(null);
    try {
      await work();
    } catch {
      setProblem(UNREACHABLE);
    }
    setBusy(false);
  }

  const runTriage = () => step(async () => {
    const response = await fetch(`/mail/${encodeURIComponent(mailId)}/triage`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
    });
    const body: unknown = await response.json().catch(() => null);
    if (response.ok && isTriage(body)) setTriage(body);
    else setProblem(askProblem(body, response.status).message);
  });

  const runMatch = () => step(async () => {
    const result = await findDuplicate(mailId);
    if (result.ok) setFound(result);
    else setProblem(result.message);
  });

  const link = (ticketId: string) => step(async () => {
    const result = await linkToCase(mailId, ticketId);
    if (result.ok) router.refresh();
    else setProblem(result.message);
  });

  const match = found?.match;
  return (
    <div className="mail-tools">
      <button className="button" type="button" disabled={busy} onClick={runTriage}>Triage</button>
      <button className="button" type="button" disabled={busy} onClick={runMatch}>Find duplicate</button>
      {match && <button className="button" type="button" disabled={busy} onClick={() => link(match.ticket_id)}>Link to {match.ticket_id}</button>}
      <div aria-live="polite" className="mail-tools-result">
        {busy && <p>Working…</p>}
        {triage && <p>Suggested: {triage.category} · {triage.priority} · {triage.team}. {triage.reason}</p>}
        {match && <p>Possible duplicate: <Link href={`/tickets/${encodeURIComponent(match.ticket_id)}`}>{match.ticket_id}</Link> · {match.subject ?? "No subject recorded"} · {match.status ?? "status not recorded"}</p>}
        {found && !match && <p>No active case is close to this mail.</p>}
      </div>
      {problem && <p className="mail-tools-result is-failed" role="alert">{problem}</p>}
    </div>
  );
}
