// Words for customer mail. Used in the browser, so it holds nothing from the server.
import type { MailMessage, MailSync } from "@/lib/api";
import { plural } from "@/lib/format";

// Mail is customer text: anyone can write anything in it, under any name.
export const MAIL_UNVERIFIED = "Mail is shown as the sender wrote it. The desk has not checked who sent it or whether it is true.";

const LINKED_BY: Record<NonNullable<MailMessage["linked_by"]>, string> = {
  subject: "Ticket ID in the subject",
  thread: "Reply in the same thread",
};

export function mailLinkLabel(linkedBy: MailMessage["linked_by"]) {
  return linkedBy === null ? "Not linked to a case" : LINKED_BY[linkedBy];
}

// "3 mails", or "showing 100 of 240" when the list stops short of the total.
export function mailCount(total: number, shown: number) {
  return shown < total ? `showing ${shown} of ${total}` : plural(total, "mail");
}

// `linked` also counts older mail that got a ticket on this sync, and `unlinked` counts new mail only. So the new mail that
// linked is what `added` leaves after `unlinked`, and anything over that is older mail. Saying so keeps the counts adding up.
export function mailSyncSentence({ added, linked, unlinked, skipped, remaining }: MailSync) {
  const linkedNew = Math.min(linked, Math.max(added - unlinked, 0));
  const linkedOlder = linked - linkedNew;
  const split = [
    linkedNew > 0 ? `${linkedNew} linked to a case` : null,
    unlinked > 0 ? `${unlinked} unlinked` : null,
  ].filter((part) => part !== null).join(", ");
  const parts = [
    added === 0 ? "No new mail." : `${plural(added, "new mail")}${split ? `: ${split}` : ""}.`,
    linkedOlder > 0 ? `${plural(linkedOlder, "older mail")} linked to a case.` : null,
    skipped > 0 ? `${plural(skipped, "mail")} could not be stored.` : null,
    remaining > 0 ? `${plural(remaining, "mail")} left for the next sync.` : null,
  ];
  return parts.filter((part) => part !== null).join(" ");
}
