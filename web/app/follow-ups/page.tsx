import type { Metadata } from "next";
import Link from "next/link";

import { ApiProblemPanel, PageHead, TicketSearchBar } from "@/components/desk";
import { followUps } from "@/lib/api";
import { orNotRecorded } from "@/lib/format";

import "@/components/mail.css";

export const metadata: Metadata = { title: "Follow-up" };

const DESCRIPTION = "Active cases past a target, oldest first. Each draft is text to read: nothing here is stored or sent.";

export default async function FollowUpPage() {
  const result = await followUps();

  return (
    <>
      <TicketSearchBar />
      <main className="page">
        <PageHead title="Follow-up" description={DESCRIPTION} />
        {result.ok ? (
          <section className="card mail-card" aria-labelledby="late-title">
            <div className="card-head">
              <h2 id="late-title">Late cases <span>· showing {result.data.items.length} of {result.data.total}</span></h2>
            </div>
            {result.data.items.length === 0 ? (
              <div className="empty"><p className="empty-title">No late cases</p></div>
            ) : (
              <ol className="mail-list">
                {result.data.items.map((item) => (
                  <li className="mail-item" key={item.ticket_id}>
                    <div className="mail-meta">
                      <Link className="mail-sender" href={`/tickets/${encodeURIComponent(item.ticket_id)}`}>{item.ticket_id}</Link>
                      <span>· {orNotRecorded(item.company)}</span>
                      <span>· {orNotRecorded(item.priority)}</span>
                      <span>· {item.late_reply && item.late_resolution ? "Reply and resolution late" : item.late_reply ? "Reply late" : "Resolution late"}</span>
                    </div>
                    <p className="mail-subject">{item.subject || "No subject recorded"}</p>
                    <details>
                      <summary>Follow-up draft</summary>
                      <div className="follow-up-draft">{item.draft}</div>
                    </details>
                  </li>
                ))}
              </ol>
            )}
          </section>
        ) : (
          <ApiProblemPanel problem={result.problem} retryTarget="the follow-up list" />
        )}
      </main>
    </>
  );
}
