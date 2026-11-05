import { describe, expect, it } from "vitest";

import { isTriage, recordHref } from "@/lib/triage";

const TRIAGE = { category: "billing", priority: "P2", team: "Customer care", reason: "Why.", record_ids: ["T00001"], model: "m", dropped_ids: 0 };

describe("recordHref", () => {
  it("finds the page for each kind of record", () => {
    expect(recordHref("T00727")).toBe("/tickets/T00727");
    expect(recordHref("C0086")).toBe("/customers/C0086");
    expect(recordHref("KB004")).toBe("/knowledge/KB004");
  });

  it("gives no link for anything else", () => {
    expect(recordHref("A03")).toBeNull();
    expect(recordHref("T00727/../admin")).toBeNull();
    expect(recordHref("")).toBeNull();
  });
});

describe("isTriage", () => {
  it("accepts the whole shape", () => {
    expect(isTriage(TRIAGE)).toBe(true);
    expect(isTriage({ ...TRIAGE, record_ids: [] })).toBe(true);
  });

  it("refuses anything missing or of the wrong type", () => {
    expect(isTriage(null)).toBe(false);
    expect(isTriage({ ...TRIAGE, priority: undefined })).toBe(false);
    expect(isTriage({ ...TRIAGE, record_ids: [1] })).toBe(false);
    expect(isTriage({ ...TRIAGE, record_ids: "T00001" })).toBe(false);
    expect(isTriage({ ...TRIAGE, dropped_ids: "0" })).toBe(false);
  });
});
