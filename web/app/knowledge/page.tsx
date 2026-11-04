import type { Metadata } from "next";

import { ApiProblemPanel, PageHead, TopBar } from "@/components/desk";
import { KnowledgeList } from "@/components/knowledge-list";
import { SearchField } from "@/components/search";
import { knowledgeList } from "@/lib/api";
import "./knowledge.css";

export const metadata: Metadata = { title: "Knowledge base" };

type Props = { searchParams: Promise<{ q?: string | string[] }> };

export default async function KnowledgePage({ searchParams }: Props) {
  const { q } = await searchParams;
  const query = (Array.isArray(q) ? q[0] : q) ?? "";
  const result = await knowledgeList();

  if (!result.ok) {
    return (
      <>
        <TopBar>
          <SearchField label="Search articles" placeholder="Search article title or ID" action="/knowledge" />
        </TopBar>
        <main className="page kb-page">
          <PageHead title="Knowledge base"
            description="Product guidance and troubleshooting references for customer support." />
          <ApiProblemPanel problem={result.problem} />
        </main>
      </>
    );
  }

  // The key starts the search again when a link changes the words in the address.
  return <KnowledgeList key={query} data={result.data} initialQuery={query} />;
}
