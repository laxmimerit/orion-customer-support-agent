"use client";

import Link from "next/link";
import { useState } from "react";

import { PriorityTile, StatusPill, TopBar } from "@/components/desk";
import { SearchField } from "@/components/search";
import type { CustomerTicket } from "@/lib/api";
import { channelLabel, isResolved, orNotRecorded, plural } from "@/lib/format";

type Show = "all" | "active" | "resolved";

// The search box sits in the top bar and filters the history below it, so this component draws the
// page frame. `head` and `rail` are rendered on the server and passed through.
export function CustomerHistory({ tickets, head, rail }: {
  tickets: CustomerTicket[]; head: React.ReactNode; rail: React.ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [show, setShow] = useState<Show>("all");

  const resolved = tickets.filter((ticket) => isResolved(ticket.status)).length;
  const options: [Show, string][] = [
    ["all", `All ${tickets.length}`],
    ["active", `Active ${tickets.length - resolved}`],
    ["resolved", `Resolved ${resolved}`],
  ];

  const words = query.trim().toLowerCase();
  const rows = tickets.filter((ticket) =>
    (show === "all" || (show === "resolved") === isResolved(ticket.status)) &&
    (!words || [ticket.subject, ticket.ticket_id, ticket.component]
      .some((value) => value?.toLowerCase().includes(words))));

  return (
    <>
      <TopBar>
        {/* onSubmit stops Enter from reloading the page and losing the filter. */}
        <SearchField label="Search this customer's tickets" placeholder="Search this customer's tickets"
          value={query} onChange={setQuery} onSubmit={setQuery} />
      </TopBar>
      <main className="page is-detail cprof-page">
        {head}
        <div className="split">
          <section className="card split-main cprof-history" aria-labelledby="hist-title">
            <div className="card-head">
              <h2 id="hist-title">Support history <span aria-live="polite">· {plural(rows.length, "ticket")}</span></h2>
              <div className="segmented" role="group" aria-label="Show tickets">
                {options.map(([value, label]) => (
                  <button key={value} type="button" aria-pressed={show === value} onClick={() => setShow(value)}>
                    {label}
                  </button>
                ))}
              </div>
            </div>
            {rows.length > 0 ? (
              <ul className="cprof-rows">
                {rows.map((ticket) => <TicketRow key={ticket.ticket_id} ticket={ticket} />)}
              </ul>
            ) : (
              <p className="cprof-none">
                {tickets.length > 0 ? "No tickets match." : "No tickets recorded for this customer."}
              </p>
            )}
          </section>
          <aside className="split-rail" aria-label="Account">{rail}</aside>
        </div>
      </main>
    </>
  );
}

function TicketRow({ ticket }: { ticket: CustomerTicket }) {
  const id = ticket.ticket_id;
  return (
    <li className="row cprof-row">
      <PriorityTile priority={ticket.priority} />
      <span className="row-text">
        <Link className="row-title cprof-link" href={`/tickets/${encodeURIComponent(id)}`}>{ticket.subject ?? id}</Link>
        <span className="row-sub">
          <strong>{id}</strong> · {orNotRecorded(ticket.component)} · {channelLabel(ticket.channel)}
        </span>
      </span>
      <span className="cprof-row-end">
        <span className="cprof-owner">
          <strong>{orNotRecorded(ticket.assigned_to)}</strong>
          <span>{orNotRecorded(ticket.team)}</span>
        </span>
        <StatusPill status={ticket.status} fixed />
      </span>
    </li>
  );
}
