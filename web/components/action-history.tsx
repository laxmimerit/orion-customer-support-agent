import { ApiProblemPanel } from "@/components/desk";
import { ticketActions } from "@/lib/api";
import { actionLabel, actionTime } from "@/lib/compose";

// Streams in after the case. Rows can't be changed. A name is what someone picked, as the desk has no sign-in yet.
export async function ActionHistory({ ticketId }: { ticketId: string }) {
  const result = await ticketActions(ticketId);
  return (
    <section className="card mail-card" aria-labelledby="actions-title">
      <div className="card-head"><h2 id="actions-title">Action history</h2></div>
      {!result.ok ? (
        <div className="mail-problem">
          <ApiProblemPanel problem={result.problem} title="The desk API did not return the action history" retryTarget="the action history" />
        </div>
      ) : result.data.items.length === 0 ? (
        <div className="empty"><p className="empty-title">No drafts or replies on this case yet</p></div>
      ) : (
        <ol className="mail-list">
          {result.data.items.map((item) => (
            <li className="mail-item" key={`${item.draft_id}-${item.action}`}>
              <div className="mail-meta">
                <span className="mail-sender">{actionLabel(item.action)}</span>
                <span>{item.actor}</span>
                <span>{actionTime(item.acted_at)}</span>
                <span>{item.draft_id}</span>
              </div>
              {item.action === "drafted" && <p className="mail-subject">{item.subject} · to {item.recipient} · cites {item.article_id}</p>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
