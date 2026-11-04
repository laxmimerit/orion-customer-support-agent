import type { Metadata } from "next";
import Link from "next/link";

import { ApiProblemPanel, PageHead, PriorityTile, StatusPill } from "@/components/desk";
import { BackIcon } from "@/components/icons";
import { Queue, QueueSearch } from "@/components/queue";
import {
  type BacklogRow,
  type FirstReplyRow,
  type PriorityRow,
  type Report,
  type Result,
  type SearchHit,
  type SearchResults,
  backlogReport,
  firstReplyReport,
  priorityReport,
  SEARCH_LIMIT,
  searchDesk,
  ticketPage,
} from "@/lib/api";
import { NOT_RECORDED, hoursShort, orNotRecorded, percent, plural, sentenceCase } from "@/lib/format";
import "./queue.css";

export const metadata: Metadata = { title: "Ticket queue" };

const PAGE_SIZE = 25;
const QUEUE_DESCRIPTION = "Work from the top: tickets are ranked by priority, then open before in progress.";

function oneValue(value: string | string[] | undefined) {
  return typeof value === "string" ? value : "";
}

export default async function TicketQueue({ searchParams }: {
  searchParams: Promise<{ page?: string | string[]; q?: string | string[] }>;
}) {
  const params = await searchParams;
  const query = oneValue(params.q).trim();
  const requested = Number(oneValue(params.page) || "1");
  const page = Number.isInteger(requested) && requested >= 1 ? Math.min(requested, 100_000) : 1;

  const reports = [backlogReport(), firstReplyReport(), priorityReport()] as const;

  if (query) {
    const [results, backlog, firstReply, priority] = await Promise.all([searchDesk(query), ...reports]);
    return (
      <>
        <QueueSearch key={query} initial={query} />
        <main className="page">
          <PageHead title="Ticket queue" description={QUEUE_DESCRIPTION} />
          <Pulse backlog={backlog} firstReply={firstReply} priority={priority} />
          <SearchSection query={query} results={results} />
        </main>
      </>
    );
  }

  const [tickets, backlog, firstReply, priority] = await Promise.all([ticketPage(page, PAGE_SIZE), ...reports]);
  const pulse = <Pulse backlog={backlog} firstReply={firstReply} priority={priority} />;

  if (!tickets.ok) {
    return (
      <>
        <QueueSearch initial="" />
        <main className="page">
          <PageHead title="Ticket queue" description={QUEUE_DESCRIPTION} />
          {pulse}
          <ApiProblemPanel problem={tickets.problem} retryTarget="the ticket queue" />
        </main>
      </>
    );
  }

  // The key starts each page fresh, so a filter or selection never carries over to other tickets.
  return <Queue key={page} {...tickets.data} description={QUEUE_DESCRIPTION}>{pulse}</Queue>;
}

// The total row of a report, or null when the report failed or has none.
function allRow<Row>(result: Result<Report<Row>>, key: keyof Row) {
  return result.ok ? result.data.rows.find((row) => row[key] === "All") ?? null : null;
}

// The order the board lists the backlog's statuses in, with the class of each one's colour.
const BACKLOG_STATUSES: [string, string][] = [["open", "is-open"], ["pending", "is-pending"], ["in progress", "is-progress"]];

function backlogTone(status: string) {
  return BACKLOG_STATUSES.find(([name]) => name === status)?.[1] ?? "is-other";
}

function backlogOrder(status: string) {
  const at = BACKLOG_STATUSES.findIndex(([name]) => name === status);
  return at === -1 ? BACKLOG_STATUSES.length : at;
}

function score(value: string | null) {
  return value === null ? NOT_RECORDED : Number(value).toFixed(2);
}

function Segment({ tone, count }: { tone: string; count: number }) {
  return count > 0 ? <span className={`queue-seg ${tone}`} style={{ flexGrow: count }} /> : null;
}

function Missing() {
  return <span className="queue-tile-value is-missing">Did not load</span>;
}

// Desk-wide figures. Each tile stands alone, so one failed report leaves the others in place.
function Pulse({ backlog, firstReply, priority }: {
  backlog: Result<Report<BacklogRow>>;
  firstReply: Result<Report<FirstReplyRow>>;
  priority: Result<Report<PriorityRow>>;
}) {
  const waiting = allRow(backlog, "status");
  const replies = allRow(firstReply, "priority");
  const desk = allRow(priority, "priority");
  const statuses = backlog.ok
    ? backlog.data.rows
      .filter((row) => row.status !== "All" && row.tickets > 0)
      .sort((a, b) => backlogOrder(a.status) - backlogOrder(b.status))
    : [];

  return (
    <section className="queue-pulse" aria-label="Desk pulse, all tickets">
      <div className="queue-tile">
        <span className="queue-tile-label">Unresolved · desk-wide</span>
        {waiting ? (
          <>
            <span className="queue-tile-figure">
              <span className="queue-tile-value">{waiting.tickets}</span>
              <span className="queue-tile-note">
                avg age {waiting.avg_age_hours === null
                  ? NOT_RECORDED : plural(Math.round(Number(waiting.avg_age_hours) / 24), "day")}
              </span>
            </span>
            <div className="queue-bar" role="img"
              aria-label={statuses.map((row) => `${sentenceCase(row.status)} ${row.tickets}`).join(", ")}>
              {statuses.map((row) => (
                <Segment key={row.status} tone={backlogTone(row.status)} count={row.tickets} />
              ))}
            </div>
            <span className="queue-legend">
              {statuses.map((row) => (
                <span key={row.status}>
                  <span className={`queue-key ${backlogTone(row.status)}`} aria-hidden="true" />
                  {sentenceCase(row.status)} {row.tickets}
                </span>
              ))}
            </span>
          </>
        ) : <Missing />}
      </div>

      <div className="queue-tile">
        <span className="queue-tile-label">No first reply yet</span>
        {waiting ? (
          <>
            <span className="queue-tile-figure">
              <span className="queue-tile-value">{waiting.no_first_reply}</span>
              <span className="queue-tile-note is-warning">{waiting.no_first_reply_past_target} past target</span>
            </span>
            <WaitDots total={waiting.no_first_reply} late={waiting.no_first_reply_past_target} />
          </>
        ) : <Missing />}
      </div>

      <div className="queue-tile">
        <span className="queue-tile-label">First reply on target</span>
        {replies ? (
          <>
            <span className="queue-tile-figure">
              <span className="queue-tile-value">{percent(replies.met, replies.tickets) ?? NOT_RECORDED}</span>
              <span className="queue-tile-note">
                avg {desk?.avg_first_response_hours ? hoursShort(desk.avg_first_response_hours) : NOT_RECORDED}
              </span>
            </span>
            <div className="queue-bar" role="img"
              aria-label={`${replies.met} met, ${replies.missed} missed, ${replies.no_first_reply} not replied`}>
              <Segment tone="is-met" count={replies.met} />
              <Segment tone="is-missed" count={replies.missed} />
              <Segment tone="is-waiting" count={replies.no_first_reply + replies.no_target} />
            </div>
            <span className="queue-tile-line">{replies.met} met · {replies.missed} missed</span>
          </>
        ) : <Missing />}
      </div>

      <div className="queue-tile">
        <span className="queue-tile-head">
          <span className="queue-tile-label">Satisfaction</span>
          <Link href="/reports">Why it dips</Link>
        </span>
        {desk ? (
          <span className="queue-tile-figure">
            <span className="queue-tile-value">{score(desk.avg_csat)}</span>
            <span className="queue-tile-note">/ 5 · {desk.csat_counted} rated</span>
          </span>
        ) : <Missing />}
        {replies && (
          <span className="queue-tile-line">
            <strong className="is-good">{score(replies.avg_csat_met)}</strong> when the first reply is on time
            {" · "}
            <strong className="is-late">{score(replies.avg_csat_missed)}</strong> when late
          </span>
        )}
      </div>
    </section>
  );
}

// One dot per waiting ticket, filled when past target. A long backlog is drawn to scale at 48 dots.
function WaitDots({ total, late }: { total: number; late: number }) {
  const dots = Math.min(total, 48);
  const filled = total > 0 ? Math.round((late / total) * dots) : 0;
  return (
    <div className="queue-dots" role="img" aria-label={`${late} of ${total} past target`}>
      {Array.from({ length: dots }, (_, index) => (
        <span key={index} className={`queue-dot${index < filled ? " is-late" : ""}`} />
      ))}
    </div>
  );
}

function SearchSection({ query, results }: { query: string; results: Result<SearchResults> }) {
  const back = <Link className="button" href="/"><BackIcon />Back to the queue</Link>;

  if (!results.ok) {
    return (
      <section className="queue-results" aria-labelledby="queue-results-title">
        <div className="queue-results-head">
          <h2 id="queue-results-title">Results for “{query}”</h2>
          {back}
        </div>
        <ApiProblemPanel problem={results.problem} title="The desk API did not return these results" retryTarget="the search results" />
      </section>
    );
  }

  const { items } = results.data;
  return (
    <section className="card queue-results" aria-labelledby="queue-results-title">
      <div className="card-head">
        <h2 id="queue-results-title">Results for “{query}” <span>· {items.length === SEARCH_LIMIT ? `Top ${SEARCH_LIMIT} results` : plural(items.length, "result")}</span></h2>
        {back}
      </div>
      {items.length ? (
        <ul className="queue-hits">
          {items.map((hit) => <li key={`${hit.kind}-${hit.id}`}><Hit hit={hit} /></li>)}
        </ul>
      ) : (
        <div className="empty">
          <p className="empty-title">Nothing in the desk matches “{query}”</p>
          <p className="empty-hint">Check the ticket ID, or try other words.</p>
        </div>
      )}
    </section>
  );
}

function Hit({ hit }: { hit: SearchHit }) {
  const category = hit.category ? sentenceCase(hit.category) : NOT_RECORDED;

  if (hit.kind === "article") {
    return (
      <Link className="row queue-hit" href={`/knowledge/${encodeURIComponent(hit.id)}`} prefetch={false}>
        <span className="pill">Article</span>
        <span className="row-text">
          <span className="row-title">{orNotRecorded(hit.title)}</span>
          <span className="row-sub"><strong>{hit.id}</strong> · {category}</span>
        </span>
      </Link>
    );
  }

  return (
    <Link className="row queue-hit" href={`/tickets/${encodeURIComponent(hit.id)}`} prefetch={false}>
      <PriorityTile priority={hit.priority} />
      <span className="row-text">
        <span className="row-title">{orNotRecorded(hit.title)}</span>
        <span className="row-sub"><strong>{hit.id}</strong> · {category}</span>
      </span>
      <StatusPill status={hit.status} fixed />
    </Link>
  );
}
