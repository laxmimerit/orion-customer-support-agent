import { ApiProblemPanel } from "@/components/desk";
import { MailItem, MailUnverified } from "@/components/mail-item";
import { MailSyncButton } from "@/components/mail-sync-button";
import { ticketMail } from "@/lib/api";
import { mailCount } from "@/lib/mail";

// Streams in after the case, so a slow or failed answer never holds up the conversation.
export async function MailThread({ ticketId }: { ticketId: string }) {
  const result = await ticketMail(ticketId);

  if (!result.ok) {
    return (
      <Panel>
        <div className="mail-problem">
          <ApiProblemPanel problem={result.problem} title="The desk API did not return customer mail"
            retryTarget="customer mail" />
        </div>
      </Panel>
    );
  }

  const { total, items } = result.data;
  return (
    <Panel count={mailCount(total, items.length)}>
      {items.length === 0 ? (
        <div className="empty">
          <p className="empty-title">No mail linked to this case</p>
          <p className="empty-hint">Mail with this ticket ID in its subject, or a reply to one, shows here after a sync.</p>
        </div>
      ) : (
        <ol className="mail-list">
          {items.map((mail) => <MailItem key={mail.mail_id} mail={mail} />)}
        </ol>
      )}
    </Panel>
  );
}

// The same element in every state, so the button keeps its result when the page comes back after a sync.
function Panel({ count, children }: { count?: string; children: React.ReactNode }) {
  return (
    <section className="card mail-card" aria-labelledby="mail-title">
      <div className="card-head">
        <h2 id="mail-title">Customer mail{count && <span> · {count}</span>}</h2>
        <MailSyncButton />
      </div>
      <MailUnverified />
      {children}
    </section>
  );
}

export function MailLoading() {
  return (
    <section className="card mail-card" aria-labelledby="mail-title">
      <div className="card-head"><h2 id="mail-title">Customer mail</h2></div>
      <MailUnverified />
      <div className="mail-loading" role="status" aria-busy="true" aria-live="polite">
        <span className="visually-hidden">Loading customer mail</span>
        <span className="bone is-line" aria-hidden="true" />
        <span className="bone mail-bone-body" aria-hidden="true" />
      </div>
    </section>
  );
}
