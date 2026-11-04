import { describe, expect, it } from "vitest";

import type { BacklogRow, Breakdown, CategoryRow, FirstReplyRow, PriorityRow, VolumeRow } from "@/lib/api";
import { NOT_RECORDED } from "@/lib/format";
import {
  METRICS,
  backlogHeadline,
  categoryHeadline,
  categoryName,
  categorySpotlight,
  daysText,
  firstReplyHeadline,
  hoursLabel,
  hoursText,
  kpisFrom,
  num,
  percentText,
  periodHeadline,
  periodsFrom,
  priorityHeadline,
  priorityName,
  ratingAxis,
  ratingCountNote,
  ratingGap,
  ratingLabel,
  ratingText,
  ratio,
  soleHighest,
  soleLowest,
  splitTotal,
  stripNotes,
  tablesShownNotice,
  undatedTickets,
  type Metric,
  type Period,
} from "@/lib/report-text";

const breakdown = (over: Partial<Breakdown> = {}): Breakdown => ({
  tickets: 100,
  resolved: 60,
  unresolved: 40,
  status_missing: 0,
  avg_first_response_hours: null,
  first_response_counted: 0,
  first_response_missing: 0,
  avg_resolution_hours: null,
  resolution_counted: 0,
  resolution_missing: 0,
  avg_csat: null,
  csat_counted: 0,
  csat_missing: 0,
  ...over,
});

const category = (name: string | null, over: Partial<Breakdown> = {}): CategoryRow => ({ ...breakdown(over), category: name });

const priority = (name: string | null, over: Partial<Breakdown> = {}): PriorityRow => ({ ...breakdown(over), priority: name });

const volume = (month: string | null, tickets: number, unresolved: number, resolved = tickets - unresolved): VolumeRow => ({
  month,
  tickets,
  resolved,
  unresolved,
  status_missing: 0,
});

const firstReply = (over: Partial<FirstReplyRow> = {}): FirstReplyRow => ({
  priority: "All",
  tickets: 100,
  met: 60,
  missed: 40,
  no_first_reply: 0,
  no_target: 0,
  avg_csat_met: null,
  csat_met_counted: 0,
  csat_met_missing: 0,
  avg_csat_missed: null,
  csat_missed_counted: 0,
  csat_missed_missing: 0,
  ...over,
});

const backlog = (over: Partial<BacklogRow> = {}): BacklogRow => ({
  status: "All",
  tickets: 12,
  no_first_reply: 0,
  no_first_reply_past_target: 0,
  avg_age_hours: null,
  age_counted: 0,
  age_missing: 0,
  ...over,
});

const period = (n: number, share: number | null): Period => ({ n, tickets: 100, unresolved: 0, share });

const metric = (label: string): Metric => {
  const found = METRICS.find((item) => item.label === label);
  if (!found) throw new Error(`No metric named ${label}`);
  return found;
};

describe("num", () => {
  it("parses decimal strings and passes numbers through", () => {
    expect(num("4.10")).toBe(4.1);
    expect(num("0")).toBe(0);
    expect(num(17.65)).toBe(17.65);
    expect(num(0)).toBe(0);
  });

  it("keeps a missing value as null, never 0", () => {
    expect(num(null)).toBeNull();
    expect(num(undefined)).toBeNull();
    expect(num("")).toBeNull();
  });

  it("gives null for anything that is not a finite number", () => {
    expect(num("not a number")).toBeNull();
    expect(num("Infinity")).toBeNull();
    expect(num(Number.NaN)).toBeNull();
    expect(num(Number.POSITIVE_INFINITY)).toBeNull();
  });
});

describe("splitTotal", () => {
  it("takes the All row out of the breakdown rows", () => {
    const p1 = priority("P1");
    const p2 = priority("P2");
    const all = priority("All");
    const result = splitTotal([p1, p2, all], "priority");
    expect(result.total).toBe(all);
    expect(result.rows).toEqual([p1, p2]);
  });

  it("finds the total wherever it sits in the report", () => {
    const all = priority("All");
    const p1 = priority("P1");
    const result = splitTotal([all, p1], "priority");
    expect(result.total).toBe(all);
    expect(result.rows).toEqual([p1]);
  });

  it("gives a null total when the report has none", () => {
    const p1 = priority("P1");
    expect(splitTotal([p1], "priority")).toEqual({ total: null, rows: [p1] });
    expect(splitTotal<PriorityRow>([], "priority")).toEqual({ total: null, rows: [] });
  });

  it("keeps a row with a null key among the breakdown rows", () => {
    const blank = volume(null, 3, 1);
    const all = volume("All", 3, 1);
    const result = splitTotal([blank, all], "month");
    expect(result.total).toBe(all);
    expect(result.rows).toEqual([blank]);
  });

  it("matches the key exactly", () => {
    const lower = priority("all");
    expect(splitTotal([lower], "priority")).toEqual({ total: null, rows: [lower] });
  });
});

describe("ratio", () => {
  it("divides part by whole", () => {
    expect(ratio(1, 4)).toBe(0.25);
    expect(ratio(0, 5)).toBe(0);
    expect(ratio(5, 5)).toBe(1);
  });

  it("gives null when there is nothing to divide by", () => {
    expect(ratio(3, 0)).toBeNull();
    expect(ratio(0, 0)).toBeNull();
    expect(ratio(3, -1)).toBeNull();
  });
});

describe("hoursLabel", () => {
  it("rounds half up and keeps one decimal place", () => {
    expect(hoursLabel(17.65)).toBe("17.7h");
    expect(hoursLabel(3)).toBe("3.0h");
    expect(hoursLabel(0)).toBe("0.0h");
  });
});

describe("percentText", () => {
  it("rounds a half-way share up", () => {
    expect(percentText(57 / 200)).toBe("29%");
    expect(percentText(353 / 2000, 1)).toBe("17.7%");
  });

  it("shows a share as a whole percentage by default", () => {
    expect(percentText(0.6128)).toBe("61%");
    expect(percentText(0)).toBe("0%");
    expect(percentText(1)).toBe("100%");
  });

  it("takes decimal places", () => {
    expect(percentText(0.6128, 1)).toBe("61.3%");
    expect(percentText(0.25, 1)).toBe("25.0%");
  });

  it("reads Not recorded for a null share, never 0%", () => {
    expect(percentText(null)).toBe(NOT_RECORDED);
    expect(percentText(null, 1)).toBe(NOT_RECORDED);
  });
});

describe("hoursText", () => {
  it("reads a value too small to print in plain digits as zero", () => {
    expect(hoursText("0.0000001")).toBe("0.0h");
  });

  it("words a decimal string as hours", () => {
    expect(hoursText("17.65")).toBe("17.7h");
    expect(hoursText("0")).toBe("0.0h");
  });

  it("reads Not recorded when the value is missing or unreadable", () => {
    expect(hoursText(null)).toBe(NOT_RECORDED);
    expect(hoursText("")).toBe(NOT_RECORDED);
    expect(hoursText("soon")).toBe(NOT_RECORDED);
  });
});

describe("ratingLabel", () => {
  it("always shows two decimal places", () => {
    expect(ratingLabel(4.1)).toBe("4.10");
    expect(ratingLabel(5)).toBe("5.00");
    expect(ratingLabel(3.87)).toBe("3.87");
  });
});

describe("ratingText", () => {
  it("words a decimal string as a rating", () => {
    expect(ratingText("4.1")).toBe("4.10");
    expect(ratingText("0")).toBe("0.00");
  });

  it("reads Not recorded when the value is missing or unreadable", () => {
    expect(ratingText(null)).toBe(NOT_RECORDED);
    expect(ratingText("")).toBe(NOT_RECORDED);
    expect(ratingText("good")).toBe(NOT_RECORDED);
  });
});

describe("daysText", () => {
  it("turns hours into whole days", () => {
    expect(daysText("1944")).toBe("81 days");
    expect(daysText("48")).toBe("2 days");
  });

  it("rounds to the nearest day, a half day going up", () => {
    expect(daysText("36")).toBe("2 days");
    expect(daysText("35.9")).toBe("1 day");
    expect(daysText("12")).toBe("1 day");
    expect(daysText("11.9")).toBe("0 days");
  });

  it("uses the singular only for exactly one day", () => {
    expect(daysText("24")).toBe("1 day");
    expect(daysText("0")).toBe("0 days");
  });

  it("gives null when the age is missing", () => {
    expect(daysText(null)).toBeNull();
    expect(daysText("")).toBeNull();
    expect(daysText("old")).toBeNull();
  });
});

describe("priorityName", () => {
  it("keeps the priority as it is", () => {
    expect(priorityName("P1")).toBe("P1");
  });

  it("reads Not recorded for a null priority", () => {
    expect(priorityName(null)).toBe(NOT_RECORDED);
  });
});

describe("categoryName", () => {
  it("sentence-cases the category", () => {
    expect(categoryName("feature request")).toBe("Feature request");
    expect(categoryName("Bug")).toBe("Bug");
  });

  it("reads Not recorded for a null or empty category", () => {
    expect(categoryName(null)).toBe(NOT_RECORDED);
    expect(categoryName("")).toBe(NOT_RECORDED);
  });
});

describe("soleHighest", () => {
  const read = (row: { value: number | null }) => row.value;

  it("picks the single highest row", () => {
    const top = { value: 3 };
    expect(soleHighest([{ value: 1 }, top, { value: 2 }], read)).toBe(top);
  });

  it("gives null on a tie for the top", () => {
    expect(soleHighest([{ value: 3 }, { value: 3 }, { value: 1 }], read)).toBeNull();
  });

  it("ignores rows with no value and needs two rows that have one", () => {
    const only = { value: 3 };
    expect(soleHighest([only, { value: null }], read)).toBeNull();
    expect(soleHighest([only], read)).toBeNull();
    const top = { value: 3 };
    expect(soleHighest([{ value: null }, top, { value: 1 }], read)).toBe(top);
  });

  it("gives null when no row has a value", () => {
    expect(soleHighest([{ value: null }, { value: null }], read)).toBeNull();
    expect(soleHighest([], read)).toBeNull();
  });

  it("treats 0 as a value", () => {
    const top = { value: 0 };
    expect(soleHighest([top, { value: -1 }], read)).toBe(top);
  });
});

describe("soleLowest", () => {
  const read = (row: { value: number | null }) => row.value;

  it("picks the single lowest row", () => {
    const bottom = { value: 1 };
    expect(soleLowest([{ value: 3 }, bottom, { value: 2 }], read)).toBe(bottom);
  });

  it("gives null on a tie for the bottom", () => {
    expect(soleLowest([{ value: 1 }, { value: 1 }, { value: 3 }], read)).toBeNull();
  });

  it("ignores rows with no value and needs two rows that have one", () => {
    const only = { value: 1 };
    expect(soleLowest([only, { value: null }], read)).toBeNull();
    const bottom = { value: 1 };
    expect(soleLowest([{ value: null }, bottom, { value: 3 }], read)).toBe(bottom);
  });

  it("gives null when no row has a value", () => {
    expect(soleLowest([{ value: null }], read)).toBeNull();
    expect(soleLowest([], read)).toBeNull();
  });

  it("treats 0 as a value", () => {
    const bottom = { value: 0 };
    expect(soleLowest([bottom, { value: 2 }], read)).toBe(bottom);
  });
});

describe("periodsFrom", () => {
  it("numbers periods by row order and works out each share", () => {
    expect(periodsFrom([volume("2026-02", 10, 4), volume("2026-01", 20, 5)])).toEqual([
      { n: 1, tickets: 10, unresolved: 4, share: 0.4 },
      { n: 2, tickets: 20, unresolved: 5, share: 0.25 },
    ]);
  });

  it("leaves out a row with no month without leaving a gap in the numbers", () => {
    const periods = periodsFrom([volume("2026-01", 10, 1), volume(null, 7, 7), volume("2026-02", 10, 2)]);
    expect(periods.map((item) => item.n)).toEqual([1, 2]);
    expect(periods.map((item) => item.unresolved)).toEqual([1, 2]);
  });

  it("gives a null share for a period with no tickets", () => {
    expect(periodsFrom([volume("2026-01", 0, 0)])).toEqual([{ n: 1, tickets: 0, unresolved: 0, share: null }]);
  });

  it("gives no periods for no rows", () => {
    expect(periodsFrom([])).toEqual([]);
  });
});

describe("undatedTickets", () => {
  it("adds up the tickets on rows with no month", () => {
    expect(undatedTickets([volume(null, 3, 1), volume("2026-01", 50, 1), volume(null, 4, 2)])).toBe(7);
  });

  it("gives 0 when every row has a month", () => {
    expect(undatedTickets([volume("2026-01", 50, 1)])).toBe(0);
    expect(undatedTickets([])).toBe(0);
  });
});

describe("periodHeadline", () => {
  it("reads Not recorded when no period has a share", () => {
    expect(periodHeadline([])).toBe("Unresolved share: Not recorded");
    expect(periodHeadline([period(1, null), period(2, null)])).toBe("Unresolved share: Not recorded");
  });

  it("says no period left tickets open when the highest share is 0", () => {
    expect(periodHeadline([period(1, 0), period(2, 0)])).toBe("No period left tickets open");
    expect(periodHeadline([period(1, 0)])).toBe("No period left tickets open");
  });

  it("names a single winner", () => {
    expect(periodHeadline([period(1, 0.1), period(2, 0.34), period(3, 0.2)])).toBe("Period 2 left the most open: 34%");
  });

  it("states one figure when every period is equal", () => {
    expect(periodHeadline([period(1, 0.2), period(2, 0.2)])).toBe("Every period left 20% open");
  });

  it("does not call a lone period the most", () => {
    expect(periodHeadline([period(1, 0.2)])).toBe("Every period left 20% open");
  });

  it("states the real extremes when the top is tied", () => {
    expect(periodHeadline([period(1, 0.3), period(2, 0.1), period(3, 0.3)])).toBe("Between 10% and 30% left open in each period");
  });
});

describe("firstReplyHeadline", () => {
  const row = (met: number, tickets: number) => firstReply({ priority: "P1", met, tickets });

  it("reads Not recorded with no total row or no tickets", () => {
    expect(firstReplyHeadline(null, [row(1, 2)])).toBe("First reply on target: Not recorded");
    expect(firstReplyHeadline(firstReply({ met: 0, tickets: 0 }), [])).toBe("First reply on target: Not recorded");
  });

  it("gives the lead alone when there are no priority rows to compare", () => {
    expect(firstReplyHeadline(firstReply({ met: 61, tickets: 100 }), [])).toBe("About 6 in 10 on time");
  });

  it("gives the lead alone when no priority row has tickets", () => {
    expect(firstReplyHeadline(firstReply({ met: 61, tickets: 100 }), [row(0, 0)])).toBe("About 6 in 10 on time");
  });

  it("says at every priority when each rounds to the same tenth", () => {
    expect(firstReplyHeadline(firstReply({ met: 61, tickets: 100 }), [row(56, 100), row(64, 100)]))
      .toBe("About 6 in 10 on time, at every priority");
  });

  it("states the spread when one priority rounds to another tenth", () => {
    expect(firstReplyHeadline(firstReply({ met: 61, tickets: 100 }), [row(40, 100), row(56, 100), row(72, 100)]))
      .toBe("About 6 in 10 on time, 40% to 72% by priority");
  });

  it("ignores priority rows with no tickets", () => {
    expect(firstReplyHeadline(firstReply({ met: 61, tickets: 100 }), [row(60, 100), row(0, 0)]))
      .toBe("About 6 in 10 on time, at every priority");
  });

  it("rounds the lead to the nearest tenth", () => {
    expect(firstReplyHeadline(firstReply({ met: 54, tickets: 100 }), [])).toBe("About 5 in 10 on time");
    expect(firstReplyHeadline(firstReply({ met: 55, tickets: 100 }), [])).toBe("About 6 in 10 on time");
    expect(firstReplyHeadline(firstReply({ met: 0, tickets: 100 }), [])).toBe("About 0 in 10 on time");
    expect(firstReplyHeadline(firstReply({ met: 100, tickets: 100 }), [])).toBe("About 10 in 10 on time");
  });
});

describe("categoryHeadline", () => {
  const fastAndLow = (name: string | null) => [
    category(name, { avg_first_response_hours: "1.50", avg_csat: "3.90" }),
    category("billing", { avg_first_response_hours: "4.00", avg_csat: "4.40" }),
  ];

  it("uses the headline name when one category is both fastest and lowest rated", () => {
    expect(categoryHeadline(fastAndLow("outage"))).toBe("Outages: fastest reply, lowest rating");
    expect(categoryHeadline(fastAndLow("bug"))).toBe("Bugs: fastest reply, lowest rating");
    expect(categoryHeadline(fastAndLow("feature request"))).toBe("Feature requests: fastest reply, lowest rating");
  });

  it("matches the headline name whatever the case", () => {
    expect(categoryHeadline(fastAndLow("OUTAGE"))).toBe("Outages: fastest reply, lowest rating");
  });

  it("falls back to the category name plus tickets", () => {
    expect(categoryHeadline(fastAndLow("account"))).toBe("Account tickets: fastest reply, lowest rating");
  });

  it("names each extreme when they are different categories", () => {
    expect(categoryHeadline([
      category("bug", { avg_first_response_hours: "1.50", avg_csat: "4.40" }),
      category("outage", { avg_first_response_hours: "4.00", avg_csat: "3.90" }),
    ])).toBe("Fastest reply: Bug at 1.5h; lowest rating: Outage at 3.90");
  });

  it("names every category in a tie", () => {
    expect(categoryHeadline([
      category("bug", { avg_first_response_hours: "1.50", avg_csat: "3.90" }),
      category("outage", { avg_first_response_hours: "1.50", avg_csat: "3.90" }),
      category("account", { avg_first_response_hours: "4.00", avg_csat: "4.40" }),
    ])).toBe("Fastest reply: Bug and Outage at 1.5h; lowest rating: Bug and Outage at 3.90");
  });

  it("keeps to the neutral line for a single category", () => {
    expect(categoryHeadline([category("bug", { avg_first_response_hours: "1.50", avg_csat: "3.90" })]))
      .toBe("Fastest reply: Bug at 1.5h; lowest rating: Bug at 3.90");
  });

  it("does not put a null category in the combined claim", () => {
    expect(categoryHeadline(fastAndLow(null))).toBe("Fastest reply: Not recorded at 1.5h; lowest rating: Not recorded at 3.90");
  });

  it("states only the half that has values, in sentence case", () => {
    expect(categoryHeadline([category("bug", { avg_first_response_hours: "1.50" }), category("outage", { avg_first_response_hours: "2.00" })]))
      .toBe("Fastest reply: Bug at 1.5h");
    expect(categoryHeadline([category("bug", { avg_csat: "3.90" }), category("outage", { avg_csat: "4.20" })]))
      .toBe("Lowest rating: Bug at 3.90");
  });

  it("reads Not recorded when no row has a value", () => {
    expect(categoryHeadline([category("bug")])).toBe("Category averages: Not recorded");
    expect(categoryHeadline([])).toBe("Category averages: Not recorded");
  });
});

describe("categorySpotlight", () => {
  it("picks the lowest rated category", () => {
    const low = category("outage", { avg_csat: "3.90", avg_first_response_hours: "9.00" });
    const fast = category("bug", { avg_csat: "4.40", avg_first_response_hours: "1.00" });
    expect(categorySpotlight([fast, low])).toBe(low);
  });

  it("falls back to the fastest reply when the rating is tied", () => {
    const fast = category("bug", { avg_csat: "4.00", avg_first_response_hours: "1.00" });
    const slow = category("outage", { avg_csat: "4.00", avg_first_response_hours: "9.00" });
    expect(categorySpotlight([slow, fast])).toBe(fast);
  });

  it("falls back to the fastest reply when there are no ratings", () => {
    const fast = category("bug", { avg_first_response_hours: "1.00" });
    const slow = category("outage", { avg_first_response_hours: "9.00" });
    expect(categorySpotlight([slow, fast])).toBe(fast);
  });

  it("gives null when neither picks out a single category", () => {
    expect(categorySpotlight([
      category("bug", { avg_csat: "4.00", avg_first_response_hours: "1.00" }),
      category("outage", { avg_csat: "4.00", avg_first_response_hours: "1.00" }),
    ])).toBeNull();
    expect(categorySpotlight([category("bug", { avg_csat: "4.00", avg_first_response_hours: "1.00" })])).toBeNull();
    expect(categorySpotlight([])).toBeNull();
  });
});

describe("tablesShownNotice", () => {
  it("names both sections when both have a table", () => {
    expect(tablesShownNotice(true, true)).toBe("Tables shown in the first reply and satisfaction section and the categories section.");
  });

  it("names only the section that has a table", () => {
    expect(tablesShownNotice(true, false)).toBe("Tables shown in the first reply and satisfaction section.");
    expect(tablesShownNotice(false, true)).toBe("Tables shown in the categories section.");
  });
});

describe("backlogHeadline", () => {
  it("says nothing is waiting with no total row or no tickets", () => {
    expect(backlogHeadline(null)).toBe("Nothing waiting");
    expect(backlogHeadline(backlog({ tickets: 0, avg_age_hours: "48" }))).toBe("Nothing waiting");
  });

  it("states the count and the average age in days", () => {
    expect(backlogHeadline(backlog({ tickets: 12, avg_age_hours: "1944" }))).toBe("12 waiting, 81 days on average");
    expect(backlogHeadline(backlog({ tickets: 1, avg_age_hours: "24" }))).toBe("1 waiting, 1 day on average");
  });

  it("says the age is not recorded when it is missing", () => {
    expect(backlogHeadline(backlog({ tickets: 12, avg_age_hours: null }))).toBe("12 waiting, average age not recorded");
  });
});

describe("priorityHeadline", () => {
  const shortAndLow = (name: string | null) => [
    priority(name, { avg_first_response_hours: "0.50", avg_csat: "3.90" }),
    priority("P4", { avg_first_response_hours: "9.00", avg_csat: "4.40" }),
  ];

  it("calls P1 Urgent when it both waits least and is rated lowest", () => {
    expect(priorityHeadline(shortAndLow("P1"))).toBe("Urgent tickets wait least and are rated lowest");
  });

  it("keeps any other priority's name", () => {
    expect(priorityHeadline(shortAndLow("P2"))).toBe("P2 tickets wait least and are rated lowest");
  });

  it("names each extreme when they are different priorities", () => {
    expect(priorityHeadline([
      priority("P1", { avg_first_response_hours: "0.50", avg_csat: "4.40" }),
      priority("P4", { avg_first_response_hours: "9.00", avg_csat: "3.90" }),
    ])).toBe("Shortest wait: P1 at 0.5h; lowest rating: P4 at 3.90");
  });

  it("names every priority in a tie", () => {
    expect(priorityHeadline([
      priority("P1", { avg_first_response_hours: "0.50", avg_csat: "3.90" }),
      priority("P2", { avg_first_response_hours: "0.50", avg_csat: "3.90" }),
      priority("P3", { avg_first_response_hours: "9.00", avg_csat: "4.40" }),
    ])).toBe("Shortest wait: P1 and P2 at 0.5h; lowest rating: P1 and P2 at 3.90");
  });

  it("keeps to the neutral line for a single priority", () => {
    expect(priorityHeadline([priority("P1", { avg_first_response_hours: "0.50", avg_csat: "3.90" })]))
      .toBe("Shortest wait: P1 at 0.5h; lowest rating: P1 at 3.90");
  });

  it("does not put a null priority in the combined claim", () => {
    expect(priorityHeadline(shortAndLow(null))).toBe("Shortest wait: Not recorded at 0.5h; lowest rating: Not recorded at 3.90");
  });

  it("states only the half that has values, in sentence case", () => {
    expect(priorityHeadline([priority("P1", { avg_first_response_hours: "0.50" }), priority("P2", { avg_first_response_hours: "2.00" })]))
      .toBe("Shortest wait: P1 at 0.5h");
    expect(priorityHeadline([priority("P1", { avg_csat: "3.90" }), priority("P2", { avg_csat: "4.20" })]))
      .toBe("Lowest rating: P1 at 3.90");
  });

  it("reads Not recorded when no row has a value", () => {
    expect(priorityHeadline([priority("P1")])).toBe("Priority averages: Not recorded");
    expect(priorityHeadline([])).toBe("Priority averages: Not recorded");
  });
});

describe("METRICS", () => {
  it("lists the three strips in order", () => {
    expect(METRICS.map((item) => item.label)).toEqual(["First reply", "Resolution", "Rating"]);
  });

  it("reads each metric from its own field, keeping a missing value null", () => {
    const row = category("bug", { avg_first_response_hours: "1.50", avg_resolution_hours: "20.25", avg_csat: "4.10" });
    expect(metric("First reply").read(row)).toBe(1.5);
    expect(metric("Resolution").read(row)).toBe(20.25);
    expect(metric("Rating").read(row)).toBe(4.1);
    expect(METRICS.map((item) => item.read(category("bug")))).toEqual([null, null, null]);
  });

  describe.each(["First reply", "Resolution"])("%s, in hours", (label) => {
    const hours = metric(label);

    it("words a value and a span", () => {
      expect(hours.text(17.65)).toBe("17.7h");
      expect(hours.span(1.25, 17.65)).toBe("1.3–17.7h");
      expect(hours.span(2, 3)).toBe("2.0–3.0h");
    });

    it("words the axis range", () => {
      expect(hours.range(0, 20)).toBe("0–20 hours");
    });

    it("runs a short axis from 0 up to the next whole hour", () => {
      expect(hours.axis([2.3, 1])).toEqual([0, 3]);
      expect(hours.axis([10])).toEqual([0, 10]);
    });

    it("never gives an axis less than an hour wide", () => {
      expect(hours.axis([0.3])).toEqual([0, 1]);
      expect(hours.axis([0])).toEqual([0, 1]);
    });

    it("runs an axis above 10 hours up to the next ten", () => {
      expect(hours.axis([10.5])).toEqual([0, 20]);
      expect(hours.axis([3, 20])).toEqual([0, 20]);
      expect(hours.axis([20.1])).toEqual([0, 30]);
    });
  });

  describe("Rating", () => {
    const rating = metric("Rating");

    it("words a value, a span and the axis range", () => {
      expect(rating.text(4.1)).toBe("4.10");
      expect(rating.span(3.9, 4.25)).toBe("3.90–4.25");
      expect(rating.range(3, 5)).toBe("3.0–5.0");
    });

    it("takes whole points around the values", () => {
      expect(rating.axis([3.2, 4.6])).toEqual([3, 5]);
      expect(rating.axis([4.2])).toEqual([4, 5]);
      expect(rating.axis([3, 5])).toEqual([3, 5]);
    });

    it("never gives an axis with no width", () => {
      expect(rating.axis([4])).toEqual([3, 4]);
      expect(rating.axis([5, 5])).toEqual([4, 5]);
    });
  });
});

describe("stripNotes", () => {
  const firstReplyMetric = metric("First reply");
  // A 0 to 10 hour axis, so one hour is 10% and "well away" means an hour or more.
  const at = (value: number) => value * 10;
  const rows = (...hours: (string | null)[]) => hours.map((value, index) => category(`category ${index + 1}`, { avg_first_response_hours: value }));

  it("gives the spotlight its own note and the others one range", () => {
    const others = rows("1.00", "1.50", "1.90");
    const spotlight = category("outage", { avg_first_response_hours: "8.00" });
    expect(stripNotes(firstReplyMetric, [...others, spotlight], spotlight, at)).toEqual([
      { text: "Outage 8.0h", position: 80, spotlit: true },
      { text: "Others 1.0–1.9h", position: 14.5, spotlit: false },
    ]);
  });

  it("leads with All when there is no spotlight", () => {
    expect(stripNotes(firstReplyMetric, rows("1.00", "2.00"), null, at)).toEqual([
      { text: "All 1.0–2.0h", position: 15, spotlit: false },
    ]);
  });

  it("orders the range by value, not by row order", () => {
    expect(stripNotes(firstReplyMetric, rows("2.00", "1.00"), null, at)[0].text).toBe("All 1.0–2.0h");
  });

  it("states one figure when the range ends read the same", () => {
    expect(stripNotes(firstReplyMetric, rows("2.01", "2.04"), null, at)).toEqual([
      { text: "All 2.0h", position: 20.25, spotlit: false },
    ]);
  });

  it("gives the highest category its own note when it sits well away from the rest", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0.50" });
    const [one, two, far] = rows("1.00", "1.50", "6.00");
    expect(stripNotes(firstReplyMetric, [one, far, two, spotlight], spotlight, at)).toEqual([
      { text: "Outage 0.5h", position: 5, spotlit: true },
      { text: "Others 1.0–1.5h", position: 12.5, spotlit: false },
      { text: "Category 3 6.0h", position: 60, spotlit: false },
    ]);
  });

  it("gives the lowest category its own note when it sits well away from the rest", () => {
    const spotlight = category("outage", { avg_first_response_hours: "9.00" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "5.00", "5.50"), spotlight], spotlight, at)).toEqual([
      { text: "Outage 9.0h", position: 90, spotlit: true },
      { text: "Others 5.0–5.5h", position: 52.5, spotlit: false },
      { text: "Category 1 1.0h", position: 10, spotlit: false },
    ]);
  });

  it("sets only the highest apart when both ends sit away", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0.50" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "5.00", "9.00"), spotlight], spotlight, at)).toEqual([
      { text: "Outage 0.5h", position: 5, spotlit: true },
      { text: "Others 1.0–5.0h", position: 30, spotlit: false },
      { text: "Category 3 9.0h", position: 90, spotlit: false },
    ]);
  });

  it("counts a gap of exactly 10% as apart, and anything less as not", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0.50" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "1.50", "2.50"), spotlight], spotlight, at).map((note) => note.text))
      .toEqual(["Outage 0.5h", "Others 1.0–1.5h", "Category 3 2.5h"]);
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "1.50", "2.40"), spotlight], spotlight, at).map((note) => note.text))
      .toEqual(["Outage 0.5h", "Others 1.0–2.4h"]);
  });

  it("measures the gap along the strip, not in units", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0.50" });
    const wide = (value: number) => value;
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "1.50", "6.00"), spotlight], spotlight, wide).map((note) => note.text))
      .toEqual(["Outage 0.5h", "Others 1.0–6.0h"]);
  });

  it("sets nobody apart with fewer than three others", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0.50" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "9.00"), spotlight], spotlight, at).map((note) => note.text))
      .toEqual(["Outage 0.5h", "Others 1.0–9.0h"]);
  });

  it("leaves out rows with no value", () => {
    const spotlight = category("outage", { avg_first_response_hours: "8.00" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", null, "2.00"), spotlight], spotlight, at).map((note) => note.text))
      .toEqual(["Outage 8.0h", "Others 1.0–2.0h"]);
  });

  it("gives no spotlit note when the spotlight has no value on this strip", () => {
    const spotlight = category("outage");
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "2.00"), spotlight], spotlight, at)).toEqual([
      { text: "Others 1.0–2.0h", position: 15, spotlit: false },
    ]);
  });

  it("keeps a spotlight whose value is 0", () => {
    const spotlight = category("outage", { avg_first_response_hours: "0" });
    expect(stripNotes(firstReplyMetric, [spotlight], spotlight, at)).toEqual([
      { text: "Outage 0.0h", position: 0, spotlit: true },
    ]);
  });

  it("gives no range when the spotlight is the only row with a value", () => {
    const spotlight = category("outage", { avg_first_response_hours: "8.00" });
    expect(stripNotes(firstReplyMetric, [category("bug"), spotlight], spotlight, at)).toEqual([
      { text: "Outage 8.0h", position: 80, spotlit: true },
    ]);
  });

  it("gives no notes when no row has a value", () => {
    expect(stripNotes(firstReplyMetric, [category("bug")], null, at)).toEqual([]);
  });

  it("reads Not recorded for a null category", () => {
    const spotlight = category(null, { avg_first_response_hours: "8.00" });
    expect(stripNotes(firstReplyMetric, [spotlight], spotlight, at)[0].text).toBe("Not recorded 8.0h");
    const far = category(null, { avg_first_response_hours: "6.00" });
    const other = category("outage", { avg_first_response_hours: "0.50" });
    expect(stripNotes(firstReplyMetric, [...rows("1.00", "1.50"), far, other], other, at)[2].text).toBe("Not recorded 6.0h");
  });

  it("words the notes with the metric it is given", () => {
    const spotlight = category("outage", { avg_csat: "3.20" });
    const others = [category("bug", { avg_csat: "4.10" }), category("account", { avg_csat: "4.30" })];
    const scale = (value: number) => (value - 3) * 50;
    const notes = stripNotes(metric("Rating"), [...others, spotlight], spotlight, scale);
    expect(notes.map((note) => note.text)).toEqual(["Outage 3.20", "Others 4.10–4.30"]);
    expect(notes[0].position).toBeCloseTo(10, 10);
    expect(notes[1].position).toBeCloseTo(60, 10);
  });
});

describe("ratingAxis", () => {
  it("takes the half points strictly around the values", () => {
    expect(ratingAxis([3.7, 4.6])).toEqual({ low: 3.5, high: 5, ticks: [4, 4.5] });
  });

  it("moves past a value that sits on a half point", () => {
    expect(ratingAxis([4])).toEqual({ low: 3.5, high: 4.5, ticks: [4] });
    expect(ratingAxis([4.5])).toEqual({ low: 4, high: 5, ticks: [4.5] });
    expect(ratingAxis([3.5, 4.5])).toEqual({ low: 3, high: 5, ticks: [3.5, 4, 4.5] });
  });

  it("draws fifths of a point when the axis is a single half point wide", () => {
    expect(ratingAxis([4.1, 4.3])).toEqual({ low: 4, high: 4.5, ticks: [4.2, 4.4] });
    expect(ratingAxis([4.6, 4.9])).toEqual({ low: 4.5, high: 5, ticks: [4.6, 4.8] });
  });

  it("does not depend on the order of the values", () => {
    expect(ratingAxis([4.6, 3.7])).toEqual(ratingAxis([3.7, 4.6]));
  });

  it("gives ticks rounded to one decimal place", () => {
    expect(ratingAxis([3.6, 3.9]).ticks).toEqual([3.6, 3.8]);
  });
});

describe("ratingGap", () => {
  const gap = (met: string | null, missed: string | null) => ratingGap(firstReply({ avg_csat_met: met, avg_csat_missed: missed }));

  it("gives null when either side has no ratings", () => {
    expect(ratingGap(null)).toBeNull();
    expect(gap(null, "4.00")).toBeNull();
    expect(gap("4.00", null)).toBeNull();
    expect(gap(null, null)).toBeNull();
  });

  it("is late minus on time, with a true minus sign and the sign spelled out", () => {
    expect(gap("4.10", "3.95")).toEqual({ hundredths: -15, text: "−0.15", spoken: "minus 0.15" });
  });

  it("shows a late rating above on time with a plus", () => {
    expect(gap("3.95", "4.20")).toEqual({ hundredths: 25, text: "+0.25", spoken: "plus 0.25" });
  });

  it("shows no sign for no gap", () => {
    expect(gap("4.10", "4.10")).toEqual({ hundredths: 0, text: "0.00", spoken: "0.00" });
  });

  it("shows no sign when the gap rounds to nothing", () => {
    const result = gap("4.104", "4.10");
    expect(result?.text).toBe("0.00");
    expect(result?.spoken).toBe("0.00");
  });

  it("keeps two decimal places on a gap over one point", () => {
    expect(gap("4.50", "3.20")).toEqual({ hundredths: -130, text: "−1.30", spoken: "minus 1.30" });
  });
});

describe("ratingCountNote", () => {
  it("states the rating counts and the caution", () => {
    expect(ratingCountNote(firstReply({ csat_met_counted: 120, csat_missed_counted: 80 })))
      .toBe("120 and 80 ratings · association, not proof of cause");
  });

  it("adds the unrated counts when either side has any", () => {
    expect(ratingCountNote(firstReply({ csat_met_counted: 120, csat_missed_counted: 80, csat_met_missing: 3, csat_missed_missing: 5 })))
      .toBe("120 and 80 ratings, 3 and 5 unrated · association, not proof of cause");
    expect(ratingCountNote(firstReply({ csat_met_counted: 120, csat_missed_counted: 80, csat_met_missing: 0, csat_missed_missing: 5 })))
      .toBe("120 and 80 ratings, 0 and 5 unrated · association, not proof of cause");
    expect(ratingCountNote(firstReply({ csat_met_counted: 120, csat_missed_counted: 80, csat_met_missing: 3, csat_missed_missing: 0 })))
      .toBe("120 and 80 ratings, 3 and 0 unrated · association, not proof of cause");
  });
});

describe("kpisFrom", () => {
  it("rounds a half-way share up in the percentage tiles", () => {
    const row = { met: 57, tickets: 200 } as FirstReplyRow;
    expect(kpisFrom({ firstReply: row })).toEqual([{ label: "First reply on target", value: "29", unit: "%" }]);
  });

  const averages = breakdown({
    tickets: 200,
    resolved: 150,
    avg_first_response_hours: "17.65",
    avg_resolution_hours: "40.04",
    avg_csat: "4.1",
  });

  it("gives nothing when every report failed", () => {
    expect(kpisFrom({})).toEqual([]);
  });

  it("gives every figure, in order, when all reports are in", () => {
    expect(kpisFrom({ volume: volume("All", 400, 100, 244), breakdown: averages, firstReply: firstReply({ met: 61, tickets: 100 }) })).toEqual([
      { label: "Tickets", value: "400", unit: "" },
      { label: "Resolved", value: "61", unit: "%" },
      { label: "First reply on target", value: "61", unit: "%" },
      { label: "Avg first reply", value: "17.7", unit: "h" },
      { label: "Avg resolution", value: "40.0", unit: "h" },
      { label: "Satisfaction", value: "4.10", unit: "/ 5" },
    ]);
  });

  it("takes the counts from the breakdown when the volume report failed", () => {
    expect(kpisFrom({ breakdown: averages }).slice(0, 2)).toEqual([
      { label: "Tickets", value: "200", unit: "" },
      { label: "Resolved", value: "75", unit: "%" },
    ]);
  });

  it("leaves out the averages when the breakdown failed", () => {
    expect(kpisFrom({ volume: volume("All", 400, 100, 300) })).toEqual([
      { label: "Tickets", value: "400", unit: "" },
      { label: "Resolved", value: "75", unit: "%" },
    ]);
  });

  it("gives only the first reply figure when that is the only report", () => {
    expect(kpisFrom({ firstReply: firstReply({ met: 1, tickets: 3 }) })).toEqual([
      { label: "First reply on target", value: "33", unit: "%" },
    ]);
  });

  it("keeps a report with no total row, with null figures", () => {
    expect(kpisFrom({ volume: null, breakdown: null, firstReply: null })).toEqual([
      { label: "Tickets", value: null, unit: "" },
      { label: "Resolved", value: null, unit: "%" },
      { label: "First reply on target", value: null, unit: "%" },
      { label: "Avg first reply", value: null, unit: "h" },
      { label: "Avg resolution", value: null, unit: "h" },
      { label: "Satisfaction", value: null, unit: "/ 5" },
    ]);
  });

  it("does not fill a volume report with no total row from the breakdown", () => {
    expect(kpisFrom({ volume: null, breakdown: averages }).slice(0, 2)).toEqual([
      { label: "Tickets", value: null, unit: "" },
      { label: "Resolved", value: null, unit: "%" },
    ]);
  });

  it("gives a null share, not 0, when there are no tickets", () => {
    expect(kpisFrom({ volume: volume("All", 0, 0, 0), firstReply: firstReply({ met: 0, tickets: 0 }) })).toEqual([
      { label: "Tickets", value: "0", unit: "" },
      { label: "Resolved", value: null, unit: "%" },
      { label: "First reply on target", value: null, unit: "%" },
    ]);
  });

  it("keeps a missing average null", () => {
    expect(kpisFrom({ breakdown: breakdown() }).slice(2)).toEqual([
      { label: "Avg first reply", value: null, unit: "h" },
      { label: "Avg resolution", value: null, unit: "h" },
      { label: "Satisfaction", value: null, unit: "/ 5" },
    ]);
  });

  it("rounds the averages half up, to one place for hours and two for ratings", () => {
    const kpis = kpisFrom({ breakdown: breakdown({ avg_first_response_hours: "1.25", avg_resolution_hours: "0", avg_csat: "1.005" }) });
    expect(kpis.slice(2).map((kpi) => kpi.value)).toEqual(["1.3", "0.0", "1.01"]);
  });
});
