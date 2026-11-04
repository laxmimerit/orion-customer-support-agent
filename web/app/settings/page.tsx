import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { LockIcon } from "@/components/icons";
import { apiAddress, apiInfo, ticketPage } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded, plural } from "@/lib/format";
import "./settings.css";

export const metadata: Metadata = { title: "Settings" };

// Nothing here is editable: each panel reports what the desk is connected to today.
export default async function Settings() {
  const [info, tickets] = await Promise.all([apiInfo(), ticketPage(1, 1)]);

  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <PageHead title="Settings" description="What this desk is connected to. Nothing on this page can be changed yet." />

        <div className="settings-note" role="note">
          <LockIcon size={18} strokeWidth={2} />
          <span>
            <strong>Read-only.</strong> API details are read from the Orion desk API when the page opens.
            Mail and models are not set up, so there is nothing to configure for them.
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

            <div className="card settings-panel">
              <PanelHead title="Language models"><NotSetUp /></PanelHead>
              <p>No language model is connected. The desk does not draft, summarise or classify anything.</p>
            </div>
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

            <div className="card settings-panel">
              <PanelHead title="Customer mail"><NotSetUp /></PanelHead>
              <p>
                No mail provider is connected. The desk cannot send or receive mail, and no reply leaves it.
                The rules mail must follow are in <code>docs/communication-contract.md</code>.
              </p>
            </div>
          </div>
        </section>
      </main>
    </>
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

function NotSetUp() {
  return (
    <span className="pill settings-pill is-off">
      <span className="dot" aria-hidden="true" />
      Not set up
    </span>
  );
}
