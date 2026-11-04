"use client";

import Link from "next/link";
import { useState } from "react";

import { PageHead, TopBar } from "@/components/desk";
import { KnowledgeIcon } from "@/components/icons";
import { SearchField } from "@/components/search";
import type { ArticleSummary, KnowledgeList as KnowledgeData } from "@/lib/api";
import { NOT_RECORDED, plural, sentenceCase } from "@/lib/format";

function categoryOf(article: ArticleSummary) {
  return article.category ? sentenceCase(article.category) : NOT_RECORDED;
}

// The whole list arrives as props, so searching and the category chips work without another request.
export function KnowledgeList({ data, initialQuery }: { data: KnowledgeData; initialQuery: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [category, setCategory] = useState<string | null>(null);

  const categories = [...new Set(data.items.map(categoryOf))];
  const needle = query.trim().toLowerCase();
  const matches = (article: ArticleSummary) =>
    !needle || `${article.article_id} ${article.title ?? ""}`.toLowerCase().includes(needle);

  const groups = categories
    .filter((label) => category === null || label === category)
    .map((label) => ({ label, items: data.items.filter((item) => categoryOf(item) === label && matches(item)) }))
    .filter((group) => group.items.length > 0);
  const shown = groups.reduce((sum, group) => sum + group.items.length, 0);

  const chips = [
    { label: "All", value: null, count: data.items.length },
    ...categories.map((label) => ({
      label,
      value: label,
      count: data.items.filter((item) => categoryOf(item) === label).length,
    })),
  ];

  return (
    <>
      <TopBar>
        <SearchField label="Search articles" placeholder="Search article title or ID" value={query}
          onChange={setQuery} onSubmit={setQuery} />
      </TopBar>
      <main className="page kb-page">
        <PageHead title="Knowledge base"
          description="Product guidance and troubleshooting references for customer support.">
          <span className="kb-count">
            <strong>{data.total}</strong> {data.total === 1 ? "article" : "articles"}
            {" · "}{plural(categories.length, "category", "categories")}
          </span>
        </PageHead>

        <div className="chips kb-chips" role="group" aria-label="Category">
          {chips.map((chip) => (
            <button key={chip.label} type="button" className="chip" aria-pressed={category === chip.value}
              onClick={() => setCategory(chip.value)}>
              {chip.label}
              <span className="kb-chip-count">{chip.count}</span>
            </button>
          ))}
        </div>

        <p className="visually-hidden" role="status">{plural(shown, "article")} shown</p>

        {groups.length === 0 ? (
          <div className="card empty kb-empty">
            {data.items.length === 0 ? (
              <p className="empty-title">No articles recorded</p>
            ) : (
              <>
                <p className="empty-title">No articles match</p>
                <button type="button" className="button"
                  onClick={() => { setQuery(""); setCategory(null); }}>
                  Clear search
                </button>
              </>
            )}
          </div>
        ) : (
          <div className="kb-groups">
            {groups.map((group) => (
              <section key={group.label} className="card kb-group" aria-label={group.label}>
                <div className="kb-group-head">
                  <span className="kb-group-icon" aria-hidden="true"><KnowledgeIcon size={17} strokeWidth={1.9} /></span>
                  <h2>{group.label}</h2>
                  <span className="kb-group-count">{plural(group.items.length, "article")}</span>
                </div>
                <ul>
                  {group.items.map((item) => (
                    <li key={item.article_id}>
                      <Link className="kb-item" href={`/knowledge/${encodeURIComponent(item.article_id)}`}>
                        <span className="kb-item-id">{item.article_id}</span>
                        <span className="kb-item-title">{item.title ?? NOT_RECORDED}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        )}
      </main>
    </>
  );
}
