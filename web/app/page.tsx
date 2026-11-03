import Link from "next/link";

import { ApiProblemPanel, Notice, PageHeading, PriorityChip, StatusPill } from "@/components/desk";
import { type TicketPage, ticketPage } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded } from "@/lib/format";

const PAGE_SIZE = 25;

export default async function TicketQueue({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const requested = Number((await searchParams).page ?? "1");
  const page = Number.isInteger(requested) && requested >= 1 ? Math.min(requested, 100_000) : 1;
  const result = await ticketPage(page, PAGE_SIZE);

  return (
    <>
      <PageHeading crumbs={[{ label: "Tickets" }, { label: "Ticket queue" }]} title="Ticket queue">
        <p className="page-desc">Every ticket in the desk, newest first. Open a ticket to see its customer and conversation.</p>
      </PageHeading>

      <Notice lead="Read-only.">
        Every value on this page comes from the Orion desk API. Dates and times are not shown, and nothing here changes a ticket.
      </Notice>

      {result.ok ? <Queue {...result.data} /> : <ApiProblemPanel problem={result.problem} />}

      <footer className="footer">Prototype. Search is not part of this version.</footer>
    </>
  );
}

function Queue({ items, page, page_size, total }: TicketPage) {
  const pages = Math.max(1, Math.ceil(total / page_size));
  const first = (page - 1) * page_size + 1;
  const last = first + items.length - 1;
  const shown = items.length ? `${first}–${last}` : "None";

  return (
    <>
      <section className="stats" aria-label="Queue summary">
        <div className="stat"><div className="stat-value">{total}</div><div className="stat-label">Tickets in the desk</div></div>
        <div className="stat"><div className="stat-value">{shown}</div><div className="stat-label">Shown on this page</div></div>
        <div className="stat"><div className="stat-value">{page} of {pages}</div><div className="stat-label">Page</div></div>
      </section>

      <section className="panel" aria-labelledby="queue-title">
        <div className="panel-head">
          <h2 id="queue-title">Tickets, newest first</h2>
          <div className="panel-meta">{items.length ? `${first}–${last} of ${total}` : `0 of ${total}`}</div>
        </div>

        {items.length ? (
          <div className="table-scroll">
            <table className="tickets">
              <thead>
                <tr>
                  <th scope="col">Ticket / subject</th>
                  <th scope="col">Customer</th>
                  <th scope="col">Status</th>
                  <th scope="col">Priority</th>
                  <th scope="col">Agent</th>
                </tr>
              </thead>
              <tbody>
                {items.map((ticket) => (
                  <tr key={ticket.ticket_id}>
                    <td>
                      <div className="cell-stack">
                        <span className="ticket-number">{ticket.ticket_id}</span>
                        <Link className="ticket-subject" href={`/tickets/${encodeURIComponent(ticket.ticket_id)}`}>
                          {ticket.subject ?? "No subject recorded"}
                        </Link>
                        <span className="cell-sub">
                          {orNotRecorded(ticket.category)} · {orNotRecorded(ticket.channel)}
                        </span>
                      </div>
                    </td>
                    <td><span className="customer-id">{ticket.customer_id ?? NOT_RECORDED}</span></td>
                    <td><StatusPill status={ticket.status} /></td>
                    <td><PriorityChip priority={ticket.priority} /></td>
                    <td>{orNotRecorded(ticket.agent_id)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty">
            No tickets on this page. The queue has {pages} {pages === 1 ? "page" : "pages"}. <Link href="/">Go to the first page</Link>.
          </p>
        )}

        <nav className="paging" aria-label="Queue pages">
          <span className="panel-meta">Page {page} of {pages}</span>
          <div className="paging-links">
            <PageLink page={page - 1} disabled={page <= 1}>Previous page</PageLink>
            <PageLink page={page + 1} disabled={page >= pages}>Next page</PageLink>
          </div>
        </nav>
      </section>
    </>
  );
}

function PageLink({ page, disabled, children }: { page: number; disabled: boolean; children: React.ReactNode }) {
  if (disabled) {
    return <span className="paging-link" aria-disabled="true">{children}</span>;
  }
  return <Link className="paging-link" href={page === 1 ? "/" : `/?page=${page}`}>{children}</Link>;
}
