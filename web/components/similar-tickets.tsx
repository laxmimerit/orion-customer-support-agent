import Link from "next/link";

import { ApiProblemPanel } from "@/components/desk";
import { SimilarList } from "@/components/similar-list";
import { type SimilarTickets as Similar, similarTickets } from "@/lib/api";
import { matchedPhrase, plural } from "@/lib/format";

// Streams in after the case, so a slow answer never holds up the conversation.
export async function SimilarTickets({ ticketId }: { ticketId: string }) {
  const result = await similarTickets(ticketId);

  if (!result.ok) {
    return (
      <Panel>
        <div className="similar-problem">
          <ApiProblemPanel problem={result.problem} title="The desk API did not return similar tickets"
            retryTarget="similar tickets" />
        </div>
      </Panel>
    );
  }

  const similar = result.data;
  if (similar.total === 0) {
    return (
      <Panel>
        <div className="empty similar-empty">
          <p className="empty-title">No resolved tickets are close to this one</p>
          <p>Try searching the desk in other words, or look for a help article.</p>
          <Link className="button" href="/">Search the desk</Link>
        </div>
      </Panel>
    );
  }

  const count = <span> · nearest {similar.items.length} of {similar.total}</span>;
  const basis = similar.matched_on.length > 0
    ? `${matchedPhrase(similar.matched_on)} as ${ticketId}`
    : `Close in meaning to ${ticketId}`;
  return (
    <Panel count={count} basis={basis}>
      <Solved similar={similar} />
      <SimilarList items={similar.items} topReply={similar.replies.top_reply} />
    </Panel>
  );
}

function Panel({ count, basis, children }: { count?: React.ReactNode; basis?: string; children: React.ReactNode }) {
  return (
    <section className="card similar" aria-labelledby="similar-title">
      <div className="similar-head">
        <h2 id="similar-title">Similar tickets{count}</h2>
        {basis && <p>{basis}</p>}
      </div>
      {children}
    </section>
  );
}

function replySentence({ total, replies }: Similar) {
  if (replies.distinct_replies === 0) return "No agent reply is recorded on these tickets.";
  if (total === 1) return "The agent gave this reply.";
  if (replies.distinct_replies === 1) {
    return replies.tickets_without_reply === 0
      ? `Agents gave the same reply in all ${total}.`
      : `Agents gave the same reply in ${replies.top_reply_tickets} of ${total}.`;
  }
  return `Agents gave ${replies.distinct_replies} different replies across these ${total}. `
    + `The most used, in ${plural(replies.top_reply_tickets, "ticket")}:`;
}

function Solved({ similar }: { similar: Similar }) {
  const { articles, articles_read_same: readSame, replies } = similar;
  return (
    <div className="similar-solved">
      <div>
        <h3>How they were solved</h3>
        <p>{replySentence(similar)}</p>
      </div>
      {replies.top_reply !== null && <p className="similar-reply">{replies.top_reply}</p>}
      {articles.length > 0 && (
        <p className="similar-articles">
          Also in help {articles.length === 1 ? "article" : "articles"}{" "}
          {articles.map((article, index) => (
            <span key={article.article_id}>
              {index > 0 && (index === articles.length - 1 ? " and " : ", ")}
              <Link href={`/knowledge/${encodeURIComponent(article.article_id)}`}>{article.article_id}</Link>
            </span>
          ))}
          {readSame ? ", which read the same." : "."}
        </p>
      )}
    </div>
  );
}

export function SimilarLoading() {
  return (
    <section className="card similar" aria-labelledby="similar-title">
      <div className="similar-head"><h2 id="similar-title">Similar tickets</h2></div>
      <div className="similar-loading" role="status" aria-busy="true" aria-live="polite">
        <span className="visually-hidden">Loading similar tickets</span>
        <span className="bone is-line" aria-hidden="true" />
        <span className="bone similar-bone-reply" aria-hidden="true" />
        {[0, 1, 2].map((row) => <span key={row} className="bone similar-bone-row" aria-hidden="true" />)}
      </div>
    </section>
  );
}
