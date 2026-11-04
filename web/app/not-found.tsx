import type { Metadata } from "next";
import Link from "next/link";

import { PageHead, TicketSearchBar } from "@/components/desk";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <PageHead title="Page not found" description="The desk has no page at this address." />
        <p><Link className="button is-primary" href="/">Back to the ticket queue</Link></p>
      </main>
    </>
  );
}
