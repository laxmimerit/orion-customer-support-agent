import Link from "next/link";

import { Crumbs, TicketSearchBar } from "@/components/desk";

import "./customer.css";

export default function CustomerNotFound() {
  return (
    <>
      <TicketSearchBar />
      <main className="page is-detail cprof-page">
        <Crumbs parent="Customers" href="/customers" current="Not found" />
        <section className="card empty">
          <h1 className="page-title">Customer not found</h1>
          <p className="empty-hint cprof-not-found">No customer has this ID. IDs match exactly, including capitals.</p>
          <Link className="button" href="/customers">Back to Customers</Link>
        </section>
      </main>
    </>
  );
}
