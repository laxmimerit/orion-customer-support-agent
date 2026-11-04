// The ticket queue's sections (notes/design-brief.md, Ticket queue and Search results).
import Link from "next/link";

import { PriorityChip, StatusPill } from "@/components/desk";
import type { BacklogRow, PriorityRow, Result, Report, SearchHit, SearchResults, TicketPage, TicketSummary } from "@/lib/api";
import { orNotRecorded, trimDecimal } from "@/lib/format";
import { rankPage } from "@/lib/ranking";

const NOT_IN_ANSWER = "Not in this answer";
const NOT_A_TICKET = "Not a ticket";
const ANSWER_HOLDS = "This answer holds each ticket’s ID, subject, status, priority and category; customer, channel and agent are not in it.";

function caseHref(ticketId: string) {
  return `/tickets/${encodeURIComponent(ticketId)}`;
}

const results = (count: number) => `${count} ${count === 1 ? "result" : "results"}`;

// Figures from the reports only: the "All" row of each. No report, no strip.
export function SummaryStrip({ backlog, priority }: {
  backlog: Result<Report<BacklogRow>>; priority: Result<Report<PriorityRow>>;
}) {
  const open = backlog.ok ? backlog.data.rows.find((row) => row.status === "All") : undefined;
  const all = priority.ok ? priority.data.rows.find((row) => row.priority === "All") : undefined;
  if (!open || !all) return null;

  return (
    <section className="sub" aria-label="Figures from the reports">
      <Metric figure={open.tickets} unit="tickets" label="Unresolved" note="Backlog: open, in progress and pending" />
      <Metric
        figure={open.no_first_reply_past_target}
        unit="tickets"
        label="No first reply, past target"
        note={`Backlog: ${open.no_first_reply} have no first reply`}
      />
      <Metric
        figure={all.avg_first_response_hours === null ? null : trimDecimal(all.avg_first_response_hours)}
        unit="h"
        label="Average first reply"
        note={`Priority: ${all.first_response_counted} tickets, ${all.first_response_missing} not recorded`}
      />
      <Metric
        figure={all.avg_csat}
        unit="CSAT"
        label="Average CSAT"
        note={`Priority: ${all.csat_counted} tickets, ${all.csat_missing} not recorded`}
      />
    </section>
  );
}

function Metric({ figure, unit, label, note }: { figure: string | number | null; unit: string; label: string; note: string }) {
  return (
    <div className="panel metric c3 metric-col">
      <span className="fig">{orNotRecorded(figure)}{figure !== null && <small>{unit}</small>}</span>
      <span className="label">{label}</span>
      <span className="note">{note}</span>
    </div>
  );
}

export function RankedQueue({ items, page, page_size, total }: TicketPage) {
  const { cards, rows } = rankPage(items);
  const first = (page - 1) * page_size + 1;
  const caption = items.length ? `${first}–${first + items.length - 1} of ${total}, in API order` : `0 of ${total}, in API order`;

  return (
    <>
      <section className="sub" aria-labelledby="now-h">
        <div className="sec-head c12">
          <div className="sec-title">
            <h2 id="now-h">Needs an agent now</h2>
            <span className="cap">Open or in progress at P1 or P2, on this page</span>
          </div>
          <div className="paging">
            <p className="caption" aria-live="polite">
              {caption}
              <span>Ranked within this page by status and priority.</span>
            </p>
            <PageLink page={page - 1} disabled={page <= 1}>Previous</PageLink>
            <PageLink page={page + 1} disabled={page * page_size >= total}>Next</PageLink>
          </div>
        </div>
        {cards.length
          ? cards.map((ticket) => <TicketCard key={ticket.ticket_id} ticket={ticket} />)
          : <p className="empty-line c12">Nothing on this page needs an agent now.</p>}
      </section>

      <section className="panel c12" aria-labelledby="rows-h">
        <div className="panel-head">
          <h2 id="rows-h">What’s next</h2>
        </div>
        {items.length === 0 ? <NoTickets /> : rows.length > 0 && (
          <TicketTable>
            {rows.map((ticket) => <QueueRow key={ticket.ticket_id} ticket={ticket} />)}
          </TicketTable>
        )}
      </section>
    </>
  );
}

function PageLink({ page, disabled, children }: { page: number; disabled: boolean; children: React.ReactNode }) {
  if (disabled) {
    return <button type="button" className="btn" disabled>{children}</button>;
  }
  return <Link className="btn" href={page === 1 ? "/" : `/?page=${page}`}>{children}</Link>;
}

function TicketCard({ ticket }: { ticket: TicketSummary }) {
  return (
    <article className="panel tcard c4 tcard-col">
      <div className="top">
        <span className="ticket-number">{ticket.ticket_id}</span>
        <span className="tags">
          <StatusPill status={ticket.status} />
          <PriorityChip priority={ticket.priority} />
        </span>
      </div>
      <Link className="ticket-subject" href={caseHref(ticket.ticket_id)}>{orNotRecorded(ticket.subject)}</Link>
      <span className="subline">{orNotRecorded(ticket.category)} · {orNotRecorded(ticket.channel)}</span>
      <div className="meta">
        <span><span className="muted">Customer</span> {orNotRecorded(ticket.customer_id)}</span>
        <span><span className="muted">Agent</span> {orNotRecorded(ticket.agent_id)}</span>
      </div>
    </article>
  );
}

function TicketTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="table-box">
      <table className="rows">
        <thead>
          <tr>
            <th scope="col" className="first">Ticket / subject</th>
            <th scope="col">Customer</th>
            <th scope="col">Status</th>
            <th scope="col">Priority</th>
            <th scope="col">Agent</th>
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

function QueueRow({ ticket }: { ticket: TicketSummary }) {
  return (
    <tr>
      <td className="first">
        <div className="l1">
          <span className="ticket-number">{ticket.ticket_id}</span>{" "}
          <Link className="ticket-subject" href={caseHref(ticket.ticket_id)}>{orNotRecorded(ticket.subject)}</Link>
        </div>
        <div className="subline">{orNotRecorded(ticket.category)} · {orNotRecorded(ticket.channel)}</div>
      </td>
      <td>{orNotRecorded(ticket.customer_id)}</td>
      <td><StatusPill status={ticket.status} /></td>
      <td><PriorityChip priority={ticket.priority} /></td>
      <td>{orNotRecorded(ticket.agent_id)}</td>
    </tr>
  );
}

// The API treats an ID as exact, so a query shaped like an ID that comes back by meaning has no ticket.
const ID_SHAPE = /^t\d{5}$/i;

export function SearchSection({ answer, priority }: { answer: SearchResults; priority: string | null }) {
  const { query, match, items } = answer;
  const exact = match === "exact_id";
  const idMissed = !exact && ID_SHAPE.test(query);
  // An exact ID comes back whatever the filter, so the filter is only named when it applied.
  const at = priority && !exact ? ` at ${priority}` : "";
  const caption = idMissed
    ? `No ticket has the ID "${query}"${at} · ${results(items.length)} by meaning`
    : `${results(items.length)} for "${query}"${at}${exact ? "" : ", in relevance order"}`;
  const closest = items.every((item) => item.kind === "ticket")
    ? `${items.length} ${items.length === 1 ? "ticket" : "tickets"}`
    : results(items.length);

  return (
    <section className="panel c12" aria-labelledby="rows-h">
      <div className="panel-head">
        <h2 id="rows-h">Search results</h2>
        <span className="cap" aria-live="polite">{caption}</span>
      </div>
      {items.length === 0 ? <NoTickets /> : (
        <>
          {idMissed && (
            <p className="panel-body">No ticket has that ID, so the API returned the {closest} closest to it by meaning instead.</p>
          )}
          <p className="cap">
            {exact ? "Found by exact ID. " : idMissed ? "Found by meaning, in relevance order. " : "Found by meaning. "}
            {ANSWER_HOLDS}
          </p>
          <TicketTable>
            {items.map((item) => (item.kind === "article"
              ? <ArticleRow key={item.id} article={item} />
              : <SearchRow key={item.id} ticket={item} found={exact ? "Found by exact ID" : "Found by meaning"} />))}
          </TicketTable>
        </>
      )}
    </section>
  );
}

function SearchRow({ ticket, found }: { ticket: SearchHit; found: string }) {
  return (
    <tr>
      <td className="first">
        <div className="l1">
          <span className="ticket-number">{ticket.id}</span>{" "}
          <Link className="ticket-subject" href={caseHref(ticket.id)}>{orNotRecorded(ticket.title)}</Link>
        </div>
        <div className="subline">{orNotRecorded(ticket.category)} · channel not in this answer</div>
        <div className="subline">{found}</div>
      </td>
      <td className="muted">{NOT_IN_ANSWER}</td>
      <td><StatusPill status={ticket.status} /></td>
      <td><PriorityChip priority={ticket.priority} /></td>
      <td className="muted">{NOT_IN_ANSWER}</td>
    </tr>
  );
}

// The desk has no article page, so nothing here is a link.
function ArticleRow({ article }: { article: SearchHit }) {
  return (
    <tr>
      <td className="first">
        <div className="l1">
          <span className="ticket-number">{article.id}</span>{" "}
          <span className="ticket-subject">{orNotRecorded(article.title)}</span>
        </div>
        <div className="subline">{orNotRecorded(article.category)} · Help article</div>
        <div className="subline">Found by meaning</div>
      </td>
      <td className="muted">{NOT_A_TICKET}</td>
      <td className="muted">{NOT_A_TICKET}</td>
      <td className="muted">{NOT_A_TICKET}</td>
      <td className="muted">{NOT_A_TICKET}</td>
    </tr>
  );
}

function NoTickets() {
  return (
    <div className="empty">
      <p><strong>No tickets match.</strong> Try other words or a ticket ID, or press Clear to go back to the queue.</p>
    </div>
  );
}

const SKELETON_METRICS = [0, 1, 2, 3];
const SKELETON_CARDS = [0, 1, 2];
const SKELETON_ROWS = [0, 1, 2, 3, 4, 5];

// Placeholder blocks only: no values, real or invented.
export function QueueLoading({ searching }: { searching: boolean }) {
  return (
    <>
      <section className="sub" aria-label="Figures from the reports, loading">
        {SKELETON_METRICS.map((key) => (
          <div key={key} className="panel metric c3 metric-col" aria-hidden="true">
            <span className="skel" style={{ width: 96, height: 32 }} />
            <span className="skel" style={{ width: 140, height: 12, marginTop: 8 }} />
            <span className="skel" style={{ width: 200, maxWidth: "100%", height: 12, marginTop: 8 }} />
          </div>
        ))}
      </section>

      {!searching && (
        <section className="sub" aria-labelledby="now-h">
          <div className="sec-head c12">
            <div className="sec-title">
              <h2 id="now-h">Needs an agent now</h2>
              <span className="cap">Open or in progress at P1 or P2, on this page</span>
            </div>
            <div className="paging">
              <p className="caption" role="status" aria-live="polite" aria-busy="true">
                Loading tickets from the Orion desk API
                <span>Ranked within this page by status and priority once loaded.</span>
              </p>
              <button type="button" className="btn" disabled>Previous</button>
              <button type="button" className="btn" disabled>Next</button>
            </div>
          </div>
          {SKELETON_CARDS.map((key) => (
            <div key={key} className="panel skel-card c4 tcard-col" aria-hidden="true">
              <span className="skel" style={{ width: 64, height: 16 }} />
              <span className="skel" style={{ width: "80%", height: 16 }} />
              <span className="skel" style={{ width: "50%", height: 12 }} />
              <span className="skel" style={{ width: "60%", height: 16, marginTop: 8 }} />
            </div>
          ))}
        </section>
      )}

      <section className="panel c12" aria-labelledby="rows-h">
        <div className="panel-head">
          <h2 id="rows-h">{searching ? "Search results" : "What’s next"}</h2>
          <span className="cap">Loading</span>
        </div>
        <div className="skel-rows" aria-hidden="true">
          {SKELETON_ROWS.map((key) => (
            <div key={key} className="skel-row">
              <span className="skel" style={{ flex: "0 0 48%", height: 28 }} />
              <span className="skel" style={{ flex: 1, height: 12 }} />
              <span className="skel" style={{ flex: 1, height: 20 }} />
              <span className="skel" style={{ flex: 1, height: 20 }} />
              <span className="skel" style={{ flex: 1, height: 12 }} />
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
