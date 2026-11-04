import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ApiProblemPanel, Facts, PageHeading, Panel, PriorityChip, StatusPill } from "@/components/desk";
import { type Customer, type Message, type Ticket, ticketDetail } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded, trimDecimal } from "@/lib/format";

type Props = { params: Promise<{ ticketId: string }> };

function decodeId(raw: string) {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: decodeId((await params).ticketId) };
}

export default async function CasePage({ params }: Props) {
  const ticketId = decodeId((await params).ticketId);
  const result = await ticketDetail(ticketId);

  if (!result.ok) {
    // 404: no such ticket. 422: an ID the API cannot hold (over 32 characters).
    if (result.problem.status === 404 || result.problem.status === 422) notFound();
    return (
      <>
        <PageHeading crumbs={[{ label: "Ticket queue", href: "/" }, { label: ticketId }]} title={ticketId} />
        <ApiProblemPanel
          problem={result.problem}
          heading="This case can’t be shown"
          cannotLoad="this case can’t load"
          refused="this case can’t be shown"
        />
      </>
    );
  }

  const { ticket, customer, messages } = result.data;

  return (
    <>
      <PageHeading
        crumbs={[{ label: "Ticket queue", href: "/" }, { label: ticket.ticket_id }]}
        title={`${ticket.ticket_id} · ${orNotRecorded(ticket.subject)}`}
      >
        <p className="ribbon">
          {orNotRecorded(ticket.category)} · {orNotRecorded(ticket.component)} · Via {orNotRecorded(ticket.channel)}
        </p>
      </PageHeading>

      <div className="case-row c12">
        <div className="case-main">
          <Panel id="summary" title="Request summary">
            <p className="panel-body">{orNotRecorded(ticket.body)}</p>
          </Panel>

          <section className="targets" aria-labelledby="targets">
            <h2 id="targets">Service targets</h2>
            <TargetTile label="First reply" doneLabel="Waited" target={ticket.sla_response_hours} done={ticket.first_response_hours} />
            <TargetTile label="Resolution" doneLabel="Took" target={ticket.sla_resolution_hours} done={ticket.resolution_hours} />
          </section>

          <Conversation messages={messages} ticket={ticket} />
        </div>

        <aside className="case-side" aria-label="Case details">
          <Panel id="ticket" title="Ticket facts">
            <TicketFacts ticket={ticket} />
          </Panel>
          <Panel id="customer" title="Customer">
            <CustomerFacts customer={customer} customerId={ticket.customer_id} />
          </Panel>
        </aside>
      </div>
    </>
  );
}

function TargetFigure({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value === null ? NOT_RECORDED : <>{trimDecimal(value)}<small>h</small></>}</dd>
    </div>
  );
}

function TargetTile({ label, doneLabel, target, done }: {
  label: string; doneLabel: string; target: string | null; done: string | null;
}) {
  const figures = (
    <dl className="figs">
      <TargetFigure label="Target" value={target} />
      <TargetFigure label={doneLabel} value={done} />
    </dl>
  );

  if (target === null || done === null) {
    return (
      <div className="panel tile">
        <h3>{label}: <span className="pill tone-status">{NOT_RECORDED}</span></h3>
        {figures}
      </div>
    );
  }

  const targetValue = Number(target);
  const doneValue = Number(done);
  const missed = doneValue > targetValue;
  const outcome = missed ? "target missed" : "target met";
  const verb = doneLabel.toLowerCase();
  // The track is the larger of the two, so the tick shows where the target fell.
  const scale = Math.max(targetValue, doneValue) || 1;
  const percent = (value: number) => (value / scale * 100).toFixed(1);
  const tick = percent(targetValue);

  return (
    <div className="panel tile">
      <h3>{label}: <span className={`pill ${missed ? "tone-missed" : "tone-met"}`}>{outcome}</span></h3>
      {figures}
      <div>
        <div className="wait-wrap">
          <span className="tick-label" style={{ left: `${tick}%`, transform: `translateX(${Number(tick) > 75 ? "-100%" : "-50%"})` }}>
            Target {trimDecimal(target)} h
          </span>
          <div
            className="wait"
            role="img"
            aria-label={`${label}: ${verb} ${trimDecimal(done)} hours against a ${trimDecimal(target)} hour target; ${outcome}`}
          >
            <span className="in" style={{ width: `calc(${percent(Math.min(doneValue, targetValue))}% - 1px)` }} />
            {missed && <span className="over" style={{ width: `calc(${percent(doneValue - targetValue)}% - 1px)` }} />}
            <span className="tick" style={{ left: `${tick}%` }} />
          </div>
        </div>
        <div className="wait-axis"><span>0 h</span><span>{trimDecimal(done)} h {verb}</span></div>
      </div>
      <div className="legend">
        <span><i style={{ background: "var(--series-resolved)" }} />Within target</span>
        {missed && <span><i style={{ background: "var(--series-missed)" }} />Past target</span>}
      </div>
    </div>
  );
}

function Conversation({ messages, ticket }: { messages: Message[]; ticket: Ticket }) {
  const count = messages.length === 1 ? "1 message" : `${messages.length} messages`;

  return (
    <Panel id="conversation" title="Conversation" meta={count}>
      {messages.length === 0 ? (
        <p className="empty-line">No messages recorded for this ticket.</p>
      ) : (
        <ol className="thread">
          {messages.map((message) => {
            const isAgent = message.author_role === "agent";
            const isCustomer = message.author_role === "customer";
            return (
              <li key={message.message_id} className={`msg ${isAgent ? "agent" : "cust"}`}>
                <span className="who">
                  {isAgent ? <><strong>{orNotRecorded(ticket.agent_id)}</strong> · Agent</>
                    : isCustomer ? <><strong>{orNotRecorded(ticket.customer_id)}</strong> · Customer</>
                    : <strong>{NOT_RECORDED}</strong>}
                </span>
                <p className="bubble">{orNotRecorded(message.body)}</p>
              </li>
            );
          })}
        </ol>
      )}
    </Panel>
  );
}

function TicketFacts({ ticket }: { ticket: Ticket }) {
  return (
    <Facts items={[
      ["Status", <StatusPill key="status" status={ticket.status} />],
      ["Priority", <PriorityChip key="priority" priority={ticket.priority} />],
      ["Assigned agent", orNotRecorded(ticket.agent_id)],
      ["Channel", orNotRecorded(ticket.channel)],
      ["Category", orNotRecorded(ticket.category)],
      ["Component", orNotRecorded(ticket.component)],
      ["Sentiment", orNotRecorded(ticket.sentiment)],
      ["CSAT", orNotRecorded(ticket.csat)],
      ["Reopened", orNotRecorded(ticket.reopened_count)],
      ["Escalated", orNotRecorded(ticket.escalated)],
    ]} />
  );
}

// Only these four customer fields are shown, whatever else the API returns.
function CustomerFacts({ customer, customerId }: { customer: Customer | null; customerId: string | null }) {
  return (
    <Facts items={[
      ["Customer ID", orNotRecorded(customer?.customer_id ?? customerId)],
      ["Company", orNotRecorded(customer?.company)],
      ["Plan", orNotRecorded(customer?.plan_id)],
      ["Seats", orNotRecorded(customer?.seats)],
    ]} />
  );
}
