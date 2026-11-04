import type { Metadata } from "next";

import { CustomersList } from "@/components/customers-list";
import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { customerList } from "@/lib/api";

import "./customers.css";

export const metadata: Metadata = { title: "Customers" };

const DESCRIPTION = "Customer accounts, subscription details and support history.";

export default async function CustomersPage() {
  const result = await customerList();

  if (!result.ok) {
    return (
      <>
        <TicketSearchBar />
        <main className="page clist-page">
          <PageHead title="Customers" description={DESCRIPTION} />
          <ApiProblemPanel problem={result.problem} retryTarget="the customer list" />
        </main>
      </>
    );
  }

  return <CustomersList total={result.data.total} items={result.data.items} description={DESCRIPTION} />;
}
