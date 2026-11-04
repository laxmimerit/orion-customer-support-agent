import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import {
  BacklogWaffle, ByPriority, CategoryStrips, FirstReplyFinding, FirstReplyRings, KpiStrip, ReportProblem, UnresolvedByPeriod,
} from "@/components/report-charts";
import { TablesProvider, TablesToggle } from "@/components/report-tables";
import { backlogReport, categoryReport, firstReplyReport, priorityReport, volumeReport } from "@/lib/api";
import { kpisFrom, splitTotal } from "@/lib/report-text";
import "./reports.css";

export const metadata: Metadata = { title: "Team reports" };

const TITLE = "Team reports";
const DESCRIPTION = "How fast the desk answers, how customers rate it, what is waiting.";

export default async function Reports() {
  const [volume, backlog, priority, category, firstReply] = await Promise.all([
    volumeReport(), backlogReport(), priorityReport(), categoryReport(), firstReplyReport(),
  ]);

  if (!volume.ok && !backlog.ok && !priority.ok && !category.ok && !firstReply.ok) {
    return (
      <>
        <TicketSearchBar />
        <main className="page">
          <PageHead title={TITLE} description={DESCRIPTION} />
          <ApiProblemPanel problem={volume.problem} title="The desk API did not return the reports" />
        </main>
      </>
    );
  }

  const volumeTotal = volume.ok ? splitTotal(volume.data.rows, "month").total : undefined;
  const firstReplyTotal = firstReply.ok ? splitTotal(firstReply.data.rows, "priority").total : undefined;
  const breakdownTotal = priority.ok ? splitTotal(priority.data.rows, "priority").total
    : category.ok ? splitTotal(category.data.rows, "category").total : undefined;
  const kpis = kpisFrom({ volume: volumeTotal, breakdown: breakdownTotal, firstReply: firstReplyTotal });
  const tickets = (volumeTotal ?? breakdownTotal)?.tickets;

  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <TablesProvider>
          <PageHead title={TITLE} description={DESCRIPTION}>
            <div className="rp-head-tools">
              {tickets !== undefined && <span className="rp-scope">All {tickets} tickets</span>}
              {(firstReply.ok || category.ok) && <TablesToggle />}
            </div>
          </PageHead>

          {kpis.length > 0 && <KpiStrip kpis={kpis} />}

          {firstReply.ok
            ? <FirstReplyFinding report={firstReply.data.rows} />
            : <ReportProblem id="rp-finding-title" eyebrow="First reply and satisfaction" problem={firstReply.problem} />}

          <div className="rp-grid">
            {volume.ok
              ? <UnresolvedByPeriod report={volume.data.rows} />
              : <ReportProblem id="rp-volume-title" eyebrow="Unresolved by period" problem={volume.problem} />}
            {firstReply.ok
              ? <FirstReplyRings report={firstReply.data.rows} waits={priority.ok ? priority.data.rows : undefined} />
              : <ReportProblem id="rp-first-reply-title" eyebrow="First reply on target" problem={firstReply.problem} />}
            {category.ok
              ? <CategoryStrips report={category.data.rows} />
              : <ReportProblem id="rp-category-title" eyebrow="Categories" problem={category.problem} />}
            {backlog.ok
              ? <BacklogWaffle report={backlog.data.rows} />
              : <ReportProblem id="rp-backlog-title" eyebrow="Backlog" problem={backlog.problem} />}
          </div>

          {priority.ok
            ? <ByPriority report={priority.data.rows} />
            : <ReportProblem id="rp-priority-title" eyebrow="By priority" problem={priority.problem} />}
        </TablesProvider>
      </main>
    </>
  );
}
