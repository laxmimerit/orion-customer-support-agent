import type { Metadata } from "next";
import Link from "next/link";

import { Crumbs, PageHead, TopBar } from "@/components/desk";
import { SearchField } from "@/components/search";

export const metadata: Metadata = { title: "Article not found" };

export default function ArticleNotFound() {
  return (
    <>
      <TopBar>
        <SearchField label="Search articles" placeholder="Search article title or ID" action="/knowledge" param="q" />
      </TopBar>
      <main className="page is-detail">
        <Crumbs parent="Knowledge base" href="/knowledge" current="Article not found" />
        <PageHead title="Article not found" description="The knowledge base has no article with this ID." />
        <p><Link className="button is-primary" href="/knowledge">Back to the knowledge base</Link></p>
      </main>
    </>
  );
}
