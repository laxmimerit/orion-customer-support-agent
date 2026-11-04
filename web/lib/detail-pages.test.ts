import { describe, expect, it } from "vitest";

import { detailLoadingLabel } from "@/lib/detail-pages";

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
