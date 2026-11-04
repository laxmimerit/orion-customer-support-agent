// The charts on the reports page: plain HTML, CSS and SVG, rendered on the server. Each section takes the
// report's raw rows, separates the total row, and draws only what the rows say. A null average draws no mark.
import { Fragment } from "react";

import { ApiProblemPanel, PriorityTile } from "@/components/desk";
import { ScrollBox, WhenTables } from "@/components/report-tables";
import type { ApiProblem, BacklogRow, CategoryRow, FirstReplyRow, PriorityRow, VolumeRow } from "@/lib/api";
import { NOT_RECORDED, plural, sentenceCase } from "@/lib/format";
import {
  METRICS, backlogHeadline, categoryHeadline, categoryName, categorySpotlight, daysText, firstReplyHeadline, hoursText, num,
  percentText, periodHeadline, periodsFrom, priorityHeadline, priorityName, ratingAxis, ratingCountNote, ratingGap, ratingLabel,
  ratingText, ratio, soleHighest, soleLowest, splitTotal, stripNotes, undatedTickets, type Kpi, type Metric, type StripNote,
} from "@/lib/report-text";

function ReportCard({ id, eyebrow, title, children }: {
  id: string; eyebrow: string; title: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <section className="card rp-card" aria-labelledby={id}>
      <div className="rp-card-head">
        <span className="rp-eyebrow">{eyebrow}</span>
        <h2 id={id} className="rp-title">{title}</h2>
      </div>
      {children}
    </section>
  );
}

// One report failed: its section says so and the rest of the page stays. The hidden words keep each failed
// section's name apart in a screen reader's list of regions.
export function ReportProblem({ id, eyebrow, problem }: { id: string; eyebrow: string; problem: ApiProblem }) {
  return (
    <ReportCard id={id} eyebrow={eyebrow} title={<>This report did not load<span className="visually-hidden">: {eyebrow}</span></>}>
      <ApiProblemPanel problem={problem} title="The desk API did not return this report" retryTarget={`the “${eyebrow}” report`} />
    </ReportCard>
  );
}

function NoRows() {
  return <div className="empty"><p className="empty-title">Nothing to report yet</p></div>;
}

function Key({ tone, children }: { tone: string; children: React.ReactNode }) {
  return <span className="rp-key"><span className={`rp-key-dot ${tone}`} aria-hidden="true" />{children}</span>;
}

export function KpiStrip({ kpis }: { kpis: Kpi[] }) {
  return (
    <section className="rp-kpis" aria-label="Headline numbers">
      {kpis.map((kpi) => (
        <div key={kpi.label} className="rp-kpi">
          <span className="rp-kpi-label">{kpi.label}</span>
          {kpi.value === null
            ? <span className="rp-kpi-none">{NOT_RECORDED}</span>
            : <span className="rp-kpi-figure"><span className="rp-kpi-value">{kpi.value}</span><span className="rp-kpi-unit">{kpi.unit}</span></span>}
        </div>
      ))}
    </section>
  );
}

// Ratings run from 1 to 5.
function ratingPosition(rating: number) {
  return Math.min(100, Math.max(0, ((rating - 1) / 4) * 100));
}

// Rating points: value labels closer than this would touch, so the late one drops under the line.
const BELL_LABEL_CLEARANCE = 0.35;

function BellMark({ value, tone, label, count, under = false }: {
  value: number; tone: string; label: string; count: number; under?: boolean;
}) {
  const left = `${ratingPosition(value).toFixed(2)}%`;
  const text = ratingLabel(value);
  return (
    <>
      <span className={`rp-dot rp-mark ${tone}`} style={{ left }} title={`${label} · ${text} from ${count} ratings`} />
      <span className={`rp-bell-value ${tone}${under ? " is-under" : ""}`} style={{ left }}>{text}</span>
    </>
  );
}

function Dumbbell({ row }: { row: FirstReplyRow }) {
  const name = priorityName(row.priority);
  const met = num(row.avg_csat_met);
  const missed = num(row.avg_csat_missed);
  const gaps = [missed === null && "Late", met === null && "On time"].filter(Boolean);
  const tooClose = met !== null && missed !== null && Math.abs(met - missed) < BELL_LABEL_CLEARANCE;
  return (
    <div className="rp-bell">
      <span className="rp-bell-name">{name}</span>
      <div className="rp-bell-plot">
        <div className="rp-bell-rule" />
        {met !== null && missed !== null && (
          <div className={`rp-bell-line${met < missed ? " is-reversed" : ""}`} style={{
            left: `${ratingPosition(Math.min(met, missed)).toFixed(2)}%`,
            width: `${Math.abs(ratingPosition(met) - ratingPosition(missed)).toFixed(2)}%`,
          }} />
        )}
        {missed !== null && <BellMark value={missed} tone="is-amber" label={`${name} · late`} count={row.csat_missed_counted} under={tooClose} />}
        {met !== null && <BellMark value={met} tone="is-teal" label={`${name} · on time`} count={row.csat_met_counted} />}
        {gaps.length > 0 && <span className="rp-bell-none">{gaps.join(" and ")}: {NOT_RECORDED}</span>}
      </div>
    </div>
  );
}

function HeroTile({ tone, label, value }: { tone: string; label: string; value: string | null }) {
  return (
    <div className={`rp-hero-tile ${tone}`}>
      <div className="rp-hero-tile-label">{label}</div>
      <div className={`rp-hero-tile-value${num(value) === null ? " is-none" : ""}`}>{ratingText(value)}</div>
    </div>
  );
}

export function FirstReplyFinding({ report }: { report: FirstReplyRow[] }) {
  const { total, rows } = splitTotal(report, "priority");
  const gap = ratingGap(total);
  const alt = rows.map((row) => `${priorityName(row.priority)} ${ratingText(row.avg_csat_missed)} versus ${ratingText(row.avg_csat_met)}.`);
  return (
    <section className="card rp-hero" aria-labelledby="rp-finding-title">
      <div className="rp-hero-lead">
        <span className="rp-eyebrow is-teal">First reply and satisfaction</span>
        <div className="rp-hero-claim">
          {gap
            ? <span className={`rp-hero-number${gap.hundredths < 0 ? " is-down" : ""}`} aria-hidden="true">{gap.text}</span>
            : <span className="rp-hero-none" aria-hidden="true">{NOT_RECORDED}</span>}
          <h2 id="rp-finding-title" className="rp-hero-title">
            <span className="visually-hidden">{gap ? `${gap.spoken} ` : `${NOT_RECORDED}: `}</span>
            rating points when the first reply is late
          </h2>
        </div>
        <div className="rp-hero-tiles">
          <HeroTile tone="is-teal" label="On time" value={total?.avg_csat_met ?? null} />
          <HeroTile tone="is-amber" label="Late" value={total?.avg_csat_missed ?? null} />
        </div>
        {total && <span className="rp-note">{ratingCountNote(total)}</span>}
      </div>
      <div className="rp-hero-chart">
        {rows.length === 0 ? <NoRows /> : (
          <>
            <div className="rp-keys is-end">
              <Key tone="is-amber">Late</Key>
              <Key tone="is-teal">On time</Key>
            </div>
            <div role="img" aria-label={`Average rating, late versus on-time first reply. ${alt.join(" ")}`}>
              {rows.map((row) => <Dumbbell key={row.priority ?? "none"} row={row} />)}
              <div className="rp-bell-axis">
                <span className="rp-bell-spacer" />
                <div className="rp-bell-ticks">
                  {[1, 2, 3, 4, 5].map((tick) => <span key={tick} style={{ left: `${ratingPosition(tick)}%` }}>{tick}</span>)}
                </div>
              </div>
            </div>
          </>
        )}
        <WhenTables>
          <ScrollBox className="rp-table-box" label="Average rating by priority table">
            <table className="rp-table">
              <caption className="visually-hidden">Average rating by priority, on-time and late first reply</caption>
              <thead><tr><th scope="col">Priority</th><th scope="col">On time</th><th scope="col">Ratings</th><th scope="col">Late</th><th scope="col">Ratings</th></tr></thead>
              <tbody>
                {report.map((row) => (
                  <tr key={row.priority ?? "none"}>
                    <th scope="row">{priorityName(row.priority)}</th>
                    <td>{ratingText(row.avg_csat_met)}</td>
                    <td className="is-soft">{row.csat_met_counted}</td>
                    <td>{ratingText(row.avg_csat_missed)}</td>
                    <td className="is-soft">{row.csat_missed_counted}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollBox>
        </WhenTables>
      </div>
    </section>
  );
}

// Room above a bar for its value label. A bar's limit is its chart's CSS height less this; the phone
// layout of .rp-periods keeps the limit and spends its extra height on the average tag.
const BAR_HEADROOM = 38;
const PERIOD_BAR_MAX = 200 - BAR_HEADROOM;

export function UnresolvedByPeriod({ report }: { report: VolumeRow[] }) {
  const { total, rows } = splitTotal(report, "month");
  const periods = periodsFrom(rows);
  const undated = undatedTickets(rows);
  const average = total ? ratio(total.unresolved, total.tickets) : null;
  const top = soleHighest(periods, (period) => period.share);
  const peak = Math.max(average ?? 0, ...periods.map((period) => period.share ?? 0));
  const pxPerShare = peak > 0 ? PERIOD_BAR_MAX / peak : 0;
  const barPx = (share: number) => Math.round(share * pxPerShare);
  const alt = periods.map((period) => `Period ${period.n} ${percentText(period.share, 1)}, ${period.unresolved} of ${period.tickets}`).join("; ");
  return (
    <ReportCard id="rp-volume-title" eyebrow="Unresolved by period" title={periodHeadline(periods)}>
      {periods.length === 0 ? <NoRows /> : (
        <ScrollBox className="rp-scroll" label="Unresolved share by period chart">
          <div className="rp-periods-box" style={{ "--rp-cols": periods.length } as React.CSSProperties}>
            <div className="rp-periods" role="img"
              aria-label={`Share of each period's tickets still unresolved: ${alt}${average === null ? "" : `; average ${percentText(average, 1)}`}.`}>
              {average !== null && (
                <>
                  <div className="rp-avg-line" style={{ bottom: `${barPx(average)}px` }} />
                  <span className="rp-avg-tag" style={{ bottom: `${barPx(average) + 4}px` }}>avg {percentText(average, 1)}</span>
                </>
              )}
              {periods.map((period) => (
                <div key={period.n} className="rp-period">
                  <span className={`rp-period-value${period === top ? " is-top" : ""}${period.share === null ? " is-none" : ""}`}>{percentText(period.share, 1)}</span>
                  {period.share !== null && (
                    <span className={`rp-period-bar rp-mark${period === top ? " is-top" : ""}`}
                      style={{ height: `${barPx(period.share)}px` }}
                      title={`Period ${period.n} · ${period.unresolved} of ${period.tickets} unresolved`} />
                  )}
                </div>
              ))}
            </div>
            <div className="rp-period-labels" aria-hidden="true">
              {periods.map((period) => (
                <div key={period.n}>
                  <span className="rp-period-n">{period.n}</span>
                  <span className="rp-period-count">{period.unresolved}/{period.tickets}</span>
                </div>
              ))}
            </div>
          </div>
        </ScrollBox>
      )}
      <span className="rp-note">
        Periods in report order; dates are left out.
        {undated > 0 && ` ${plural(undated, "ticket")} with no recorded period ${undated === 1 ? "is" : "are"} left out of the bars.`}
      </span>
    </ReportCard>
  );
}

const RING_RADIUS = 38;
const RING_LENGTH = 2 * Math.PI * RING_RADIUS;

function Ring({ row, wait }: { row: FirstReplyRow; wait?: string }) {
  const share = ratio(row.met, row.tickets);
  const name = priorityName(row.priority);
  const waits = wait === undefined ? "" : `, average wait ${wait}`;
  return (
    <div className="rp-ring">
      <div className="rp-ring-dial" role="img" aria-label={`${name}: ${row.met} of ${row.tickets} on target${waits}`}>
        <svg width="96" height="96" viewBox="0 0 96 96" aria-hidden="true">
          <circle className="rp-ring-track" cx="48" cy="48" r={RING_RADIUS} />
          {share !== null && share > 0 && (
            <circle className="rp-ring-fill" cx="48" cy="48" r={RING_RADIUS} transform="rotate(-90 48 48)"
              strokeDasharray={`${(share * RING_LENGTH).toFixed(1)} ${RING_LENGTH.toFixed(1)}`} />
          )}
        </svg>
        <span className={`rp-ring-value${share === null ? " is-none" : ""}`} aria-hidden="true">{percentText(share)}</span>
      </div>
      <PriorityTile priority={row.priority} />
      {wait !== undefined && <span className="rp-ring-wait">waits <strong>{wait}</strong></span>}
    </div>
  );
}

// `waits` is the priority report's rows, left out when that report failed.
export function FirstReplyRings({ report, waits }: { report: FirstReplyRow[]; waits?: PriorityRow[] }) {
  const { total, rows } = splitTotal(report, "priority");
  const waitFor = (row: FirstReplyRow) => {
    if (!waits) return undefined;
    return hoursText(waits.find((item) => item.priority === row.priority)?.avg_first_response_hours ?? null);
  };
  return (
    <ReportCard id="rp-first-reply-title" eyebrow="First reply on target" title={firstReplyHeadline(total, rows)}>
      {rows.length === 0 ? <NoRows /> : (
        <div className="rp-rings">
          {rows.map((row) => <Ring key={row.priority ?? "none"} row={row} wait={waitFor(row)} />)}
        </div>
      )}
      <span className="rp-note">Ring shows the share of tickets whose first reply met target.</span>
    </ReportCard>
  );
}

// A server component cannot measure text, so note widths are estimated: the strip's width on a 375px
// phone, and the average character of .rp-strip-note's 12px bold text.
const NOTE_STRIP_WIDTH = 300;
const NOTE_CHAR_WIDTH = 6.8;
const NOTE_GAP = 6;

// Lays notes out for a phone's strip: one that would touch another drops below the line.
function placeNotes(notes: StripNote[]) {
  const taken: [number, number][] = [];
  return notes.map((note) => {
    const width = Math.ceil(note.text.length * NOTE_CHAR_WIDTH);
    const centre = Math.min(NOTE_STRIP_WIDTH - width / 2, Math.max(width / 2, (note.position / 100) * NOTE_STRIP_WIDTH));
    const start = centre - width / 2 - NOTE_GAP;
    const end = centre + width / 2 + NOTE_GAP;
    const under = taken.some(([from, to]) => start < to && from < end);
    if (!under) taken.push([start, end]);
    return { ...note, width, under };
  });
}

function Strip({ metric, rows, spotlight }: { metric: Metric; rows: CategoryRow[]; spotlight: CategoryRow | null }) {
  const values = rows.map(metric.read).filter((value) => value !== null);
  const [low, high] = values.length > 0 ? metric.axis(values) : [0, 1];
  const at = (value: number) => ((value - low) / (high - low)) * 100;
  const most = Math.max(...rows.map((row) => row.tickets), 1);
  const size = (tickets: number) => 8 + (tickets / most) * 10;
  const alt = rows.map((row) => {
    const value = metric.read(row);
    return `${categoryName(row.category)} ${value === null ? NOT_RECORDED : metric.text(value)}`;
  }).join(", ");
  return (
    <div className="rp-strip">
      <div className="rp-strip-head">
        <span className="rp-strip-name">{metric.label}</span>
        <span className="rp-strip-range">{values.length > 0 ? metric.range(low, high) : NOT_RECORDED}</span>
      </div>
      <div className="rp-strip-plot" role="img" aria-label={`${metric.label} by category: ${alt}`}>
        <div className="rp-strip-rule" />
        {[...rows].sort((a, b) => b.tickets - a.tickets).map((row) => {
          const value = metric.read(row);
          if (value === null) return null;
          const name = categoryName(row.category);
          const dot = `${size(row.tickets).toFixed(1)}px`;
          return (
            <span key={row.category ?? "none"} className={`rp-strip-dot rp-mark${row === spotlight ? " is-spot" : ""}`}
              title={`${name} · ${metric.text(value)} · ${row.tickets} tickets`}
              style={{ left: `${at(value).toFixed(2)}%`, width: dot, height: dot }} />
          );
        })}
        {values.length > 0 && placeNotes(stripNotes(metric, rows, spotlight, at)).map((note) => (
          <span key={note.text} className={`rp-strip-note ${note.spotlit ? "is-amber" : "is-teal"}${note.under ? " is-under" : ""}`} style={{
            width: `${note.width}px`,
            left: `clamp(0px, calc(${note.position.toFixed(2)}% - ${note.width / 2}px), calc(100% - ${note.width}px))`,
          }}>{note.text}</span>
        ))}
      </div>
    </div>
  );
}

export function CategoryStrips({ report }: { report: CategoryRow[] }) {
  const { rows } = splitTotal(report, "category");
  const spotlight = categorySpotlight(rows);
  return (
    <ReportCard id="rp-category-title" eyebrow="Categories" title={categoryHeadline(rows)}>
      {rows.length === 0 ? <NoRows /> : (
        <>
          <div className="rp-strips">
            {METRICS.map((metric) => <Strip key={metric.label} metric={metric} rows={rows} spotlight={spotlight} />)}
          </div>
          <div className="rp-keys">
            {spotlight && <Key tone="is-amber">{categoryName(spotlight.category)}</Key>}
            <Key tone="is-teal">{spotlight ? "Other categories" : "Categories"}</Key>
            <span className="rp-key-note">Dot size = tickets</span>
          </div>
        </>
      )}
      <WhenTables>
        <ScrollBox className="rp-table-box" label="Averages by category table">
          <table className="rp-table">
            <caption className="visually-hidden">Tickets, first reply, resolution and rating by category</caption>
            <thead><tr><th scope="col">Category</th><th scope="col">Tickets</th><th scope="col">First reply</th><th scope="col">Resolution</th><th scope="col">Rating</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.category ?? "none"}>
                  <th scope="row">{categoryName(row.category)}</th>
                  <td>{row.tickets}</td>
                  <td>{hoursText(row.avg_first_response_hours)}</td>
                  <td>{hoursText(row.avg_resolution_hours)}</td>
                  <td>{ratingText(row.avg_csat)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollBox>
      </WhenTables>
    </ReportCard>
  );
}

const STATUS_SQUARES: Record<string, string> = { open: "is-open", pending: "is-pending", "in progress": "is-progress" };

function statusTone(status: string) {
  return STATUS_SQUARES[status.toLowerCase()] ?? "is-other";
}

function BacklogKeyItem({ tone, count, label, sub }: { tone: string; count: number; label: string; sub: string }) {
  return (
    <div className="rp-backlog-item">
      <span className={`rp-square-key ${tone}`} aria-hidden="true" />
      <span className="rp-backlog-text">
        <span className="rp-backlog-n">{count}</span>
        <span className="rp-backlog-label">{label}</span>
        <span className="rp-backlog-sub">{sub}</span>
      </span>
    </div>
  );
}

export function BacklogWaffle({ report }: { report: BacklogRow[] }) {
  const { total, rows } = splitTotal(report, "status");
  const counted = (key: "tickets" | "no_first_reply" | "no_first_reply_past_target") =>
    total?.[key] ?? rows.reduce((sum, row) => sum + row[key], 0);
  const pastTarget = counted("no_first_reply_past_target");
  const noReply = counted("no_first_reply");
  const waiting = counted("tickets");
  const alt = `${waiting} unresolved tickets, one square each: ${rows.map((row) => `${row.tickets} ${row.status}`).join(", ")}. `
    + `${pastTarget} ${pastTarget === 1 ? "has" : "have"} no first reply and ${pastTarget === 1 ? "is" : "are"} past target.`;
  return (
    <ReportCard id="rp-backlog-title" eyebrow="Backlog" title={backlogHeadline(total)}>
      {rows.length === 0 ? <NoRows /> : (
        <>
          <div className="rp-waffle" role="img" aria-label={alt}>
            {rows.flatMap((row) => Array.from({ length: row.tickets }, (_, index) => (
              <span key={`${row.status}-${index}`} className={`rp-square ${index < row.no_first_reply_past_target ? "is-late" : statusTone(row.status)}`} />
            )))}
          </div>
          <div className="rp-backlog-key">
            {rows.map((row) => {
              const age = daysText(row.avg_age_hours);
              return (
                <BacklogKeyItem key={row.status} tone={statusTone(row.status)} count={row.tickets}
                  label={sentenceCase(row.status)} sub={age ? `${age} old` : `Age: ${NOT_RECORDED}`} />
              );
            })}
            <BacklogKeyItem tone="is-late" count={pastTarget} label="No first reply"
              sub={noReply === pastTarget ? "past target" : `past target, of ${noReply} unanswered`} />
          </div>
          {total && total.age_missing > 0 && (
            <span className="rp-note">Average age from {total.age_counted} tickets; {total.age_missing} have no recorded age.</span>
          )}
        </>
      )}
    </ReportCard>
  );
}

const WAIT_BAR_MAX = 170 - BAR_HEADROOM;

function WaitBars({ rows }: { rows: PriorityRow[] }) {
  const most = Math.max(...rows.map((row) => num(row.avg_first_response_hours) ?? 0));
  const alt = rows.map((row) => `${priorityName(row.priority)} ${hoursText(row.avg_first_response_hours)}`).join(", ");
  return (
    <div className="rp-half">
      <span className="rp-half-title">Average wait for a first reply</span>
      <div className="rp-waits" role="img" aria-label={`Average first reply: ${alt}.`}>
        {rows.map((row) => {
          const hours = num(row.avg_first_response_hours);
          const text = hoursText(row.avg_first_response_hours);
          return (
            <div key={row.priority ?? "none"} className="rp-wait">
              <span className={`rp-wait-value${hours === null ? " is-none" : ""}`}>{text}</span>
              {hours !== null && (
                <span className="rp-wait-bar rp-mark" title={`${priorityName(row.priority)} · ${text}`}
                  style={{ height: `${most > 0 ? Math.max(4, Math.round((hours / most) * WAIT_BAR_MAX)) : 4}px` }} />
              )}
            </div>
          );
        })}
      </div>
      <PriorityLabels rows={rows} />
    </div>
  );
}

function PriorityLabels({ rows }: { rows: PriorityRow[] }) {
  return (
    <div className="rp-priority-labels" aria-hidden="true">
      {rows.map((row) => <span key={row.priority ?? "none"}>{priorityName(row.priority)}</span>)}
    </div>
  );
}

const RATING_PLOT = 126;
const RATING_FLOOR = 10;
// .rp-rating-dot is 18px, so its radius centres it on the rating; its value sits 5px above the dot.
const RATING_DOT_RADIUS = 9;
const RATING_VALUE_LIFT = RATING_DOT_RADIUS + 5;
const RATING_TICK_LIFT = 2;

function RatingDots({ rows }: { rows: PriorityRow[] }) {
  const read = (row: PriorityRow) => num(row.avg_csat);
  const values = rows.map(read).filter((value) => value !== null);
  const axis = values.length > 0 ? ratingAxis(values) : { low: 0, high: 1, ticks: [] };
  const height = (rating: number) => RATING_FLOOR + Math.round(((rating - axis.low) / (axis.high - axis.low)) * RATING_PLOT);
  const worst = soleLowest(rows, read);
  const alt = rows.map((row) => `${priorityName(row.priority)} ${ratingText(row.avg_csat)}`).join(", ");
  return (
    <div className="rp-half">
      <span className="rp-half-title">Average rating out of 5</span>
      <div className="rp-ratings" role="img" aria-label={`Average rating: ${alt}.`}>
        {axis.ticks.map((tick) => (
          <Fragment key={tick}>
            <span className="rp-rating-rule" style={{ bottom: `${height(tick)}px` }} />
            <span className="rp-rating-tick" style={{ bottom: `${height(tick) + RATING_TICK_LIFT}px` }}>{tick.toFixed(1)}</span>
          </Fragment>
        ))}
        {rows.map((row) => {
          const rating = read(row);
          const tone = row === worst ? "is-amber" : "is-teal";
          return (
            <div key={row.priority ?? "none"} className="rp-rating">
              {rating === null ? <span className="rp-rating-none">{NOT_RECORDED}</span> : (
                <>
                  <span className={`rp-rating-value ${tone}`} style={{ bottom: `${height(rating) + RATING_VALUE_LIFT}px` }}>{ratingLabel(rating)}</span>
                  <span className={`rp-rating-dot rp-mark ${tone}`} style={{ bottom: `${height(rating) - RATING_DOT_RADIUS}px` }}
                    title={`${priorityName(row.priority)} · ${ratingLabel(rating)} from ${row.csat_counted} ratings`} />
                </>
              )}
            </div>
          );
        })}
      </div>
      <PriorityLabels rows={rows} />
    </div>
  );
}

export function ByPriority({ report }: { report: PriorityRow[] }) {
  const { rows } = splitTotal(report, "priority");
  return (
    <ReportCard id="rp-priority-title" eyebrow="By priority" title={priorityHeadline(rows)}>
      {rows.length === 0 ? <NoRows /> : (
        <div className="rp-halves">
          <WaitBars rows={rows} />
          <RatingDots rows={rows} />
        </div>
      )}
    </ReportCard>
  );
}
