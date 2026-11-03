import Link from "next/link";

import { PageHeading, Panel } from "@/components/desk";

export default function TicketNotFound() {
  return (
    <>
      <PageHeading crumbs={[{ label: "Ticket queue", href: "/" }, { label: "Not found" }]} title="No such ticket" />
      <Panel id="not-found" title="The desk API has no ticket with this ID">
        <p className="panel-body">
          Ticket IDs are matched exactly, including case, for example T00727. <Link href="/">Back to the ticket queue</Link>.
        </p>
      </Panel>
    </>
  );
}
