// Shared pieces of the Orion desk (notes/DESIGN.md section 5).
import Link from "next/link";

import type { ApiProblem } from "@/lib/api";
import { NOT_RECORDED, sentenceCase } from "@/lib/format";

type Crumb = { label: string; href?: string };

export function PageHeading({ crumbs, title, children }: { crumbs: Crumb[]; title: string; children?: React.ReactNode }) {
  return (
    <div className="heading">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        {crumbs.map((crumb, index) => (
          <span key={crumb.label}>
            {index > 0 && <span className="breadcrumb-sep" aria-hidden="true">/</span>}
            {crumb.href ? <Link href={crumb.href}>{crumb.label}</Link> : crumb.label}
          </span>
        ))}
      </nav>
      <h1>{title}</h1>
      {children}
    </div>
  );
}

export function Notice({ lead, children }: { lead: string; children: React.ReactNode }) {
  return (
    <div className="notice">
      <strong>{lead}</strong> {children}
    </div>
  );
}

const STATUS_TONES: Record<string, string> = {
  open: "tone-open",
  "in progress": "tone-progress",
  pending: "tone-pending",
  resolved: "tone-resolved",
};

export function StatusPill({ status }: { status: string | null }) {
  const tone = (status && STATUS_TONES[status.toLowerCase()]) || "tone-status";
  return (
    <span className={`pill ${tone}`}>
      <span className="dot" aria-hidden="true" />
      {status ? sentenceCase(status) : NOT_RECORDED}
    </span>
  );
}

const PRIORITY_TONES: Record<string, string> = { P1: "tone-p1", P2: "tone-p2" };

export function PriorityChip({ priority }: { priority: string | null }) {
  const tone = (priority && PRIORITY_TONES[priority]) || "tone-priority";
  return <span className={`chip ${tone}`}>{priority ?? NOT_RECORDED}</span>;
}

export function Panel({ id, title, meta, children }: {
  id: string; title: string; meta?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <section className="panel" aria-labelledby={id}>
      <div className="panel-head">
        <h2 id={id}>{title}</h2>
        {meta && <div className="panel-meta">{meta}</div>}
      </div>
      {children}
    </section>
  );
}

export function Facts({ items }: { items: [string, React.ReactNode][] }) {
  return (
    <dl className="facts">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

// Shown in place of a page's data when the API refuses or does not answer.
export function ApiProblemPanel({ problem }: { problem: ApiProblem }) {
  return (
    <Panel id="api-problem" title="The desk API did not return this page" meta={problem.status ? `HTTP ${problem.status}` : undefined}>
      <div className="panel-body">
        <p>{problem.message}</p>
        <p className="cell-sub">Code: {problem.code}</p>
      </div>
    </Panel>
  );
}
