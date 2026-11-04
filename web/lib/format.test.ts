import { describe, expect, it } from "vitest";

import {
  NOT_RECORDED,
  asPercent,
  centsToMoney,
  channelLabel,
  duration,
  hoursShort,
  initial,
  isResolved,
  listOf,
  matchedPhrase,
  money,
  orNotRecorded,
  paragraphs,
  percent,
  plural,
  rounded,
  sentenceCase,
  toCents,
} from "@/lib/format";

describe("NOT_RECORDED", () => {
  it("is the wording the desk shows for a missing value", () => {
    expect(NOT_RECORDED).toBe("Not recorded");
  });
});

describe("orNotRecorded", () => {
  it.each([[null], [undefined], [""]])("reads %j as missing", (value) => {
    expect(orNotRecorded(value)).toBe("Not recorded");
  });

  it("keeps a real zero, which is a value and not a gap", () => {
    expect(orNotRecorded(0)).toBe("0");
  });

  it("turns a number into its text", () => {
    expect(orNotRecorded(12.5)).toBe("12.5");
  });

  it("returns text unchanged", () => {
    expect(orNotRecorded("Fern Platform 086")).toBe("Fern Platform 086");
  });
});

describe("sentenceCase", () => {
  it("capitalises the first letter only", () => {
    expect(sentenceCase("in progress")).toBe("In progress");
  });

  it("leaves the rest of the text as it is", () => {
    expect(sentenceCase("waiting on API")).toBe("Waiting on API");
  });

  it("leaves empty text empty", () => {
    expect(sentenceCase("")).toBe("");
  });
});

describe("channelLabel", () => {
  it.each([[null], [""]])("reads %j as not recorded", (channel) => {
    expect(channelLabel(channel)).toBe("Not recorded");
  });

  it.each([["api"], ["API"], ["Api"]])("writes %s as the acronym", (channel) => {
    expect(channelLabel(channel)).toBe("API");
  });

  it.each([["web"], ["WEB"], ["wEb"]])("writes %s in sentence case", (channel) => {
    expect(channelLabel(channel)).toBe("Web");
  });
});

describe("rounded", () => {
  it("rounds half up on the decimal value, not the binary float", () => {
    expect(rounded(17.65)).toBe(17.7);
    expect(rounded(1.45)).toBe(1.5);
    expect(rounded(1.005, 2)).toBe(1.01);
  });

  it("rounds other values to the nearest place", () => {
    expect(rounded(17.64)).toBe(17.6);
    expect(rounded(4.126, 2)).toBe(4.13);
    expect(rounded(2.5, 0)).toBe(3);
    expect(rounded(2.4, 0)).toBe(2);
  });

  it("keeps whole numbers and zero", () => {
    expect(rounded(0)).toBe(0);
    expect(rounded(12)).toBe(12);
  });

  it("handles numbers JavaScript prints in exponent form", () => {
    expect(rounded(1e-7)).toBe(0);
    expect(rounded(1e21)).toBe(1e21);
  });
});

describe("asPercent", () => {
  it("rounds a half-way share up, where multiplying by 100 falls just short", () => {
    expect(asPercent(57 / 200)).toBe(29);
    expect(asPercent(23 / 40)).toBe(58);
    expect(asPercent(353 / 2000, 1)).toBe(17.7);
  });

  it("rounds other shares to the nearest place", () => {
    expect(asPercent(1 / 3)).toBe(33);
    expect(asPercent(1 / 3, 1)).toBe(33.3);
    expect(asPercent(0)).toBe(0);
    expect(asPercent(1)).toBe(100);
  });

  it("handles a share too small to print in plain digits", () => {
    expect(asPercent(1e-7)).toBe(0);
  });
});

describe("duration", () => {
  it("rounds a half minute up, even where the float falls just short", () => {
    expect(duration("1.0250")).toBe("1h 2m");
    expect(duration(0.075)).toBe("5m");
    expect(duration(0.07499999999999929)).toBe("5m");
  });

  it("does not round up a value just under the half minute", () => {
    expect(duration("1.0249")).toBe("1h 1m");
  });

  it("shows hours and minutes", () => {
    expect(duration(7.96)).toBe("7h 58m");
  });

  it("drops the minutes on a whole hour", () => {
    expect(duration(3)).toBe("3h");
  });

  it("drops the hours under an hour", () => {
    expect(duration(0.5)).toBe("30m");
  });

  it("reads the API's exact decimal strings", () => {
    expect(duration("7.9600")).toBe("7h 58m");
    expect(duration("3.0000")).toBe("3h");
  });

  it("shows zero as 0m, which the SLA text relies on", () => {
    expect(duration(0)).toBe("0m");
  });

  it("rounds to the nearest minute", () => {
    expect(duration(0.0083)).toBe("0m");
    expect(duration(0.0084)).toBe("1m");
  });

  it("rounds an exact half minute up", () => {
    expect(duration(0.125)).toBe("8m");
  });

  it("carries rounded minutes into the hour, so 60m never shows", () => {
    expect(duration(0.9999)).toBe("1h");
    expect(duration(1.9999)).toBe("2h");
  });

  it("measures the size of a negative gap", () => {
    expect(duration(-1.5)).toBe("1h 30m");
    expect(duration("-0.5")).toBe("30m");
  });
});

describe("hoursShort", () => {
  it("rounds a half-way value up, as the reports do", () => {
    expect(hoursShort("17.65")).toBe("17.7h");
    expect(hoursShort("1.45")).toBe("1.5h");
    expect(hoursShort("1.005", 2)).toBe("1.01h");
  });

  it("shows one decimal place by default", () => {
    expect(hoursShort(16.2)).toBe("16.2h");
  });

  it("pads a whole number to the places asked for", () => {
    expect(hoursShort(3)).toBe("3.0h");
  });

  it("reads decimal strings", () => {
    expect(hoursShort("16.2000")).toBe("16.2h");
  });

  it("rounds to the nearest place", () => {
    expect(hoursShort("16.24")).toBe("16.2h");
    expect(hoursShort("16.26")).toBe("16.3h");
  });

  it("takes the number of places", () => {
    expect(hoursShort("7.96", 2)).toBe("7.96h");
    expect(hoursShort("7.96", 0)).toBe("8h");
  });
});

describe("percent", () => {
  it("rounds a half-way share up", () => {
    expect(percent(23, 40)).toBe("58%");
    expect(percent(57, 200)).toBe("29%");
  });

  it("rounds the share to a whole percent", () => {
    expect(percent(2451, 4000)).toBe("61%");
  });

  it("rounds an exact half up", () => {
    expect(percent(1, 8)).toBe("13%");
  });

  it("shows a real zero share", () => {
    expect(percent(0, 4000)).toBe("0%");
  });

  it("shows the whole as 100%", () => {
    expect(percent(4000, 4000)).toBe("100%");
  });

  it("does not cap a share over the whole", () => {
    expect(percent(3, 2)).toBe("150%");
  });

  it("gives null with nothing to divide by, so no 0% is invented", () => {
    expect(percent(0, 0)).toBeNull();
    expect(percent(5, 0)).toBeNull();
  });

  it("gives null for a negative whole", () => {
    expect(percent(1, -4)).toBeNull();
  });
});

describe("plural", () => {
  it("uses the single form for exactly one", () => {
    expect(plural(1, "ticket")).toBe("1 ticket");
  });

  it("adds an s for any other count, zero included", () => {
    expect(plural(0, "ticket")).toBe("0 tickets");
    expect(plural(2, "ticket")).toBe("2 tickets");
  });

  it("uses the plural form it is given", () => {
    expect(plural(3, "reply", "replies")).toBe("3 replies");
    expect(plural(1, "reply", "replies")).toBe("1 reply");
  });
});

describe("listOf", () => {
  it("gives empty text for no words", () => {
    expect(listOf([])).toBe("");
  });

  it("gives one word alone", () => {
    expect(listOf(["a"])).toBe("a");
  });

  it("joins two words with and", () => {
    expect(listOf(["a", "b"])).toBe("a and b");
  });

  it("uses commas up to the last word", () => {
    expect(listOf(["a", "b", "c"])).toBe("a, b and c");
    expect(listOf(["a", "b", "c", "d"])).toBe("a, b, c and d");
  });
});

describe("matchedPhrase", () => {
  it("names plan_id as plan", () => {
    expect(matchedPhrase(["subject", "plan_id"])).toBe("Same subject and plan");
  });

  it("reads a single field", () => {
    expect(matchedPhrase(["plan_id"])).toBe("Same plan");
    expect(matchedPhrase(["component"])).toBe("Same component");
  });

  it("reads every field the API can match on", () => {
    expect(matchedPhrase(["subject", "component", "priority", "plan_id", "channel"]))
      .toBe("Same subject, component, priority, plan and channel");
  });
});

describe("initial", () => {
  it("takes the first letter of the name", () => {
    expect(initial("Fern Platform 086")).toBe("F");
  });

  it("writes it in upper case", () => {
    expect(initial("fern")).toBe("F");
  });

  it("skips leading spaces", () => {
    expect(initial("  fern")).toBe("F");
  });

  it.each([[null], [""], ["   "]])("falls back to ? for %j", (name) => {
    expect(initial(name)).toBe("?");
  });
});

describe("isResolved", () => {
  it.each([["resolved"], ["Resolved"], ["RESOLVED"]])("counts %s as resolved", (status) => {
    expect(isResolved(status)).toBe(true);
  });

  it.each([["in progress"], ["open"], ["unresolved"], [""]])("counts %j as still active", (status) => {
    expect(isResolved(status)).toBe(false);
  });

  it("counts a ticket with no status as still active", () => {
    expect(isResolved(null)).toBe(false);
  });
});

describe("toCents", () => {
  it("turns the API's four-place amounts into whole cents", () => {
    expect(toCents("99.0000")).toBe(9900);
  });

  it("reads whole numbers and short decimals", () => {
    expect(toCents("4752")).toBe(475200);
    expect(toCents("12.5")).toBe(1250);
    expect(toCents("12.34")).toBe(1234);
    expect(toCents("0")).toBe(0);
  });

  it("ignores spaces around the amount", () => {
    expect(toCents("  99.00\n")).toBe(9900);
  });

  it("keeps the sign", () => {
    expect(toCents("-12.34")).toBe(-1234);
  });

  it("rounds on the third decimal place", () => {
    expect(toCents("1.0049")).toBe(100);
    expect(toCents("1.0050")).toBe(101);
    expect(toCents("1.0090")).toBe(101);
  });

  it("carries a rounded cent into the dollar", () => {
    expect(toCents("1.995")).toBe(200);
    expect(toCents("0.995")).toBe(100);
  });

  it("rounds a negative amount by its size", () => {
    expect(toCents("-1.005")).toBe(-101);
    expect(toCents("-1.004")).toBe(-100);
  });

  it("does not pick up float error", () => {
    expect(toCents("19.99")).toBe(1999);
    expect(toCents("1.15")).toBe(115);
    expect(toCents("4.35")).toBe(435);
  });

  it("gives null for a missing amount", () => {
    expect(toCents(null)).toBeNull();
  });

  it.each([[""], ["   "], ["abc"], ["12.3.4"], ["1,000.00"], ["$99.00"], ["+5"], [".5"], ["5."], ["1e3"], ["-"]])(
    "gives null for %j, which is not a number",
    (amount) => {
      expect(toCents(amount)).toBeNull();
    },
  );
});

describe("centsToMoney", () => {
  it("writes cents as dollars with the currency", () => {
    expect(centsToMoney(475200)).toBe("4752.00 USD");
  });

  it("pads the cents to two places", () => {
    expect(centsToMoney(5)).toBe("0.05 USD");
    expect(centsToMoney(150)).toBe("1.50 USD");
  });

  it("writes zero", () => {
    expect(centsToMoney(0)).toBe("0.00 USD");
  });

  it("puts the sign in front of the whole amount", () => {
    expect(centsToMoney(-5)).toBe("-0.05 USD");
    expect(centsToMoney(-150)).toBe("-1.50 USD");
  });
});

describe("money", () => {
  it("writes a stored amount to two places", () => {
    expect(money("99.0000")).toBe("99.00 USD");
  });

  it("writes a negative amount", () => {
    expect(money("-5.5")).toBe("-5.50 USD");
  });

  it("rounds to the cent", () => {
    expect(money("0.005")).toBe("0.01 USD");
  });

  it("shows no sign when the amount rounds to nothing", () => {
    expect(money("-0.00")).toBe("0.00 USD");
    expect(money("-0.004")).toBe("0.00 USD");
  });

  it.each([[null], [""], ["abc"]])("reads %j as not recorded", (amount) => {
    expect(money(amount)).toBe("Not recorded");
  });
});

describe("paragraphs", () => {
  it("splits on a blank line", () => {
    expect(paragraphs("one\n\ntwo")).toEqual(["one", "two"]);
  });

  it("keeps a single line break inside a paragraph", () => {
    expect(paragraphs("line one\nline two")).toEqual(["line one\nline two"]);
  });

  it("treats a line of spaces as blank", () => {
    expect(paragraphs("one\n   \ntwo")).toEqual(["one", "two"]);
  });

  it("treats several blank lines as one break", () => {
    expect(paragraphs("one\n\n\n\ntwo")).toEqual(["one", "two"]);
  });

  it("reads Windows line endings", () => {
    expect(paragraphs("one\r\n\r\ntwo")).toEqual(["one", "two"]);
  });

  it("trims each paragraph", () => {
    expect(paragraphs("  one  \n\n  two  ")).toEqual(["one", "two"]);
  });

  it("drops blank text at either end", () => {
    expect(paragraphs("\n\none\n\n")).toEqual(["one"]);
  });

  it.each([[null], [""], ["  \n\n  "]])("gives no paragraphs for %j", (text) => {
    expect(paragraphs(text)).toEqual([]);
  });
});
