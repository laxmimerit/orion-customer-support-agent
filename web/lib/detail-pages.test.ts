import { describe, expect, it } from "vitest";

import { decodeId, detailLoadingLabel, isBackToList, queueHref, queuePage, ticketHref } from "@/lib/detail-pages";

describe("decodeId", () => {
  it("decodes an escaped id", () => {
    expect(decodeId("T%2000727")).toBe("T 00727");
  });

  it("leaves a broken escape as it came", () => {
    expect(decodeId("T%ZZ")).toBe("T%ZZ");
  });
});

describe("detailLoadingLabel", () => {
  it.each([
    ["/tickets/TCK-1001", "Loading the case"],
    ["/customers/CUST-1001", "Loading customer"],
    ["/knowledge/KB-1001", "Loading the article"],
  ])("names the record that %s opens", (pathname, label) => {
    expect(detailLoadingLabel(pathname)).toBe(label);
  });

  // Links build the id with encodeURIComponent, so an encoded slash is still one segment.
  it("reads an encoded id as a single segment", () => {
    expect(detailLoadingLabel("/tickets/TCK%2F1001")).toBe("Loading the case");
    expect(detailLoadingLabel("/customers/Acme%20Ltd")).toBe("Loading customer");
  });

  it.each(["", "/"])("is null for the queue address %j", (pathname) => {
    expect(detailLoadingLabel(pathname)).toBeNull();
  });

  it.each(["/tickets", "/customers", "/knowledge"])("is null for %s, which has no id", (pathname) => {
    expect(detailLoadingLabel(pathname)).toBeNull();
  });

  it("is null when the id segment is empty", () => {
    expect(detailLoadingLabel("/tickets/")).toBeNull();
  });

  it("is null with a trailing slash, which is not the address a link builds", () => {
    expect(detailLoadingLabel("/tickets/TCK-1001/")).toBeNull();
  });

  it("is null when the section segment is empty", () => {
    expect(detailLoadingLabel("//TCK-1001")).toBeNull();
  });

  it.each(["/tickets/TCK-1001/history", "/customers/CUST-1001/tickets/TCK-1001", "/knowledge/KB-1001/edit"])(
    "is null for %s, which goes deeper than a detail page",
    (pathname) => {
      expect(detailLoadingLabel(pathname)).toBeNull();
    },
  );

  it.each(["/reports/weekly", "/settings/profile", "/company/about"])(
    "is null for %s, whose section has no detail page",
    (pathname) => {
      expect(detailLoadingLabel(pathname)).toBeNull();
    },
  );

  it("matches the section exactly, as the routes do", () => {
    expect(detailLoadingLabel("/Tickets/TCK-1001")).toBeNull();
    expect(detailLoadingLabel("/ticket/TCK-1001")).toBeNull();
  });

  it("does not take object built-ins for sections", () => {
    expect(detailLoadingLabel("/constructor/1")).toBeNull();
    expect(detailLoadingLabel("/__proto__/1")).toBeNull();
  });
});

describe("isBackToList", () => {
  it.each([
    ["/customers/CUST-1001", "/customers"],
    ["/knowledge/KB-1001", "/knowledge"],
  ])("is true going from %s to its list %s", (from, to) => {
    expect(isBackToList(from, to)).toBe(true);
  });

  it("takes the queue at / as the list for tickets", () => {
    expect(isBackToList("/tickets/TCK-1001", "/")).toBe(true);
  });

  it("has no /tickets list to go back to", () => {
    expect(isBackToList("/tickets/TCK-1001", "/tickets")).toBe(false);
  });

  it.each([
    ["/customers/CUST-1001", "/"],
    ["/knowledge/KB-1001", "/"],
    ["/customers/CUST-1001", "/knowledge"],
    ["/knowledge/KB-1001", "/customers"],
    ["/tickets/TCK-1001", "/customers"],
  ])("is false from %s to %s, which is another section's list", (from, to) => {
    expect(isBackToList(from, to)).toBe(false);
  });

  it.each([
    ["/tickets/TCK-1001", "/tickets/TCK-1002"],
    ["/customers/CUST-1001", "/customers/CUST-1002"],
    ["/customers/CUST-1001", "/tickets/TCK-1001"],
  ])("is false from %s to %s, which is another detail page", (from, to) => {
    expect(isBackToList(from, to)).toBe(false);
  });

  it.each([
    ["/", "/"],
    ["/customers", "/customers"],
    ["/customers", "/"],
    ["/reports/weekly", "/reports"],
    ["/customers/CUST-1001/tickets", "/customers"],
    ["/tickets/TCK-1001/history", "/"],
  ])("is false when %s is not a detail page, even going to %s", (from, to) => {
    expect(isBackToList(from, to)).toBe(false);
  });

  // RouteFocus passes usePathname() for both, so the queue's ?page= never reaches this comparison.
  it("compares whole pathnames", () => {
    expect(isBackToList("/customers/CUST-1001", "/customers/")).toBe(false);
    expect(isBackToList("/tickets/TCK-1001", "/?page=2")).toBe(false);
  });

  it("works on the encoded pathname a ticket link produces", () => {
    expect(isBackToList(ticketHref("TCK/1001", 1), "/")).toBe(true);
  });
});

describe("queuePage", () => {
  it.each([
    ["1", 1],
    ["2", 2],
    ["250", 250],
  ])("reads %j as page %i", (value, page) => {
    expect(queuePage(value)).toBe(page);
  });

  it("is the first page when the address has no value", () => {
    expect(queuePage(undefined)).toBe(1);
    expect(queuePage("")).toBe(1);
  });

  // The queue's page reads searchParams, which gives an array for ?page=2&page=3.
  it.each([[["2"]], [["2", "3"]], [[]]])("is the first page for the repeated value %j", (value) => {
    expect(queuePage(value)).toBe(1);
  });

  it.each(["0", "-0", "-1", "-250"])("is the first page for %j, which is below 1", (value) => {
    expect(queuePage(value)).toBe(1);
  });

  it.each(["2.5", "0.5", "1.1"])("is the first page for %j, which is not whole", (value) => {
    expect(queuePage(value)).toBe(1);
  });

  it.each(["abc", "12abc", "NaN", "Infinity", "-Infinity", "   "])("is the first page for %j, which is not a number", (value) => {
    expect(queuePage(value)).toBe(1);
  });

  // The API refuses a page above 100,000, so a longer address must not turn the queue into an error.
  it("stops at the API's last allowed page", () => {
    expect(queuePage("99999")).toBe(99_999);
    expect(queuePage("100000")).toBe(100_000);
    expect(queuePage("100001")).toBe(100_000);
    expect(queuePage("99999999999999999999")).toBe(100_000);
  });
});

describe("queueHref", () => {
  it("is the bare queue address for the first page", () => {
    expect(queueHref(1)).toBe("/");
  });

  it.each([
    [2, "/?page=2"],
    [37, "/?page=37"],
    [100_000, "/?page=100000"],
  ])("puts page %i in the address", (page, href) => {
    expect(queueHref(page)).toBe(href);
  });

  // The case page builds Back to queue as queueHref(queuePage(searchParams.queue)).
  it.each([
    [undefined, "/"],
    ["1", "/"],
    ["abc", "/"],
    ["3", "/?page=3"],
  ])("gives the address for a page read back as %j", (value, href) => {
    expect(queueHref(queuePage(value))).toBe(href);
  });
});

describe("ticketHref", () => {
  it("adds nothing for a ticket opened from the first page", () => {
    expect(ticketHref("TCK-1001", 1)).toBe("/tickets/TCK-1001");
  });

  it.each([
    [2, "/tickets/TCK-1001?queue=2"],
    [37, "/tickets/TCK-1001?queue=37"],
  ])("carries queue page %i", (page, href) => {
    expect(ticketHref("TCK-1001", page)).toBe(href);
  });

  it("encodes the id so it stays one path segment", () => {
    expect(ticketHref("TCK/1001", 1)).toBe("/tickets/TCK%2F1001");
    expect(ticketHref("TCK 1?a#b&c", 1)).toBe("/tickets/TCK%201%3Fa%23b%26c");
  });

  it("encodes the id when it also carries the queue page", () => {
    expect(ticketHref("TCK/1001", 4)).toBe("/tickets/TCK%2F1001?queue=4");
  });

  it("gives a queue value that queuePage reads back", () => {
    const queue = new URL(ticketHref("TCK-1001", 12), "http://orion.test").searchParams.get("queue") ?? undefined;
    expect(queuePage(queue)).toBe(12);
  });

  it("builds a link that counts as a ticket detail page", () => {
    expect(detailLoadingLabel(ticketHref("TCK/1001", 1))).toBe("Loading the case");
  });
});
