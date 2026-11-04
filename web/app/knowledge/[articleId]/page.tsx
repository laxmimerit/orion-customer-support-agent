import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ApiProblemPanel, Crumbs, PageHead, StatusPill, TopBar } from "@/components/desk";
import { SearchField } from "@/components/search";
import { type Article, knowledgeArticle } from "@/lib/api";
import { NOT_RECORDED, orNotRecorded, paragraphs, sentenceCase } from "@/lib/format";
import "./article.css";

type Props = { params: Promise<{ articleId: string }> };

function decodeId(raw: string) {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  return { title: decodeId((await params).articleId) };
}

// The board's header search has nothing to filter here, so Enter opens the list with the words.
function ArticleSearchBar() {
  return (
    <TopBar>
      <SearchField label="Search articles" placeholder="Search article title or ID" action="/knowledge" param="q" />
    </TopBar>
  );
}

function RelatedTickets({ tickets }: { tickets: Article["related_tickets"] }) {
  return (
    <section className="card card-pad" aria-labelledby="article-tickets-heading">
      <h2 id="article-tickets-heading" className="card-title">Tickets with this subject</h2>
      {tickets.items.length === 0 ? (
        <p className="article-panel-note">No tickets share this subject.</p>
      ) : (
        <ul>
          {tickets.items.map((ticket) => (
            <li key={ticket.ticket_id} className="article-ticket">
              <span className="article-ticket-text">
                <Link className="article-ticket-id" href={`/tickets/${encodeURIComponent(ticket.ticket_id)}`}>
                  {ticket.ticket_id}
                </Link>
                <span className="article-ticket-sub">
                  {ticket.customer_id
                    ? <Link href={`/customers/${encodeURIComponent(ticket.customer_id)}`}>{ticket.customer_id}</Link>
                    : NOT_RECORDED}
                  {" · "}{orNotRecorded(ticket.priority)}
                </span>
              </span>
              <StatusPill status={ticket.status} />
            </li>
          ))}
        </ul>
      )}
      {tickets.total > tickets.items.length && tickets.items.length > 0 && (
        <p className="article-panel-note">Showing {tickets.items.length} of {tickets.total}</p>
      )}
    </section>
  );
}

function MoreInCategory({ category, articles }: { category: string | null; articles: Article["more_in_category"] }) {
  return (
    <section className="card card-pad" aria-labelledby="article-more-heading">
      <h2 id="article-more-heading" className="card-title">More in {category ? sentenceCase(category) : "this category"}</h2>
      {articles.length === 0 ? (
        <p className="article-panel-note">No other articles in this category.</p>
      ) : (
        <ul>
          {articles.map((article) => (
            <li key={article.article_id}>
              <Link className="article-more" href={`/knowledge/${encodeURIComponent(article.article_id)}`}>
                <span className="article-more-id">{article.article_id}</span>
                <span className="article-more-title">{article.title ?? NOT_RECORDED}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default async function ArticlePage({ params }: Props) {
  const articleId = decodeId((await params).articleId);
  const result = await knowledgeArticle(articleId);

  if (!result.ok) {
    // 404: no such article. 422: an ID the API cannot hold.
    if (result.problem.status === 404 || result.problem.status === 422) notFound();
    return (
      <>
        <ArticleSearchBar />
        <main className="page is-detail article-page">
          <Crumbs parent="Knowledge base" href="/knowledge" current={articleId} />
          <PageHead title={articleId} />
          <ApiProblemPanel problem={result.problem} />
        </main>
      </>
    );
  }

  const article = result.data;
  const body = paragraphs(article.body);

  return (
    <>
      <ArticleSearchBar />
      <main className="page is-detail article-page">
        <Crumbs parent="Knowledge base" href="/knowledge" current={article.article_id} />
        <div className="split">
          <article className="card split-main article-card" aria-labelledby="article-title">
            <div className="article-meta">
              <span className={`pill ${article.category ? "article-category" : "tone-missing"}`}>
                {article.category ? sentenceCase(article.category) : NOT_RECORDED}
              </span>
              <span className="article-id">{article.article_id}</span>
            </div>
            <h1 id="article-title" className="article-title">{article.title ?? NOT_RECORDED}</h1>
            <hr className="article-rule" />
            <div className="article-body">
              {body.length > 0 ? body.map((text, index) => <p key={index}>{text}</p>) : <p>{NOT_RECORDED}</p>}
            </div>
          </article>
          <aside className="split-rail" aria-label="About this article">
            <RelatedTickets tickets={article.related_tickets} />
            <MoreInCategory category={article.category} articles={article.more_in_category} />
          </aside>
        </div>
      </main>
    </>
  );
}
