import { expect, test } from "vitest";

import { actionLabel, actionTime, isDraft, mailChoice } from "./compose";

test("a draft needs its text, its article and its approvers", () => {
  expect(isDraft({ draft_id: "DR1", body: "Hi", article_id: "KB004", approvers: ["Clara"] })).toBe(true);
  expect(isDraft({ draft_id: "DR1", body: "Hi", approvers: ["Clara"] })).toBe(false);
  expect(isDraft(null)).toBe(false);
});

test("mails and actions read as words", () => {
  expect(mailChoice({ sender_name: null, subject: "Slow" })).toBe("Sender not recorded · Slow");
  expect(actionLabel("sent")).toBe("Sent");
  expect(actionTime("2026-11-05T10:00:00Z")).toBe("2026-11-05 10:00 UTC");
});
