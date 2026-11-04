import type { Metadata } from "next";

import { Facts, PageHeading, Panel } from "@/components/desk";
import { apiAddress, apiInfo, ticketPage } from "@/lib/api";

export const metadata: Metadata = { title: "Settings" };

// Nothing here is editable: each panel reports what the desk is connected to today.
export default async function Settings() {
  const [info, tickets] = await Promise.all([apiInfo(), ticketPage(1, 1)]);

  return (
    <>
      <PageHeading
        crumbs={[{ label: "Workspace" }, { label: "Settings" }]}
        title="Settings"
        notice="Read-only. API details are read from the Orion desk API when the page opens. Mail and models are not set up, so there is nothing to configure for them."
      >
        <p className="page-desc">What this desk is connected to. Nothing on this page can be changed yet.</p>
      </PageHeading>

      <section className="settings-section c12" aria-labelledby="models-apis">
        <h2 id="models-apis">Models &amp; APIs</h2>
        <div className="settings-grid">
          <Panel id="desk-api" title="Orion desk API" meta={<Answering ok={info.ok && tickets.ok} />}>
            <Facts items={[
              ["Name", info.ok ? info.data.title : "Did not answer"],
              ["Version", info.ok ? info.data.version : "Did not answer"],
              ["Address", apiAddress()],
              ["Access", "Agent token, read-only. It is held by the web server and never sent to the browser."],
              ["Ticket access", tickets.ok ? `Allowed: ${tickets.data.total} tickets` : `${tickets.problem.code}: ${tickets.problem.message}`],
              ["Routes", info.ok
                ? <ul className="routes">{info.data.routes.map((route) => <li key={route}><code>{route}</code></li>)}</ul>
                : info.problem.message],
            ]} />
          </Panel>

          <Panel id="models" title="Language models" meta={<NotSetUp />}>
            <div className="panel-body">
              <p>No language model is connected. The desk does not draft, summarise or classify anything.</p>
            </div>
          </Panel>
        </div>
      </section>

      <section className="settings-section c12" aria-labelledby="connections">
        <h2 id="connections">Connections</h2>
        <div className="settings-grid">
          <Panel id="database" title="Desk database" meta={<Answering ok={tickets.ok} />}>
            <div className="panel-body">
              <p>
                {tickets.ok
                  ? "Read through the Orion desk API, which opens it read-only. The web app has no database connection of its own."
                  : `The API could not read it: ${tickets.problem.message}`}
              </p>
            </div>
          </Panel>

          <Panel id="mail" title="Customer mail" meta={<NotSetUp />}>
            <div className="panel-body">
              <p>
                No mail provider is connected. The desk cannot send or receive mail, and no reply leaves it.
                The rules mail must follow are in <code>docs/communication-contract.md</code>.
              </p>
            </div>
          </Panel>
        </div>
      </section>
    </>
  );
}

function Answering({ ok }: { ok: boolean }) {
  return (
    <span className={`pill ${ok ? "tone-met" : "tone-missed"}`}>
      <span className="dot" aria-hidden="true" />
      {ok ? "Answering" : "Not answering"}
    </span>
  );
}

function NotSetUp() {
  return <span className="chip tone-priority">Not set up</span>;
}
