// The Compose tab's choices and draft. Used in the browser, so it holds nothing from the server.

// The API's closed lists (ComposeRequest in api/orion_api/models.py).
export const TEMPLATES = ["Answer", "Apology", "Status update", "Ask for details"];
export const TONES = ["Warm", "Neutral", "Formal"];
export const LANGUAGES = ["English", "Spanish", "French", "German", "Hindi"];

export type ComposeDraft = {
  draft_id: string;
  recipient: string;
  subject: string;
  body: string;
  english: string;
  language: string;
  article_id: string;
  article_title: string | null;
  approvers: string[];
};

export function isDraft(value: unknown): value is ComposeDraft {
  const draft = value as Partial<ComposeDraft> | null;
  return typeof draft?.draft_id === "string" && typeof draft.body === "string" && typeof draft.article_id === "string"
    && Array.isArray(draft.approvers);
}

// One line to tell linked mails apart, as anyone can link a mail to a case.
export function mailChoice(mail: { sender_name: string | null; subject: string | null }) {
  return `${mail.sender_name ?? "Sender not recorded"} · ${mail.subject ?? "No subject"}`;
}

const ACTIONS: Record<string, string> = { drafted: "Drafted", approved: "Approved", sending: "Handed to SMTP", sent: "Sent", failed: "Failed" };

export function actionLabel(action: string) {
  return ACTIONS[action] ?? action;
}

// `2026-11-05T10:00:00Z` as `2026-11-05 10:00 UTC`.
export function actionTime(at: string) {
  return `${at.slice(0, 10)} ${at.slice(11, 16)} UTC`;
}
