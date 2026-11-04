import type { Metadata } from "next";

import { type Bar, Bars, Chart, Legend, PairedBars, SERIES, averageBar, averageText, largest } from "@/components/charts";
import { ApiProblemPanel, PageHeading, StatusPill } from "@/components/desk";
import {
  type BacklogRow, type Breakdown, type CategoryRow, type FirstReplyRow, type PriorityRow, type Report, type VolumeRow,
  backlogReport, categoryReport, firstReplyReport, priorityReport, volumeReport,
} from "@/lib/api";
import { NOT_RECORDED, orNotRecorded } from "@/lib/format";

export const metadata: Metadata = { title: "Reports" };

// This page stays on the server: report rows hold months and dates, and none may reach the browser.
export default async function Reports() {
  const [volume, backlog, priority, category, firstReply] = await Promise.all([
    volumeReport(), backlogReport(), priorityReport(), categoryReport(), firstReplyReport(),
  ]);
  const crumbs = [{ label: "Service Desk" }, { label: "Reports" }];
  const description = <p className="page-desc">The five reports the Orion desk API provides, drawn as returned.</p>;

  if (!volume.ok || !backlog.ok || !priority.ok || !category.ok || !firstReply.ok) {
    const [problem] = [volume, backlog, priority, category, firstReply].flatMap((result) => result.ok ? [] : [result.problem]);
    return (
      <>
        <PageHeading crumbs={crumbs} title="Reports">{description}</PageHeading>
        <ApiProblemPanel problem={problem} heading="Reports can’t be shown" cannotLoad="the reports can’t load" refused="no reports can be shown" />
      </>
    );
  }

  const { total } = splitTotal(priority.data.rows, "priority");

  return (
    <>
      <PageHeading crumbs={crumbs} title="Reports">
        {description}
        <p className="cap">
          Of the {total.resolved} resolved tickets, {total.csat_missing} have no customer rating, so every CSAT figure on this page counts rated tickets only.
        </p>
      </PageHeading>

      <FirstReplyPanel report={firstReply.data} />
      <BreakdownPanel
        id="priority-report" title="Priority" report={priority.data.report}
        note="Tickets, average first reply, average resolution and average CSAT for each priority."
        rows={priority.data.rows} rowKey="priority" totalLabel="All priorities"
      />
      <BreakdownPanel
        id="category-report" title="Category" report={category.data.report}
        note="The same measures for each category, in API order."
        rows={category.data.rows} rowKey="category" totalLabel="All categories"
      />
      <BacklogAndVolume backlog={backlog.data} volume={volume.data} />
    </>
  );
}

// The row named "All" is the report's total: a figure, never a bar. The reports' grouping sets always return it.
function splitTotal<Row>(rows: Row[], key: keyof Row) {
  const total = rows.find((row) => row[key] === "All") as Row;
  return { total, bars: rows.filter((row) => row !== total) };
}

function ReportPanel({ id, title, report, note, figures, className, children }: {
  id: string; title: string; report: string; note: string; figures?: React.ReactNode; className: string; children: React.ReactNode;
}) {
  return (
    <section className={`panel ${className}`} aria-labelledby={id}>
      <div className="c12">
        <div className="panel-head">
          <h2 id={id}>{title}</h2>
          <span className="panel-meta">API report: {report}</span>
        </div>
        <p className="cap">{note}</p>
        {figures && <p className="figline">{figures}</p>}
      </div>
      {children}
    </section>
  );
}

function HeadlineAverage({ name, color, value, counted, missing, note }: {
  name: string; color: string; value: string | null; counted: number; missing: number; note: string;
}) {
  return (
    <div>
      <Legend items={[{ name, color }]} style={{ marginBottom: 4 }} />
      <div className="big">{orNotRecorded(value)}</div>
      {value !== null && <div className="bv">from {counted} tickets, {missing} not recorded</div>}
      <p className="cap" style={{ margin: "4px 0 0" }}>{note}</p>
    </div>
  );
}

function FirstReplyPanel({ report }: { report: Report<FirstReplyRow> }) {
  const { total, bars } = splitTotal(report.rows, "priority");
  const pairItem = (value: string | null, counted: number, missing: number, color: string, when: string) => ({
    value,
    color,
    text: value === null ? `${when}: ${NOT_RECORDED}` : `${value} when ${when}, from ${counted} tickets, ${missing} not recorded`,
  });

  return (
    <ReportPanel
      id="first-reply-report" title="First reply" report={report.report} className="sub"
      note="First-reply target outcomes for each priority, and average CSAT when the target was met or missed."
    >
      <div className="c4 chart" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <h3 style={{ margin: 0 }}>All priorities</h3>
        <HeadlineAverage
          name="Average CSAT when met" color={SERIES.met}
          value={total.avg_csat_met} counted={total.csat_met_counted} missing={total.csat_met_missing}
          note="Average customer rating on resolved tickets whose first reply came within its target; rated tickets only."
        />
        <HeadlineAverage
          name="Average CSAT when missed" color={SERIES.missed}
          value={total.avg_csat_missed} counted={total.csat_missed_counted} missing={total.csat_missed_missing}
          note="Average customer rating on resolved tickets whose first reply came after its target; rated tickets only."
        />
        <p style={{ margin: 0 }}>
          <strong>{total.tickets} tickets:</strong> {total.met} met, {total.missed} missed, {total.no_first_reply} no first reply, {total.no_target} no target.
        </p>
      </div>

      <Chart
        className="c4" title="Target outcome (tickets)"
        note={`Whether each ticket’s first reply came within its target. Counts all ${total.tickets} tickets; no first reply means no agent has answered yet.`}
        legend={[{ name: "Met", color: SERIES.met }, { name: "Missed", color: SERIES.missed }, { name: "No first reply", color: SERIES.none }]}
      >
        <Bars bars={bars.map((row) => ({
          label: orNotRecorded(row.priority),
          segments: [
            { value: row.met, color: SERIES.met },
            { value: row.missed, color: SERIES.missed },
            { value: row.no_first_reply, color: SERIES.none },
          ],
          text: `${row.met} met · ${row.missed} missed · ${row.no_first_reply} no first reply · ${row.tickets} tickets`,
        }))} />
      </Chart>

      <Chart
        className="c4" title="Average CSAT when met and missed"
        note="Average customer rating, split by whether the first reply met its target. Counts resolved tickets that have a rating."
        legend={[{ name: "When met", color: SERIES.met }, { name: "When missed", color: SERIES.missed }]}
      >
        <PairedBars pairs={bars.map((row) => ({
          label: orNotRecorded(row.priority),
          items: [
            pairItem(row.avg_csat_met, row.csat_met_counted, row.csat_met_missing, SERIES.met, "met"),
            pairItem(row.avg_csat_missed, row.csat_missed_counted, row.csat_missed_missing, SERIES.missed, "missed"),
          ],
        }))} />
      </Chart>
    </ReportPanel>
  );
}

function BreakdownPanel<Row extends PriorityRow | CategoryRow>({ id, title, report, note, rows, rowKey, totalLabel }: {
  id: string; title: string; report: string; note: string; rows: Row[]; rowKey: keyof Row; totalLabel: string;
}) {
  const { total, bars } = splitTotal(rows, rowKey);
  const label = (row: Row) => orNotRecorded(row[rowKey] as string | null);
  const firstReply = (row: Breakdown) => [row.avg_first_response_hours, " h", row.first_response_counted, row.first_response_missing] as const;
  const resolution = (row: Breakdown) => [row.avg_resolution_hours, " h", row.resolution_counted, row.resolution_missing] as const;
  const csat = (row: Breakdown) => [row.avg_csat, "", row.csat_counted, row.csat_missing] as const;

  return (
    <ReportPanel
      id={id} title={title} report={report} note={note} className="sub"
      figures={<>
        <strong>{totalLabel}:</strong> {total.tickets} tickets, {total.resolved} resolved, {total.unresolved} unresolved
        {" · "}first reply {averageText(...firstReply(total))}
        {" · "}resolution {averageText(...resolution(total))}
        {" · "}CSAT {averageText(...csat(total))}
      </>}
    >
      <Chart
        className="c3" title="Tickets"
        note={`Counts all ${total.tickets} tickets. Unresolved means open, in progress or pending: ${total.unresolved}.`}
        legend={[{ name: "Resolved", color: SERIES.resolved }, { name: "Unresolved", color: SERIES.unresolved }]}
      >
        <Bars bars={bars.map((row) => ({
          label: label(row),
          segments: [{ value: row.resolved, color: SERIES.resolved }, { value: row.unresolved, color: SERIES.unresolved }],
          text: `${row.resolved} resolved · ${row.unresolved} unresolved · ${row.tickets} tickets`,
        }))} />
      </Chart>
      <Chart
        className="c3" title="Average first reply (h)"
        note={`Hours each ticket waited for its first agent reply. Counts the ${total.first_response_counted} tickets with a reply; the ${total.first_response_missing} without one are left out.`}
      >
        <Bars bars={bars.map((row) => averageBar(label(row), ...firstReply(row)))} />
      </Chart>
      <Chart
        className="c3" title="Average resolution (h)"
        note={`Hours each ticket took to resolve. Counts the ${total.resolution_counted} resolved tickets; the ${total.resolution_missing} unresolved are left out.`}
      >
        <Bars bars={bars.map((row) => averageBar(label(row), ...resolution(row)))} />
      </Chart>
      <Chart
        className="c3" title="Average CSAT"
        note={`Average customer rating. Counts the ${total.csat_counted} resolved tickets that have a rating.`}
      >
        <Bars bars={bars.map((row) => averageBar(label(row), ...csat(row)))} />
      </Chart>
    </ReportPanel>
  );
}

// Backlog and volume share one tickets scale, so their bars compare directly.
function BacklogAndVolume({ backlog, volume }: { backlog: Report<BacklogRow>; volume: Report<VolumeRow> }) {
  const backlogSplit = splitTotal(backlog.rows, "status");
  const volumeSplit = splitTotal(volume.rows, "month");
  const backlogTotal = backlogSplit.total;
  const volumeTotal = volumeSplit.total;

  const backlogBars: Bar[] = backlogSplit.bars.map((row) => ({
    label: <StatusPill status={row.status} />,
    segments: [{ value: row.tickets, color: SERIES.single }],
    text: (
      <>
        <strong>{row.tickets} tickets</strong> · {row.no_first_reply} no first reply · {row.no_first_reply_past_target} no first reply past target
        {" · "}average age {averageText(row.avg_age_hours, " h", row.age_counted, row.age_missing)}
      </>
    ),
  }));
  // Months are dates: the bars carry no labels, and the month itself is never read.
  const volumeBars: Bar[] = volumeSplit.bars.map((row) => ({
    segments: [{ value: row.resolved, color: SERIES.resolved }, { value: row.unresolved, color: SERIES.unresolved }],
    text: `${row.resolved} resolved · ${row.unresolved} unresolved · ${row.tickets} tickets`,
  }));
  const scale = largest([...backlogBars, ...volumeBars]);

  return (
    <>
      <ReportPanel
        id="backlog-report" title="Backlog" report={backlog.report} className="c6"
        note="Unresolved tickets for each status, in API order."
        figures={<>
          <strong>All statuses:</strong> {backlogTotal.tickets} tickets · {backlogTotal.no_first_reply} no first reply
          {" · "}{backlogTotal.no_first_reply_past_target} no first reply past target
          {" · "}average age {averageText(backlogTotal.avg_age_hours, " h", backlogTotal.age_counted, backlogTotal.age_missing)}
        </>}
      >
        <Chart
          title="Tickets" style={{ marginTop: 16 }}
          note={`Unresolved tickets only, ${backlogTotal.tickets} in all, grouped by their status.`}
        >
          <Bars bars={backlogBars} scale={scale} />
        </Chart>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 12 }}>
          <Definition term="No first reply">unresolved tickets no agent has answered yet, {backlogTotal.no_first_reply} of the {backlogTotal.tickets}.</Definition>
          <Definition term="No first reply past target">of those {backlogTotal.no_first_reply}, the {backlogTotal.no_first_reply_past_target} that have waited longer than their first-reply target.</Definition>
          <Definition term="Average age">average hours each unresolved ticket has been open, across all {backlogTotal.tickets}.</Definition>
        </div>
      </ReportPanel>

      <ReportPanel
        id="volume-report" title="Volume" report={volume.report} className="c6"
        note="One bar per calendar month, in API order."
        figures={<><strong>All months:</strong> {volumeTotal.tickets} tickets, {volumeTotal.resolved} resolved, {volumeTotal.unresolved} unresolved</>}
      >
        <Chart
          title="Tickets" style={{ marginTop: 16 }}
          note={`Counts all ${volumeTotal.tickets} tickets; each bar splits one month’s tickets into resolved and unresolved.`}
          legend={[{ name: "Resolved", color: SERIES.resolved }, { name: "Unresolved", color: SERIES.unresolved }]}
        >
          <Bars bars={volumeBars} scale={scale} />
        </Chart>
      </ReportPanel>
    </>
  );
}

function Definition({ term, children }: { term: string; children: React.ReactNode }) {
  return <p className="cap" style={{ margin: 0 }}><strong style={{ color: "var(--text)" }}>{term}:</strong> {children}</p>;
}
