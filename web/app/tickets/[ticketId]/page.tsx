import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { ApiProblemPanel, Facts, Notice, PageHeading, Panel, PriorityChip, StatusPill } from "@/components/desk";
import { type Customer, type Message, type Ticket, ticketDetail } from "@/lib/api";
import { NOT_RECORDED, hours, initials, orNotRecorded } from "@/lib/format";

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
        <ApiProblemPanel problem={result.problem} />
      </>
    );
  }

  const { ticket, customer, messages } = result.data;
  const ribbon = [ticket.category, ticket.component, ticket.channel && `Via ${ticket.channel}`].filter(Boolean).join(" · ");

  return (
    <>
      <PageHeading
        crumbs={[{ label: "Ticket queue", href: "/" }, { label: ticket.ticket_id }]}
        title={`${ticket.ticket_id} · ${ticket.subject ?? "No subject recorded"}`}
      >
        {ribbon && <div className="ribbon">{ribbon}</div>}
      </PageHeading>

      <Notice lead="Read-only.">
        Every value here comes from the Orion desk API. Messages are shown in order, oldest first, without times.
      </Notice>

      <div className="case-row">
        <div className="case-main">
          <Panel id="summary" title="Request summary">
            <p className="panel-body request">{ticket.body ?? "No request text recorded."}</p>
          </Panel>

          <Panel id="targets" title="Service targets">
            <div className="targets">
              <TargetTile label="First reply" doneLabel="Waited" target={ticket.sla_response_hours} done={ticket.first_response_hours} />
              <TargetTile label="Resolution" doneLabel="Took" target={ticket.sla_resolution_hours} done={ticket.resolution_hours} />
            </div>
            <p className="panel-note">Bar: time taken. Tick: target. All figures are in hours.</p>
          </Panel>

          <Conversation messages={messages} customer={customer} />
        </div>

        <aside className="case-side" aria-label="Ticket and customer">
          <Panel id="ticket" title="Ticket">
            <TicketFacts ticket={ticket} />
          </Panel>
          <Panel id="customer" title="Customer">
            <CustomerFacts customer={customer} customerId={ticket.customer_id} />
          </Panel>
        </aside>
      </div>

      <footer className="footer">Prototype. Targets and times taken are in hours.</footer>
    </>
  );
}

function TargetTile({ label, doneLabel, target, done }: {
  label: string; doneLabel: string; target: string | null; done: string | null;
}) {
  const targetValue = target === null ? null : Number(target);
  const doneValue = done === null ? null : Number(done);
  const comparable = targetValue !== null && doneValue !== null;
  const missed = comparable && doneValue > targetValue;
  const outcome = !comparable
    ? (done === null ? `${doneLabel.toLowerCase()} not recorded` : "no target recorded")
    : missed ? "target missed" : "target met";
  // The track is the larger of the two, so the tick shows where the target fell.
  const scale = comparable ? Math.max(doneValue, targetValue) || 1 : 1;

  return (
    <div className={`target ${missed ? "tone-missed" : comparable ? "tone-met" : "tone-priority"}`}>
      <div className="target-title">{label}: {outcome}</div>
      <div className="target-figures">
        <div>
          <div className="target-label">Target</div>
          <div className={`target-value${target === null ? " is-missing" : ""}`}>{target === null ? NOT_RECORDED : hours(target)}</div>
        </div>
        <div>
          <div className="target-label">{doneLabel}</div>
          <div className={`target-value${done === null ? " is-missing" : ""}`}>{done === null ? NOT_RECORDED : hours(done)}</div>
        </div>
      </div>
      {comparable && (
        <div className="bar" aria-hidden="true">
          <div className="bar-fill" style={{ width: `${(doneValue / scale) * 100}%` }} />
          <div className="bar-tick" style={{ left: `calc(${(targetValue / scale) * 100}% - 1px)` }} />
        </div>
      )}
    </div>
  );
}

function Conversation({ messages, customer }: { messages: Message[]; customer: Customer | null }) {
  // Messages carry a role but no author ID, so agent replies are not attributed to a named agent.
  const customerName = customer?.company ?? "Customer";
  const count = messages.length === 1 ? "1 message" : `${messages.length} messages`;

  return (
    <Panel id="conversation" title="Conversation" meta={`${count}, oldest first`}>
      {messages.length === 0 && <p className="empty">No messages recorded for this ticket.</p>}
      {messages.map((message, index) => {
        const isAgent = message.author_role === "agent";
        const isCustomer = message.author_role === "customer";
        const author = isAgent ? "Agent" : isCustomer ? customerName : "Role not recorded";
        return (
          <article key={message.message_id} className="message">
            <div className={`avatar${isAgent ? " is-agent" : ""}`} aria-hidden="true">
              {isAgent ? "AG" : initials(author)}
            </div>
            <div className="message-content">
              <div className="message-meta">
                <span className="message-author">{author}</span>
                <span className="message-role">
                  {isCustomer ? "Customer · " : ""}Message {index + 1} · {message.message_id}
                </span>
              </div>
              <p className="message-body">{message.body ?? "No text recorded."}</p>
            </div>
          </article>
        );
      })}
    </Panel>
  );
}

function TicketFacts({ ticket }: { ticket: Ticket }) {
  return (
    <Facts items={[
      ["Status", <StatusPill key="status" status={ticket.status} />],
      ["Priority", <PriorityChip key="priority" priority={ticket.priority} />],
      ["Assigned to", orNotRecorded(ticket.agent_id)],
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

function CustomerFacts({ customer, customerId }: { customer: Customer | null; customerId: string | null }) {
  if (customer === null) {
    return (
      <p className="panel-body">
        {customerId ? `No customer record for ${customerId}.` : "No customer is recorded on this ticket."}
      </p>
    );
  }
  const plan = customer.plan_id === null ? NOT_RECORDED
    : customer.seats === null ? customer.plan_id : `${customer.plan_id} · ${customer.seats} seats`;
  const location = [customer.country, customer.region].filter(Boolean).join(" · ") || NOT_RECORDED;

  return (
    <>
      <div className="account-name">{customer.company ?? "Company not recorded"}</div>
      <Facts items={[
        ["Customer id", customer.customer_id],
        ["Plan", plan],
        ["Industry", orNotRecorded(customer.industry)],
        ["Company size", orNotRecorded(customer.company_size)],
        ["Location", location],
        ["Acquired through", orNotRecorded(customer.acquisition_source)],
        ["Contact", orNotRecorded(customer.contact_email)],
      ]} />
    </>
  );
}
