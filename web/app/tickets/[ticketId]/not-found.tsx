import Link from "next/link";

import { Crumbs, PageHead, TicketSearchBar } from "@/components/desk";

import "./case.css";

export default function TicketNotFound() {
  return (
    <>
      <TicketSearchBar />
      <main className="page is-detail case-page">
        <Crumbs parent="Tickets" href="/" current="Not found" />
        <PageHead title="No such ticket" />
        <div className="card empty">
          <p className="empty-title">The desk API has no ticket with this ID</p>
          <p className="empty-hint">Ticket IDs are matched exactly, including case.</p>
          <Link className="button is-primary" href="/">Back to the ticket queue</Link>
        </div>
      </main>
    </>
  );
}
