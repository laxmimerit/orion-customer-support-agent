import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CaseClock } from "@/components/case-clock";
import { Conversation } from "@/components/conversation";
import { ApiProblemPanel, ChannelIcon, Crumbs, Facts, PageHead, PriorityTile, StatusPill, TicketSearchBar } from "@/components/desk";
import { BackIcon } from "@/components/icons";
import { type Customer, type Ticket, ticketDetail } from "@/lib/api";
import { NOT_RECORDED, channelLabel, initial, orNotRecorded, plural, sentenceCase } from "@/lib/format";

import "./case.css";

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
        <TicketSearchBar />
        <main className="page is-detail case-page">
          <Crumbs parent="Tickets" href="/" current={ticketId} />
          <PageHead title={ticketId} />
          <ApiProblemPanel problem={result.problem} />
        </main>
      </>
    );
  }

  const { ticket, customer, messages } = result.data;

  return (
    <>
      <TicketSearchBar />
      <main className="page is-detail case-page">
        <Crumbs parent="Tickets" href="/" current={ticket.ticket_id} />

        <section className="card case-hero" aria-labelledby="case-title">
          <div className="case-head">
            <div className="case-heading">
              <h1 id="case-title" className="page-title">{ticket.ticket_id} · {ticket.subject ?? "No subject recorded"}</h1>
              <CasePills ticket={ticket} />
            </div>
            <Link className="button" href="/"><BackIcon />Back to queue</Link>
          </div>
          <CaseClock
            status={ticket.status}
            replyTarget={ticket.sla_response_hours}
            reply={ticket.first_response_hours}
            resolveTarget={ticket.sla_resolution_hours}
            resolved={ticket.resolution_hours}
          />
        </section>

        <div className="split">
          <div className="split-main">
            <Conversation
              messages={messages}
              request={ticket.body}
              company={customer?.company ?? null}
              agentId={ticket.agent_id}
            />
          </div>
          <aside className="split-rail" aria-label="Case details">
            <CustomerCard customer={customer} customerId={ticket.customer_id} />
            <TicketCard ticket={ticket} />
          </aside>
        </div>
      </main>
    </>
  );
}

function CasePills({ ticket }: { ticket: Ticket }) {
  const named = (label: string, value: string | null) => value ?? `${label}: ${NOT_RECORDED}`;
  const sentiment = ticket.sentiment?.toLowerCase();
  return (
    <div className="case-pills">
      <StatusPill status={ticket.status} />
      <PriorityTile priority={ticket.priority} />
      <span className="pill">{named("Category", ticket.category && sentenceCase(ticket.category))}</span>
      <span className="pill">{named("Component", ticket.component)}</span>
      <span className="pill">
        <ChannelIcon channel={ticket.channel} />
        {named("Channel", ticket.channel && channelLabel(ticket.channel))}
      </span>
      <span className={`pill ${sentiment ? `case-sentiment-${sentiment}` : "tone-missing"}`}>
        Sentiment: {sentiment ?? NOT_RECORDED}
      </span>
    </div>
  );
}

function CustomerCard({ customer, customerId }: { customer: Customer | null; customerId: string | null }) {
  const company = customer?.company ?? null;
  const plan = customer?.plan_id
    ? [sentenceCase(customer.plan_id), customer.seats === null ? null : plural(customer.seats, "seat")].filter(Boolean).join(" · ")
    : NOT_RECORDED;
  const location = [customer?.country, customer?.region].filter(Boolean).join(" · ");

  return (
    <div className="card card-pad case-customer">
      <div className="case-company">
        <span className="case-company-mark" aria-hidden="true">{initial(company)}</span>
        <div className="case-company-text">
          <h2 className="case-company-name">
            {customer
              ? <Link href={`/customers/${encodeURIComponent(customer.customer_id)}`}>{company ?? NOT_RECORDED}</Link>
              : NOT_RECORDED}
          </h2>
          <p className="case-company-id">Customer {orNotRecorded(customerId)}</p>
        </div>
      </div>
      <Facts items={[
        ["Plan", plan],
        ["Industry", orNotRecorded(customer?.industry)],
        ["Location", orNotRecorded(location)],
        ["Company size", orNotRecorded(customer?.company_size?.replace("-", "–"))],
        ["Found Orion via", customer?.acquisition_source ? sentenceCase(customer.acquisition_source) : NOT_RECORDED],
      ]} />
    </div>
  );
}

function TicketCard({ ticket }: { ticket: Ticket }) {
  const { reopened_count: reopened, escalated } = ticket;
  return (
    <div className="card card-pad">
      <h2 className="card-title">Ticket</h2>
      <Facts items={[
        ["Agent", orNotRecorded(ticket.agent_id)],
        ["Component", orNotRecorded(ticket.component)],
        ["Reopened", reopened === null ? NOT_RECORDED : plural(reopened, "time")],
        ["Escalated", escalated === null ? NOT_RECORDED : escalated > 0 ? "Yes" : "No"],
      ]} />
      <div className="case-rating">
        <span className="case-rating-label">Customer rating</span>
        <Rating csat={ticket.csat} />
      </div>
    </div>
  );
}

function Rating({ csat }: { csat: number | null }) {
  if (csat === null) return <strong className="case-rating-none">{NOT_RECORDED}</strong>;
  return (
    <span className="case-rating-bars" role="img" aria-label={`Rated ${csat} out of 5`}>
      {[1, 2, 3, 4, 5].map((step) => <span key={step} className={`case-rating-bar${step <= csat ? " is-on" : ""}`} />)}
      <strong>{csat} / 5</strong>
    </span>
  );
}
