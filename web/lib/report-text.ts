// The arithmetic and wording behind the reports page. A headline is a claim, so each one is worked out
// from the rows and printed only if it holds; otherwise a neutral line states the actual extremes.
// Pure functions: no fetching, and the volume report's month is only ever tested, never shown.
import type { BacklogRow, Breakdown, CategoryRow, FirstReplyRow, PriorityRow, VolumeRow } from "@/lib/api";
import { NOT_RECORDED, hoursShort, sentenceCase } from "@/lib/format";

// Averages arrive as decimal strings. Null stays null, so a missing value is never drawn as 0.
export function num(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

// Every report ends with a total row; it must never sit among the breakdown rows.
export function splitTotal<Row>(rows: Row[], key: keyof Row) {
  return {
    total: rows.find((row) => row[key] === "All") ?? null,
    rows: rows.filter((row) => row[key] !== "All"),
  };
}

export function ratio(part: number, whole: number) {
  return whole > 0 ? part / whole : null;
}

// Rounds half up on the decimal value: 17.65 -> 17.7, where toFixed gives 17.6 from the binary float.
export function rounded(value: number, places = 1) {
  return Number(`${Math.round(Number(`${value}e${places}`))}e-${places}`);
}

// 17.65 -> "17.7h".
export function hoursLabel(value: number) {
  return hoursShort(rounded(value));
}

export function percentText(share: number | null, places = 0) {
  return share === null ? NOT_RECORDED : `${(share * 100).toFixed(places)}%`;
}

export function hoursText(value: string | null) {
  const hours = num(value);
  return hours === null ? NOT_RECORDED : hoursLabel(hours);
}

export function ratingText(value: string | null) {
  const rating = num(value);
  return rating === null ? NOT_RECORDED : rating.toFixed(2);
}

// 1944 hours -> "81 days". An age, so a duration and not a date.
export function daysText(hours: string | null) {
  const value = num(hours);
  if (value === null) return null;
  const days = Math.round(value / 24);
  return `${days} ${days === 1 ? "day" : "days"}`;
}

export function priorityName(priority: string | null) {
  return priority ?? NOT_RECORDED;
}

export function categoryName(category: string | null) {
  return category ? sentenceCase(category) : NOT_RECORDED;
}

type Extreme<Row> = { rows: Row[]; value: number; known: number };

function lowest<Row>(rows: Row[], read: (row: Row) => number | null): Extreme<Row> | null {
  const known = rows.flatMap((row) => {
    const value = read(row);
    return value === null ? [] : [{ row, value }];
  });
  if (known.length === 0) return null;
  const value = Math.min(...known.map((item) => item.value));
  return { rows: known.filter((item) => item.value === value).map((item) => item.row), value, known: known.length };
}

function highest<Row>(rows: Row[], read: (row: Row) => number | null): Extreme<Row> | null {
  const flipped = lowest(rows, (row) => {
    const value = read(row);
    return value === null ? null : -value;
  });
  return flipped && { ...flipped, value: -flipped.value };
}

// A superlative needs a single winner among at least two rows that have a value.
function sole<Row>(extreme: Extreme<Row> | null) {
  return extreme && extreme.rows.length === 1 && extreme.known > 1 ? extreme.rows[0] : null;
}

export function soleHighest<Row>(rows: Row[], read: (row: Row) => number | null) {
  return sole(highest(rows, read));
}

export function soleLowest<Row>(rows: Row[], read: (row: Row) => number | null) {
  return sole(lowest(rows, read));
}

// Periods are numbered by row order. A row with no month is not a period: it is counted separately.
export type Period = { n: number; tickets: number; unresolved: number; share: number | null };

export function periodsFrom(rows: VolumeRow[]): Period[] {
  return rows.filter((row) => row.month !== null).map((row, index) => ({
    n: index + 1,
    tickets: row.tickets,
    unresolved: row.unresolved,
    share: ratio(row.unresolved, row.tickets),
  }));
}

export function undatedTickets(rows: VolumeRow[]) {
  return rows.filter((row) => row.month === null).reduce((sum, row) => sum + row.tickets, 0);
}

export function periodHeadline(periods: Period[]) {
  const read = (period: Period) => period.share;
  const top = highest(periods, read);
  const bottom = lowest(periods, read);
  if (!top || !bottom) return `Unresolved share: ${NOT_RECORDED}`;
  if (top.value === 0) return "No period left tickets open";
  const winner = sole(top);
  if (winner) return `Period ${winner.n} left the most open: ${percentText(top.value)}`;
  if (top.value === bottom.value) return `Every period left ${percentText(top.value)} open`;
  return `Between ${percentText(bottom.value)} and ${percentText(top.value)} left open in each period`;
}

// "About 6 in 10" is met / tickets on the total row, in tenths. "At every priority" is only printed
// when each priority rounds to the same tenth; otherwise the real spread is stated.
export function firstReplyHeadline(total: FirstReplyRow | null, rows: FirstReplyRow[]) {
  const overall = total ? ratio(total.met, total.tickets) : null;
  if (overall === null) return `First reply on target: ${NOT_RECORDED}`;
  const tenths = Math.round(overall * 10);
  const lead = `About ${tenths} in 10 on time`;
  const shares = rows.flatMap((row) => {
    const share = ratio(row.met, row.tickets);
    return share === null ? [] : [share];
  });
  if (shares.length === 0) return lead;
  if (shares.every((share) => Math.round(share * 10) === tenths)) return `${lead}, at every priority`;
  return `${lead}, ${percentText(Math.min(...shares))} to ${percentText(Math.max(...shares))} by priority`;
}

const CATEGORY_HEADLINE: Record<string, string> = { outage: "Outages", bug: "Bugs", "feature request": "Feature requests" };

function joined(names: string[]) {
  return names.join(" and ");
}

export function categoryHeadline(rows: CategoryRow[]) {
  const fastest = lowest(rows, (row) => num(row.avg_first_response_hours));
  const rated = lowest(rows, (row) => num(row.avg_csat));
  const both = sole(fastest);
  if (both?.category && both === sole(rated)) {
    const name = CATEGORY_HEADLINE[both.category.toLowerCase()] ?? `${categoryName(both.category)} tickets`;
    return `${name}: fastest reply, lowest rating`;
  }
  const parts = [
    fastest && `Fastest reply: ${joined(fastest.rows.map((row) => categoryName(row.category)))} at ${hoursLabel(fastest.value)}`,
    rated && `lowest rating: ${joined(rated.rows.map((row) => categoryName(row.category)))} at ${rated.value.toFixed(2)}`,
  ].filter((part) => part !== null);
  return parts.length > 0 ? sentenceCase(parts.join("; ")) : `Category averages: ${NOT_RECORDED}`;
}

// The category the strips pick out: the lowest rated if there is one, else the fastest to get a reply.
export function categorySpotlight(rows: CategoryRow[]) {
  return soleLowest(rows, (row) => num(row.avg_csat)) ?? soleLowest(rows, (row) => num(row.avg_first_response_hours));
}

export function backlogHeadline(total: BacklogRow | null) {
  if (!total || total.tickets === 0) return "Nothing waiting";
  const age = daysText(total.avg_age_hours);
  return age ? `${total.tickets} waiting, ${age} on average` : `${total.tickets} waiting, average age ${NOT_RECORDED.toLowerCase()}`;
}

export function priorityHeadline(rows: PriorityRow[]) {
  const shortest = lowest(rows, (row) => num(row.avg_first_response_hours));
  const rated = lowest(rows, (row) => num(row.avg_csat));
  const both = sole(shortest);
  if (both?.priority && both === sole(rated)) {
    const name = both.priority === "P1" ? "Urgent" : both.priority;
    return `${name} tickets wait least and are rated lowest`;
  }
  const parts = [
    shortest && `Shortest wait: ${joined(shortest.rows.map((row) => priorityName(row.priority)))} at ${hoursLabel(shortest.value)}`,
    rated && `lowest rating: ${joined(rated.rows.map((row) => priorityName(row.priority)))} at ${rated.value.toFixed(2)}`,
  ].filter((part) => part !== null);
  return parts.length > 0 ? sentenceCase(parts.join("; ")) : `Priority averages: ${NOT_RECORDED}`;
}

// Late minus on time, in rating points. Null when either side has no ratings.
export function ratingGap(total: FirstReplyRow | null) {
  const met = num(total?.avg_csat_met);
  const missed = num(total?.avg_csat_missed);
  if (met === null || missed === null) return null;
  const hundredths = Math.round((missed - met) * 100);
  const sign = hundredths < 0 ? "−" : hundredths > 0 ? "+" : "";
  return { hundredths, text: `${sign}${(Math.abs(hundredths) / 100).toFixed(2)}` };
}

export function ratingCountNote(total: FirstReplyRow) {
  const unrated = total.csat_met_missing + total.csat_missed_missing > 0
    ? `, ${total.csat_met_missing} and ${total.csat_missed_missing} unrated` : "";
  return `${total.csat_met_counted} and ${total.csat_missed_counted} ratings${unrated} · association, not proof of cause`;
}

export type Kpi = { label: string; value: string | null; unit: string };

// `undefined` means that report failed, so its figures are left out; `null` is a report with no total row.
export function kpisFrom(sources: {
  volume?: VolumeRow | null; breakdown?: Breakdown | null; firstReply?: FirstReplyRow | null;
}): Kpi[] {
  const { volume, breakdown, firstReply } = sources;
  const counts = volume !== undefined ? volume : breakdown;
  const kpis: Kpi[] = [];
  const whole = (share: number | null) => (share === null ? null : (share * 100).toFixed(0));
  const fixed = (value: string | null | undefined, places: number) => {
    const parsed = num(value);
    return parsed === null ? null : rounded(parsed, places).toFixed(places);
  };
  if (counts !== undefined) {
    kpis.push({ label: "Tickets", value: counts ? String(counts.tickets) : null, unit: "" });
    kpis.push({ label: "Resolved", value: counts ? whole(ratio(counts.resolved, counts.tickets)) : null, unit: "%" });
  }
  if (firstReply !== undefined) {
    kpis.push({
      label: "First reply on target",
      value: firstReply ? whole(ratio(firstReply.met, firstReply.tickets)) : null,
      unit: "%",
    });
  }
  if (breakdown !== undefined) {
    kpis.push({ label: "Avg first reply", value: fixed(breakdown?.avg_first_response_hours, 1), unit: "h" });
    kpis.push({ label: "Avg resolution", value: fixed(breakdown?.avg_resolution_hours, 1), unit: "h" });
    kpis.push({ label: "Satisfaction", value: fixed(breakdown?.avg_csat, 2), unit: "/ 5" });
  }
  return kpis;
}
