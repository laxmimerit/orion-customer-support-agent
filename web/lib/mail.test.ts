import { describe, expect, it } from "vitest";

import { MAIL_UNVERIFIED, mailCount, mailLinkLabel, mailSyncSentence } from "@/lib/mail";

const NOTHING = { added: 0, linked: 0, unlinked: 0, skipped: 0, remaining: 0 };

describe("mailSyncSentence", () => {
  it("says so when nothing arrived", () => {
    expect(mailSyncSentence(NOTHING)).toBe("No new mail.");
  });

  it("splits new mail into linked and unlinked", () => {
    expect(mailSyncSentence({ ...NOTHING, added: 2, linked: 1, unlinked: 1 })).toBe("2 new mails: 1 linked to a case, 1 unlinked.");
  });

  it("leaves out a side of the split that is zero", () => {
    expect(mailSyncSentence({ ...NOTHING, added: 2, linked: 2 })).toBe("2 new mails: 2 linked to a case.");
    expect(mailSyncSentence({ ...NOTHING, added: 1, unlinked: 1 })).toBe("1 new mail: 1 unlinked.");
  });

  it("names older mail that got a ticket, so the counts still add up", () => {
    expect(mailSyncSentence({ ...NOTHING, linked: 1 })).toBe("No new mail. 1 older mail linked to a case.");
    expect(mailSyncSentence({ ...NOTHING, added: 1, linked: 3 })).toBe("1 new mail: 1 linked to a case. 2 older mails linked to a case.");
    expect(mailSyncSentence({ ...NOTHING, added: 1, linked: 1, unlinked: 1 })).toBe("1 new mail: 1 unlinked. 1 older mail linked to a case.");
  });

  it("says what could not be stored", () => {
    expect(mailSyncSentence({ ...NOTHING, skipped: 1 })).toBe("No new mail. 1 mail could not be stored.");
    expect(mailSyncSentence({ ...NOTHING, skipped: 2 })).toBe("No new mail. 2 mails could not be stored.");
  });

  it("says what is left for the next sync", () => {
    expect(mailSyncSentence({ ...NOTHING, remaining: 1 })).toBe("No new mail. 1 mail left for the next sync.");
    expect(mailSyncSentence({ ...NOTHING, added: 1, linked: 1, remaining: 40 }))
      .toBe("1 new mail: 1 linked to a case. 40 mails left for the next sync.");
  });

  it("puts every part together in order", () => {
    expect(mailSyncSentence({ added: 3, linked: 2, unlinked: 1, skipped: 1, remaining: 5 }))
      .toBe("3 new mails: 2 linked to a case, 1 unlinked. 1 mail could not be stored. 5 mails left for the next sync.");
  });

  it("still reads as a sentence if the counts don't split", () => {
    expect(mailSyncSentence({ ...NOTHING, added: 1 })).toBe("1 new mail.");
  });
});

describe("mailLinkLabel", () => {
  it.each([
    ["subject", "Ticket ID in the subject"],
    ["thread", "Reply in the same thread"],
    [null, "Not linked to a case"],
  ] as const)("names %s", (linkedBy, label) => {
    expect(mailLinkLabel(linkedBy)).toBe(label);
  });
});

describe("mailCount", () => {
  it("counts a whole list", () => {
    expect(mailCount(0, 0)).toBe("0 mails");
    expect(mailCount(1, 1)).toBe("1 mail");
    expect(mailCount(100, 100)).toBe("100 mails");
  });

  it("says when the list stops short of the total", () => {
    expect(mailCount(240, 100)).toBe("showing 100 of 240");
  });
});

describe("MAIL_UNVERIFIED", () => {
  it("is one short line with no em dash", () => {
    expect(MAIL_UNVERIFIED).not.toContain("—");
    expect(MAIL_UNVERIFIED.length).toBeLessThan(120);
  });
});
