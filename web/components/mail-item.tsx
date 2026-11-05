import type { MailMessage } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded } from "@/lib/format";
import { MAIL_UNVERIFIED, mailLinkLabel } from "@/lib/mail";

import "./mail.css";

// React escapes all of this. A mail body is never rendered as HTML: it comes from outside the desk.
export function MailItem({ mail }: { mail: MailMessage }) {
  return (
    <li className="mail-item">
      <div className="mail-meta">
        <span className="mail-sender">{orNotRecorded(mail.sender_name)}</span>
        <span>· {mail.mail_id}</span>
        <span>· {mailLinkLabel(mail.linked_by)}</span>
      </div>
      <p className="mail-subject">{mail.subject || "No subject recorded"}</p>
      <div className="mail-body">{mail.body ?? NOT_RECORDED}</div>
    </li>
  );
}

export function MailUnverified() {
  return <p className="mail-note">{MAIL_UNVERIFIED}</p>;
}
