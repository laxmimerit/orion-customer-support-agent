import type { Metadata } from "next";
import { Suspense } from "react";

import { ApiProblemPanel, PageHeading } from "@/components/desk";
import { QueueLoading, RankedQueue, SearchSection, SummaryStrip } from "@/components/queue";
import { SearchToolbar } from "@/components/search-toolbar";
import { backlogReport, priorityReport, search, ticketPage } from "@/lib/api";

export const metadata: Metadata = { title: "Ticket queue · Orion Service Desk" };

const PAGE_SIZE = 25;
const PRIORITIES = ["P1", "P2", "P3", "P4"];

type Params = { page?: string | string[]; q?: string | string[]; priority?: string | string[] };

const one = (value?: string | string[]) => (Array.isArray(value) ? value[0] : value);

export default async function TicketQueue({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const requested = Number(one(params.page) ?? "1");
  const page = Number.isInteger(requested) && requested >= 1 ? Math.min(requested, 100_000) : 1;
  const query = one(params.q)?.trim() ?? "";
  const asked = one(params.priority);
  const priority = asked && PRIORITIES.includes(asked) ? asked : null;

  return (
    <>
      <PageHeading crumbs={[{ label: "Tickets" }, { label: "Ticket queue" }]} title="Ticket queue">
        <p className="page-desc">Find a ticket by its ID or by describing the problem, then open its case.</p>
      </PageHeading>

      <SearchToolbar query={query} priority={priority} />

      <Suspense key={`${page}|${query}|${priority}`} fallback={<QueueLoading searching={Boolean(query)} />}>
        <QueueContent page={page} query={query} priority={priority} />
      </Suspense>
    </>
  );
}

async function QueueContent({ page, query, priority }: { page: number; query: string; priority: string | null }) {
  const [tickets, answer, backlog, byPriority] = await Promise.all([
    query ? null : ticketPage(page, PAGE_SIZE),
    query ? search(query, priority) : null,
    backlogReport(),
    priorityReport(),
  ]);

  const result = answer ?? tickets;
  if (result && !result.ok) {
    return (
      <ApiProblemPanel
        problem={result.problem}
        heading="Tickets can’t be shown"
        cannotLoad="the queue can’t load"
        refused="no tickets can be shown"
      />
    );
  }

  return (
    <>
      <SummaryStrip backlog={backlog} priority={byPriority} />
      {answer?.ok && <SearchSection answer={answer.data} priority={priority} />}
      {tickets?.ok && <RankedQueue {...tickets.data} />}
    </>
  );
}
