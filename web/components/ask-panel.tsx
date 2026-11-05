"use client";

import Link from "next/link";
import { type FormEvent, type KeyboardEvent, type MouseEvent, useEffect, useRef, useState } from "react";

import { AlertIcon } from "@/components/icons";
import { type AskProblem, type AskSource, QUESTION_LIMIT, askProblem, askReader, plainAnswer, sourceHref } from "@/lib/ask";
import { NOT_RECORDED, sentenceCase } from "@/lib/format";

type Phase = "idle" | "waiting" | "writing" | "done" | "cut-short" | "stopped" | "failed";

const ANNOUNCED: Partial<Record<Phase, string>> = {
  waiting: "Waiting for the model",
  done: "The answer has finished",
  "cut-short": "The answer was cut short",
  stopped: "Stopped",
};

const LOST: AskProblem = { status: null, code: "stream_ended", message: "The answer stopped before it finished. Try again." };

// The answer lives only on this page, so a source opens in a new tab and leaves it standing.
function Sources({ ticketId, label, sources }: { ticketId: string; label: string; sources: AskSource[] }) {
  return (
    <>
      <p className="ask-label">{label}</p>
      <ul className="ask-sources">
        {sources.map((source) => (
          <li key={source.id}>
            {source.id === ticketId
              ? <strong>{source.id}</strong>
              : <Link href={sourceHref(source)} target="_blank">{source.id}<span className="visually-hidden"> (opens in a new tab)</span></Link>}
            <span className="ask-source-title">{source.title ?? NOT_RECORDED}</span>
            <span className="ask-source-kind">{source.id === ticketId ? "This case" : sentenceCase(source.kind)}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

// One question at a time: a new one replaces the last answer, and nothing is kept once the page closes.
export function AskPanel({ ticketId }: { ticketId: string }) {
  const [question, setQuestion] = useState("");
  const [asked, setAsked] = useState("");
  const [answer, setAnswer] = useState("");
  const [lookup, setLookup] = useState<string | null>(null);
  const [found, setFound] = useState(true);
  const [sources, setSources] = useState<AskSource[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [problem, setProblem] = useState<AskProblem | null>(null);
  const running = useRef<AbortController | null>(null);
  const busy = phase === "waiting" || phase === "writing";
  const finished = phase === "done" || phase === "cut-short";

  // Leaving the page ends the call all the way to the model.
  useEffect(() => () => running.current?.abort(), []);

  function fail(failure: AskProblem) {
    setProblem(failure);
    setPhase("failed");
  }

  async function ask() {
    const text = question.trim();
    if (!text || running.current) return;
    const controller = new AbortController();
    running.current = controller;
    setAsked(text);
    setAnswer("");
    setLookup(null);
    setFound(true);
    setSources([]);
    setProblem(null);
    setPhase("waiting");
    try {
      const response = await fetch(`/tickets/${encodeURIComponent(ticketId)}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        fail(askProblem(await response.json().catch(() => null), response.status));
        return;
      }
      const read = askReader();
      const reader = response.body.getReader();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const event of read(value)) {
          if (event.type === "lookup") {
            // Anything written before a lookup was the model working, not its answer.
            setAnswer("");
            setLookup(event.label);
            setPhase("waiting");
          } else if (event.type === "delta") {
            setAnswer((current) => current + event.text);
            setPhase("writing");
          } else if (event.type === "error") {
            fail(event.problem);
            return;
          } else {
            setFound(event.found);
            setSources(event.sources);
            setPhase(event.complete ? "done" : "cut-short");
            return;
          }
        }
      }
      fail(LOST);
    } catch {
      if (controller.signal.aborted) setPhase("stopped");
      else fail({ ...LOST, code: "desk_unreachable", message: "The desk did not answer. Check the connection and try again." });
    } finally {
      running.current = null;
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask();
  }

  // The abort re-renders this button as Ask before the click has finished, and that click would then submit the form.
  function stop(event: MouseEvent) {
    event.preventDefault();
    running.current?.abort();
  }

  // Enter asks; Shift+Enter starts a new line. Enter during composition belongs to the input method.
  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void ask();
    }
  }

  return (
    <section className="card ask" aria-labelledby="ask-title">
      <div className="ask-head">
        <h2 id="ask-title">Ask about this case</h2>
        <p>A language model starts from this ticket and can read other tickets, customers and help articles. It changes nothing, and nothing goes to the customer.</p>
      </div>

      <form className="ask-form" onSubmit={submit}>
        <label htmlFor="ask-question">Your question</label>
        <textarea
          id="ask-question"
          rows={2}
          maxLength={QUESTION_LIMIT}
          placeholder="Was the first reply on time?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <div className="ask-actions">
          <span className="ask-hint">Enter to ask, Shift+Enter for a new line</span>
          {/* One button that changes job, so keyboard focus stays on it. */}
          <button
            className={busy ? "button" : "button is-primary"}
            type={busy ? "button" : "submit"}
            disabled={!busy && !question.trim()}
            onClick={busy ? stop : undefined}
          >
            {busy ? "Stop" : "Ask"}
          </button>
        </div>
      </form>

      {/* Always mounted: a live region that arrives with its text often isn't read out. The answer itself is not
          in it, so a screen reader hears when it is ready rather than every few words. */}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{ANNOUNCED[phase] ?? ""}</p>

      {phase !== "idle" && (
        <div className="ask-result" aria-busy={busy}>
          <p className="ask-label">You asked</p>
          <p className="ask-question">{asked}</p>
          <p className="ask-label">Model answer · check it against its sources before you use it</p>
          {phase === "waiting" && <p className="ask-waiting">{lookup ? `${lookup}…` : "Thinking…"}</p>}
          {answer && <p className="ask-answer">{plainAnswer(answer)}</p>}
          {phase === "cut-short" && <p className="ask-note">The answer was cut short, so it may be incomplete.</p>}
          {finished && !found && <p className="ask-note">The records do not hold this answer.</p>}
          {finished && found && sources.length === 0 && (
            <p className="ask-note">This answer names no record, so nothing backs it. Check it yourself before you use it.</p>
          )}
          {finished && sources.length > 0 && <Sources ticketId={ticketId} label={found ? "Sources" : "Records checked"} sources={sources} />}
          {phase === "stopped" && <p className="ask-note">Stopped before the answer finished.</p>}
          {problem && (
            <div className="problem" role="alert">
              <AlertIcon />
              <div>
                <p className="problem-title">No full answer</p>
                <p className="problem-text">{problem.message}</p>
                <p className="problem-code">{problem.status ? `HTTP ${problem.status} · ` : ""}{problem.code}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
