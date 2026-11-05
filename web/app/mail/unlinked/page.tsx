import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { MailItem, MailUnverified } from "@/components/mail-item";
import { MailSyncButton } from "@/components/mail-sync-button";
import { unlinkedMail } from "@/lib/api";
import { mailCount } from "@/lib/mail";

export const metadata: Metadata = { title: "Unlinked mail" };

const DESCRIPTION = "Customer mail that matched no ticket, newest first.";

export default async function UnlinkedMailPage() {
  const result = await unlinkedMail();

  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <PageHead title="Unlinked mail" description={DESCRIPTION}><MailSyncButton /></PageHead>
        {result.ok ? (
          <section className="card mail-card" aria-labelledby="mail-title">
            <div className="card-head">
              <h2 id="mail-title">Mail <span>· {mailCount(result.data.total, result.data.items.length)}</span></h2>
            </div>
            <MailUnverified />
            {result.data.items.length === 0 ? (
              <div className="empty">
                <p className="empty-title">No unlinked mail</p>
                <p className="empty-hint">Mail that matches no ticket shows here after a sync.</p>
              </div>
            ) : (
              <ol className="mail-list">
                {result.data.items.map((mail) => <MailItem key={mail.mail_id} mail={mail} />)}
              </ol>
            )}
          </section>
        ) : (
          <ApiProblemPanel problem={result.problem} retryTarget="unlinked mail" />
        )}
      </main>
    </>
  );
}
