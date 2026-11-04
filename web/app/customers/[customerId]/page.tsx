import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { CustomerHistory } from "@/components/customer-history";
import { ApiProblemPanel, Crumbs, Facts, PageHead, TicketSearchBar } from "@/components/desk";
import { AlertIcon, CheckIcon } from "@/components/icons";
import { type CustomerProfile, customerProfile, type CustomerTicket, type Invoice } from "@/lib/api";
import {
  centsToMoney, initial, isResolved, money, NOT_RECORDED, orNotRecorded, plural, sentenceCase, toCents,
} from "@/lib/format";

import "./customer.css";

export const metadata: Metadata = { title: "Customer" };

export default async function CustomerPage({ params }: { params: Promise<{ customerId: string }> }) {
  const { customerId } = await params;
  const result = await customerProfile(customerId);

  if (!result.ok) {
    if (result.problem.status === 404 || result.problem.status === 422) notFound();
    return (
      <>
        <TicketSearchBar />
        <main className="page is-detail cprof-page">
          <Crumbs parent="Customers" href="/customers" current={customerId} />
          <PageHead title={customerId} />
          <ApiProblemPanel problem={result.problem} />
        </main>
      </>
    );
  }

  const profile = result.data;
  return (
    <CustomerHistory
      tickets={profile.support_history.items}
      head={<Overview profile={profile} />}
      rail={<Rail profile={profile} />}
    />
  );
}

const planClass = (plan: string) => `is-${plan.toLowerCase()}`;
const paidCount = (invoices: Invoice[]) => invoices.filter((invoice) => invoice.status?.toLowerCase() === "paid").length;

function Overview({ profile }: { profile: CustomerProfile }) {
  const { customer_id: id, company, account_details: account, subscription, support_history: history } = profile;
  const invoices = profile.invoice_history;
  const active = history.items.filter((ticket) => !isResolved(ticket.status)).length;

  return (
    <>
      <Crumbs parent="Customers" href="/customers" current={id} />
      <section className="card cprof-hero" aria-labelledby="cust-title">
        <div className="cprof-identity">
          <span className="cprof-avatar" aria-hidden="true">{initial(company ?? id)}</span>
          <div className="cprof-name">
            <h1 id="cust-title" className="page-title">{company ?? id}</h1>
            <div className="cprof-tags">
              <span>{id} · {orNotRecorded(account.industry)}</span>
              {subscription?.plan
                ? <span className={`pill cprof-pill cprof-plan ${planClass(subscription.plan)}`}>{subscription.plan}</span>
                : <span className="pill cprof-pill tone-missing">Plan not recorded</span>}
              <SubscriptionPill subscription={subscription} />
            </div>
          </div>
        </div>
        <div className="cprof-stats">
          <Stat label="Seats" value={subscription?.seats} />
          <Stat label="Active cases" value={active} warn={active > 0} />
          <Stat label="All cases" value={history.total} />
          <Stat label="Invoices paid" value={invoices.length > 0 ? paidCount(invoices) : null}
            of={invoices.length > 0 ? invoices.length : undefined} />
        </div>
      </section>
    </>
  );
}

function SubscriptionPill({ subscription }: { subscription: CustomerProfile["subscription"] }) {
  const status = subscription?.status?.toLowerCase();
  if (!subscription) return <span className="pill cprof-pill tone-missing">Subscription {NOT_RECORDED.toLowerCase()}</span>;
  if (!status) return <span className="pill cprof-pill tone-missing">Subscription status {NOT_RECORDED.toLowerCase()}</span>;
  return (
    <span className={`pill cprof-pill ${status === "active" ? "tone-progress" : "tone-resolved"}`}>
      <span className="dot" aria-hidden="true" />
      Subscription {status}
    </span>
  );
}

function Stat({ label, value, of, warn = false }: {
  label: string; value: number | null | undefined; of?: number; warn?: boolean;
}) {
  const missing = value === null || value === undefined;
  return (
    <div className="cprof-stat">
      <div className="cprof-stat-label">{label}</div>
      <div className={`cprof-stat-value${missing ? " is-missing" : ""}${warn ? " is-warn" : ""}`}>
        {missing ? NOT_RECORDED : value}
        {!missing && of !== undefined && <span> of {of}</span>}
      </div>
    </div>
  );
}

function Rail({ profile }: { profile: CustomerProfile }) {
  const { account_details: account, subscription } = profile;
  const status = subscription?.status;
  return (
    <>
      <div className="card card-pad">
        <h2 className="card-title">Account</h2>
        <Facts items={[
          ["Industry", orNotRecorded(account.industry)],
          ["Company size", orNotRecorded(account.company_size)],
          ["Country", orNotRecorded(account.country)],
          ["Region", orNotRecorded(account.region)],
        ]} />
      </div>
      <div className="card card-pad">
        <h2 className="card-title">Subscription</h2>
        <Facts items={[
          ["Plan", orNotRecorded(subscription?.plan)],
          ["Seats", orNotRecorded(subscription?.seats)],
          ["Subscription", orNotRecorded(subscription?.subscription_id)],
          ["Status", status
            ? <span className={status.toLowerCase() === "active" ? "cprof-status-active" : undefined}>
                {sentenceCase(status.toLowerCase())}
              </span>
            : NOT_RECORDED],
        ]} />
      </div>
      <Invoices invoices={profile.invoice_history} />
      <Components tickets={profile.support_history.items} />
    </>
  );
}

function Invoices({ invoices }: { invoices: Invoice[] }) {
  // Whole cents, so the sum is exact. An invoice with no total is left out and the line says so.
  const totals = invoices.map((invoice) => toCents(invoice.total_usd)).filter((cents) => cents !== null);
  const sum = totals.reduce((all, cents) => all + cents, 0);
  const across = totals.length === invoices.length
    ? plural(invoices.length, "invoice")
    : `${totals.length} of ${plural(invoices.length, "invoice")}`;

  return (
    <div className="card card-pad">
      <div className="cprof-card-head">
        <h2 className="card-title">Invoices</h2>
        {invoices.length > 0 && <span className="card-meta">Paid {paidCount(invoices)} of {invoices.length}</span>}
      </div>
      {invoices.length === 0 ? (
        <p className="cprof-none">No invoices recorded.</p>
      ) : (
        <>
          <ul className="cprof-invoices">
            {invoices.map((invoice, index) => <InvoiceTile key={index} invoice={invoice} />)}
          </ul>
          <p className="cprof-invoice-sum">
            {totals.length > 0
              ? <><strong>{centsToMoney(sum)}</strong> across {across}</>
              : "Invoice totals not recorded"}
          </p>
        </>
      )}
    </div>
  );
}

// Seats and unit price change between invoices, so each invoice carries its own line.
function invoiceLine({ seats, unit_price_usd: price }: Invoice) {
  const seatText = seats === null ? "Seats not recorded" : plural(seats, "seat");
  return `${seatText} × ${price === null ? "price not recorded" : money(price)}`;
}

function InvoiceTile({ invoice }: { invoice: Invoice }) {
  const status = invoice.status?.toLowerCase();
  return (
    <li className={`cprof-invoice${status === "paid" ? " is-paid" : status === "overdue" ? " is-overdue" : ""}`}>
      <span className="cprof-invoice-status">
        {status === "paid" && <CheckIcon size={11} strokeWidth={3} />}
        {status === "overdue" && <AlertIcon size={11} strokeWidth={3} />}
        {status ? sentenceCase(status) : NOT_RECORDED}
      </span>
      <span className="cprof-invoice-total">{money(invoice.total_usd)}</span>
      <span className="cprof-invoice-line">{invoiceLine(invoice)}</span>
    </li>
  );
}

function Components({ tickets }: { tickets: CustomerTicket[] }) {
  const counts = new Map<string, number>();
  for (const ticket of tickets) {
    const name = ticket.component ?? NOT_RECORDED;
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  const rows = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "en"));
  const largest = rows[0]?.[1] ?? 1;

  return (
    <div className="card card-pad">
      <h2 className="card-title">Tickets by component</h2>
      {rows.length === 0 ? (
        <p className="cprof-none">No tickets recorded.</p>
      ) : (
        <div className="cprof-components" role="img" aria-label={rows.map(([name, count]) => `${name} ${count}`).join(", ")}>
          {rows.map(([name, count]) => (
            <div key={name} className="cprof-component">
              <span className="cprof-component-name">{name}</span>
              <span className="bar-track"><span className="bar-fill" style={{ width: `${(count / largest) * 100}%` }} /></span>
              <strong>{count}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
