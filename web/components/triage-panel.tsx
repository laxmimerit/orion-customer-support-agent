"use client";

import Link from "next/link";
import { type MouseEvent, useEffect, useRef, useState } from "react";

import { Facts, PriorityTile } from "@/components/desk";
import { AlertIcon } from "@/components/icons";
import { ModelPicker } from "@/components/model-picker";
import { type AskProblem, askProblem } from "@/lib/ask";
import { plural, sentenceCase } from "@/lib/format";
import { type AllowedModel, firstRunnable } from "@/lib/models";
import { type Triage, isTriage, recordHref } from "@/lib/triage";

type Phase = "idle" | "waiting" | "done" | "stopped" | "failed";

const ANNOUNCED: Partial<Record<Phase, string>> = {
  waiting: "Waiting for the model",
  done: "The triage has finished",
  stopped: "Stopped",
};

const UNREACHABLE: AskProblem = { status: null, code: "desk_unreachable", message: "The desk did not answer. Check the connection and try again." };

// A suggestion beside the stored values, never a change to them: the result lives only on this page.
export function TriagePanel({ ticketId, models }: { ticketId: string; models: AllowedModel[] }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [model, setModel] = useState(firstRunnable(models));
  const [triage, setTriage] = useState<Triage | null>(null);
  const [problem, setProblem] = useState<AskProblem | null>(null);
  const running = useRef<AbortController | null>(null);
  const busy = phase === "waiting";

  // Leaving the page ends the call all the way to the model.
  useEffect(() => () => running.current?.abort(), []);

  function fail(failure: AskProblem) {
    setProblem(failure);
    setPhase("failed");
  }

  async function run() {
    const controller = new AbortController();
    running.current = controller;
    setTriage(null);
    setProblem(null);
    setPhase("waiting");
    try {
      const response = await fetch(`/tickets/${encodeURIComponent(ticketId)}/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
        signal: controller.signal,
      });
      const body: unknown = await response.json().catch(() => null);
      if (response.ok && isTriage(body)) {
        setTriage(body);
        setPhase("done");
      } else {
        fail(askProblem(body, response.status));
      }
    } catch {
      if (controller.signal.aborted) setPhase("stopped");
      else fail(UNREACHABLE);
    } finally {
      running.current = null;
    }
  }

  // One button that changes job, so keyboard focus stays on it.
  function click(event: MouseEvent) {
    event.preventDefault();
    if (busy) running.current?.abort();
    else void run();
  }

  return (
    <section className="card ask" aria-labelledby="triage-title">
      <div className="triage-head">
        <div className="ask-head">
          <h2 id="triage-title">Triage this case</h2>
          <p>A language model reads what the customer wrote and past cases, without this ticket&apos;s stored category, priority or team. It suggests its own, and changes nothing.</p>
        </div>
        <button className={busy ? "button" : "button is-primary"} type="button" onClick={click}>{busy ? "Stop" : "Triage"}</button>
      </div>
      <div className="triage-picker">
        <ModelPicker id="triage-model" models={models} value={model} onChange={setModel} disabled={busy} />
      </div>

      {/* Always mounted: a live region that arrives with its text often isn't read out. */}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{ANNOUNCED[phase] ?? ""}</p>

      {phase !== "idle" && (
        <div className="ask-result" aria-busy={busy}>
          {busy && <p className="ask-waiting">Reading the case and past tickets…</p>}
          {phase === "stopped" && <p className="ask-note">Stopped before the triage finished.</p>}
          {triage && (
            <>
              <p className="ask-label">Model suggestion from {triage.model} · not saved</p>
              <Facts items={[
                ["Category", sentenceCase(triage.category)],
                ["Priority", <PriorityTile key="priority" priority={triage.priority} />],
                ["Team", triage.team],
              ]} />
              <p className="ask-label">Reason</p>
              <p className="ask-answer">{triage.reason}</p>
              <p className="ask-label">Records it used</p>
              {triage.record_ids.length === 0
                ? <p className="ask-note">It relied on no record a tool returned, so check this against the case yourself.</p>
                : <ul className="ask-sources">{triage.record_ids.map((id) => <Record key={id} id={id} />)}</ul>}
              {triage.dropped_ids > 0 && <p className="ask-note">The desk removed {plural(triage.dropped_ids, "ID")} that no tool returned.</p>}
            </>
          )}
          {problem && (
            <div className="problem" role="alert">
              <AlertIcon />
              <div>
                <p className="problem-title">No triage</p>
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

// The result lives only on this page, so a record opens in a new tab and leaves it standing.
function Record({ id }: { id: string }) {
  const href = recordHref(id);
  return (
    <li>
      {href
        ? <Link href={href} target="_blank">{id}<span className="visually-hidden"> (opens in a new tab)</span></Link>
        : <span className="ask-source-title">{id}</span>}
    </li>
  );
}
