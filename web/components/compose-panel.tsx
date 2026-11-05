"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { approveReply, sendReply } from "@/app/actions";
import { AlertIcon } from "@/components/icons";
import { type AskProblem, askProblem } from "@/lib/ask";
import { type ComposeDraft, LANGUAGES, TEMPLATES, TONES, isDraft, mailChoice } from "@/lib/compose";

type Phase = "idle" | "writing" | "drafted" | "approving" | "approved" | "sending" | "sent" | "failed";
type LinkedMail = { mail_id: string; sender_name: string | null; subject: string | null };

const UNREACHABLE: AskProblem = { status: null, code: "desk_unreachable", message: "The desk did not answer. Check the connection and try again." };

function Choice({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: [string, string][]; onChange: (value: string) => void }) {
  return (
    <div className="ask-model">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map(([option, text]) => <option key={option} value={option}>{text}</option>)}
      </select>
    </div>
  );
}

const named = (options: string[]) => options.map((option): [string, string] => [option, option]);

// Compose writes, a named person approves, and only then can anyone send. The draft shown is the stored text: it can't be
// edited, so what was read is what goes out. A different text is a new draft.
export function ComposePanel({ ticketId, mails }: { ticketId: string; mails: LinkedMail[] }) {
  const router = useRouter();
  const [mailId, setMailId] = useState(mails.at(-1)?.mail_id ?? "");
  const [template, setTemplate] = useState(TEMPLATES[0]);
  const [tone, setTone] = useState(TONES[0]);
  const [language, setLanguage] = useState(LANGUAGES[0]);
  const [draft, setDraft] = useState<ComposeDraft | null>(null);
  const [approver, setApprover] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [problem, setProblem] = useState<AskProblem | null>(null);
  const running = useRef<AbortController | null>(null);
  const busy = phase === "writing" || phase === "approving" || phase === "sending";

  useEffect(() => () => running.current?.abort(), []);

  function fail(failure: AskProblem) {
    setProblem(failure);
    setPhase("failed");
  }

  async function compose() {
    const controller = new AbortController();
    running.current = controller;
    setDraft(null);
    setApprover("");
    setProblem(null);
    setPhase("writing");
    try {
      const response = await fetch(`/tickets/${encodeURIComponent(ticketId)}/compose`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mail_id: mailId, template, tone, language }),
        signal: controller.signal,
      });
      const body: unknown = await response.json().catch(() => null);
      if (response.ok && isDraft(body)) {
        setDraft(body);
        setPhase("drafted");
        router.refresh();
      } else {
        fail(askProblem(body, response.status));
      }
    } catch {
      if (controller.signal.aborted) setPhase("idle");
      else fail(UNREACHABLE);
    } finally {
      running.current = null;
    }
  }

  async function step(during: Phase, after: Phase, work: () => Promise<{ ok: true } | { ok: false; problem: AskProblem }>) {
    setProblem(null);
    setPhase(during);
    try {
      const result = await work();
      if (result.ok) setPhase(after);
      else fail(result.problem);
    } catch {
      fail(UNREACHABLE);
    }
    router.refresh();
  }

  if (mails.length === 0) {
    return <div className="ask-form"><p className="ask-note">This case has no linked mail, so there is no thread to reply in.</p></div>;
  }

  const translated = draft !== null && draft.language !== "English";
  const approved = phase === "approved" || phase === "sending" || phase === "sent";

  return (
    <div>
      <form className="ask-form" onSubmit={(event) => { event.preventDefault(); void compose(); }}>
        <Choice id="compose-mail" label="Reply to" value={mailId} onChange={setMailId}
          options={mails.map((mail) => [mail.mail_id, mailChoice(mail)])} />
        <Choice id="compose-template" label="Template" value={template} options={named(TEMPLATES)} onChange={setTemplate} />
        <Choice id="compose-tone" label="Tone" value={tone} options={named(TONES)} onChange={setTone} />
        <Choice id="compose-language" label="Language" value={language} options={named(LANGUAGES)} onChange={setLanguage} />
        <div className="ask-actions">
          <span className="ask-hint">Paid: runs on GPT-6 Luna. Nothing is sent from here.</span>
          <button className="button is-primary" type="submit" disabled={busy}>Write draft</button>
        </div>
      </form>

      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{phase === "sent" ? "The reply was sent" : phase === "drafted" ? "The draft is ready" : ""}</p>

      {(draft || problem || phase === "writing") && (
        <div className="ask-result" aria-busy={busy}>
          {phase === "writing" && <p className="ask-waiting">Reading the records and writing…</p>}
          {draft && (
            <>
              <p className="ask-label">To</p>
              <p className="ask-question">{draft.recipient}</p>
              <p className="ask-label">Subject</p>
              <p className="ask-question">{draft.subject}</p>
              <div className={translated ? "compose-texts is-pair" : "compose-texts"}>
                <div>
                  <p className="ask-label">{translated ? `${draft.language}: this is what goes out` : "This is what goes out"}</p>
                  <p className="compose-text">{draft.body}</p>
                </div>
                {translated && (
                  <div>
                    <p className="ask-label">English, for checking: not sent</p>
                    <p className="compose-text">{draft.english}</p>
                  </div>
                )}
              </div>
              <p className="ask-label">Cited article</p>
              <p className="ask-question">
                <Link href={`/knowledge/${encodeURIComponent(draft.article_id)}`} target="_blank">{draft.article_id}<span className="visually-hidden"> (opens in a new tab)</span></Link>
                {draft.article_title ? ` · ${draft.article_title}` : ""}
              </p>
              {!approved && (
                <div className="compose-approve">
                  <div className="ask-model">
                    <label htmlFor="compose-approver">Approved by</label>
                    <select id="compose-approver" value={approver} onChange={(event) => setApprover(event.target.value)}>
                      <option value="">Pick your name</option>
                      {draft.approvers.map((name) => <option key={name} value={name}>{name}</option>)}
                    </select>
                  </div>
                  <button className="button is-primary" type="button" disabled={!approver || busy}
                    onClick={() => void step("approving", "approved", () => approveReply(draft.draft_id, approver))}>Approve</button>
                </div>
              )}
              {approved && <p className="ask-note">Approved by {approver}.</p>}
              {(phase === "approved" || phase === "sending") && (
                <button className="button is-primary" type="button" disabled={busy}
                  onClick={() => void step("sending", "sent", () => sendReply(draft.draft_id))}>Send to {draft.recipient}</button>
              )}
              {phase === "sent" && <p className="ask-note">Sent in the same thread. Action history has the record.</p>}
            </>
          )}
          {problem && (
            <div className="problem" role="alert">
              <AlertIcon />
              <div>
                <p className="problem-title">That did not work</p>
                <p className="problem-text">{problem.message}</p>
                <p className="problem-code">{problem.status ? `HTTP ${problem.status} · ` : ""}{problem.code}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
