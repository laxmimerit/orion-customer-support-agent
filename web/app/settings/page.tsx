import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { LockIcon } from "@/components/icons";
import { type LanguageModels, type MailState, type MailStatus, type ModelState, type Result, apiAddress, apiInfo, languageModels, mailStatus, ticketPage } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded, plural } from "@/lib/format";
import "./settings.css";

export const metadata: Metadata = { title: "Settings" };

// Nothing here is editable: each panel reports what the desk is connected to today.
export default async function Settings() {
  const [info, tickets, models, mail] = await Promise.all([apiInfo(), ticketPage(1, 1), languageModels(), mailStatus()]);

  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <PageHead title="Settings" description="What this desk is connected to. Nothing on this page can be changed yet." />

        <div className="settings-note" role="note">
          <LockIcon size={18} strokeWidth={2} />
          <span>
            <strong>Read-only.</strong> API, language model and mail details are read from the Orion desk API when the page opens.
          </span>
        </div>

        {!info.ok && <ApiProblemPanel problem={info.problem} title="The desk API did not return its details" retryTarget="the desk details" />}
        {info.ok && !tickets.ok && <ApiProblemPanel problem={tickets.problem} title="The desk API did not return ticket access" retryTarget="ticket access" />}

        <section className="settings-section" aria-labelledby="settings-models">
          <h2 id="settings-models">Models &amp; APIs</h2>
          <div className="settings-grid">
            <div className="card settings-panel is-api">
              <PanelHead title="Orion desk API"><Answering ok={info.ok} /></PanelHead>
              <dl className="settings-facts">
                <dt>Name</dt>
                <dd className={info.ok ? "is-strong" : "is-failed"}>{info.ok ? orNotRecorded(info.data.title) : "Did not answer"}</dd>
                <dt>Version</dt>
                <dd className={info.ok ? "is-strong" : "is-failed"}>{info.ok ? orNotRecorded(info.data.version) : "Did not answer"}</dd>
                <dt>Address</dt>
                <dd><code>{apiAddress()}</code></dd>
                <dt>Access</dt>
                <dd>Agent token, read-only. It is held by the web server and never sent to the browser.</dd>
                <dt>Ticket access</dt>
                <dd className={tickets.ok ? "is-strong" : "is-failed"}>
                  {tickets.ok ? `Allowed: ${plural(tickets.data.total, "ticket")}` : tickets.problem.message}
                </dd>
              </dl>
              <div className="settings-routes">
                <span id="settings-routes-label" className="settings-routes-label">{info.ok ? `Routes · ${info.data.routes.length}` : "Routes"}</span>
                {!info.ok && <p className="is-failed">The API did not list its routes.</p>}
                {info.ok && info.data.routes.length === 0 && <p>{NOT_RECORDED}</p>}
                {info.ok && info.data.routes.length > 0 && (
                  <ul role="list" aria-labelledby="settings-routes-label">{info.data.routes.map((route) => <li key={route}><code>{route}</code></li>)}</ul>
                )}
              </div>
            </div>

            <LanguageModelPanel models={models} />
          </div>
        </section>

        <section className="settings-section" aria-labelledby="settings-connections">
          <h2 id="settings-connections">Connections</h2>
          <div className="settings-grid">
            {/* The route list needs no database, so this panel goes by the ticket read instead. */}
            <div className="card settings-panel">
              <PanelHead title="Desk database"><Answering ok={tickets.ok} /></PanelHead>
              {tickets.ok
                ? <p>Read through the Orion desk API, which opens it read-only. The web app has no database connection of its own.</p>
                : <p className="is-failed">It could not be read through the Orion desk API.</p>}
            </div>

            <CustomerMailPanel mail={mail} />
          </div>
        </section>
      </main>
    </>
  );
}

const MODEL_STATES: Record<ModelState | "not_run", { pill: string; tone: "is-answering" | "is-off" | "is-failed"; note: string }> = {
  connected: { pill: "Connected", tone: "is-answering",
    note: "OpenRouter accepted the key and lists the model. Checked when this page opened; no tokens are used." },
  no_key: { pill: "Not set up", tone: "is-off",
    note: "OPENROUTER_API_KEY is not set for the desk API, so the Ask panel on a case cannot answer." },
  key_refused: { pill: "Key refused", tone: "is-failed", note: "OpenRouter refused the key in OPENROUTER_API_KEY." },
  model_unavailable: { pill: "Model unavailable", tone: "is-failed", note: "OpenRouter does not list this model at the moment." },
  not_answering: { pill: "Not answering", tone: "is-failed", note: "OpenRouter did not answer the check." },
  not_run: { pill: "Not run", tone: "is-off", note: "Written on the list and never called." },
};

function LanguageModelPanel({ models }: { models: Result<LanguageModels> }) {
  if (!models.ok) {
    return (
      <div className="card settings-panel">
        <PanelHead title="Language models"><Answering ok={false} /></PanelHead>
        <p className="is-failed">{models.problem.message}</p>
      </div>
    );
  }
  const { connection, options } = models.data;
  const state = MODEL_STATES[connection.state];
  return (
    <div className="card settings-panel is-api">
      <PanelHead title="Language models">
        <span className={`pill settings-pill ${state.tone}`}>
          <span className="dot" aria-hidden="true" />
          {state.pill}
        </span>
      </PanelHead>
      <p className={state.tone === "is-failed" ? "is-failed" : undefined}>{state.note}</p>
      <dl className="settings-facts">
        <dt>Provider</dt>
        <dd className="is-strong">{connection.provider}</dd>
        <dt>Model</dt>
        <dd><code>{connection.model}</code></dd>
        <dt>Address</dt>
        <dd><code>{connection.address}</code></dd>
        <dt>Connected with</dt>
        <dd>{connection.sdk}</dd>
        <dt>Key</dt>
        <dd>Held by the desk API. It is never sent to the web server or the browser.</dd>
        <dt>Used by</dt>
        <dd>Triage and the Ask panel on a case. Using either sends that ticket, its messages and its customer details to {connection.provider}, without emails or dates.</dd>
        <dt>If a model fails</dt>
        <dd>The agent sees the error. The desk never moves to another model, and a paid one is used only when an agent picks it.</dd>
      </dl>
      <div className="settings-routes">
        <span id="settings-providers-label" className="settings-routes-label">Allow-list · the only models the desk can call</span>
        <ul role="list" aria-labelledby="settings-providers-label" className="settings-providers">
          {options.map((option) => (
            <li key={option.id}>
              <span>{option.label} · {option.provider}</span>
              <span className={`pill settings-pill ${MODEL_STATES[option.state].tone}`}>
                <span className="dot" aria-hidden="true" />
                {MODEL_STATES[option.state].pill}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

const MAIL_STATES: Record<MailState, { pill: string; tone: "is-answering" | "is-off" | "is-failed"; note: string }> = {
  connected: { pill: "Connected", tone: "is-answering",
    note: "The desk API logged in to the mailbox. Checked at most once a minute; no mail was sent." },
  not_set_up: { pill: "Not set up", tone: "is-off",
    note: "The desk API needs ORION_MAIL_USER, ORION_MAIL_APP_PASSWORD and ORION_MAIL_LABEL before it can read mail." },
  login_refused: { pill: "Login refused", tone: "is-failed",
    note: "The mail server refused the login in ORION_MAIL_USER and ORION_MAIL_APP_PASSWORD." },
  label_missing: { pill: "Label missing", tone: "is-failed", note: "The mailbox has no label named in ORION_MAIL_LABEL." },
  not_answering: { pill: "Not answering", tone: "is-failed", note: "The mail server did not answer the check." },
};

// Each count can be unknown on its own, and an unknown count is never shown as 0.
function mailCounts(messages: number | null, unread: number | null) {
  if (messages === null && unread === null) return NOT_RECORDED;
  const unknown = NOT_RECORDED.toLowerCase();
  return `${messages === null ? `Messages ${unknown}` : plural(messages, "message")}, ${unread === null ? `unread ${unknown}` : `${unread} unread`}`;
}

function CustomerMailPanel({ mail }: { mail: Result<MailStatus> }) {
  if (!mail.ok) {
    return (
      <div className="card settings-panel">
        <PanelHead title="Customer mail"><Answering ok={false} /></PanelHead>
        <p className="is-failed">{mail.problem.message}</p>
      </div>
    );
  }
  const { provider, label, messages, unread, imap, smtp } = mail.data;
  const state = MAIL_STATES[mail.data.state];
  return (
    <div className="card settings-panel is-api">
      <PanelHead title="Customer mail">
        <span className={`pill settings-pill ${state.tone}`}>
          <span className="dot" aria-hidden="true" />
          {state.pill}
        </span>
      </PanelHead>
      <p className={state.tone === "is-failed" ? "is-failed" : undefined}>{state.note}</p>
      <dl className="settings-facts">
        <dt>Provider</dt>
        <dd className="is-strong">{provider}</dd>
        <dt>IMAP</dt>
        <dd><code>{imap.address}</code> · {MAIL_STATES[imap.state].pill}</dd>
        <dt>SMTP</dt>
        <dd><code>{smtp.address}</code> · {smtp.state === "connected" ? "Login accepted" : MAIL_STATES[smtp.state].pill}</dd>
        <dt>Label</dt>
        <dd>{orNotRecorded(label)}</dd>
        <dt>In the label</dt>
        <dd>{mailCounts(messages, unread)}</dd>
        <dt>Password</dt>
        <dd>Held by the desk API. It is never sent to the web server or the browser.</dd>
        <dt>Sending mail</dt>
        <dd>Off. The desk has no send route, so no reply can leave it.</dd>
      </dl>
      <p>
        These counts are all the desk reads. Messages do not appear on the desk yet.
        The rules mail must follow are in <code>docs/communication-contract.md</code>.
      </p>
    </div>
  );
}

function PanelHead({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="settings-panel-head">
      <h3>{title}</h3>
      {children}
    </div>
  );
}

function Answering({ ok }: { ok: boolean }) {
  return (
    <span className={`pill settings-pill ${ok ? "is-answering" : "is-failed"}`}>
      <span className="dot" aria-hidden="true" />
      {ok ? "Answering" : "Not answering"}
    </span>
  );
}
