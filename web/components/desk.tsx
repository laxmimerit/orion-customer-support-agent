// Shared pieces of the Orion desk (notes/design-brief.md, Design system).
import Link from "next/link";

import type { ApiProblem } from "@/lib/api";
import { NOT_RECORDED, sentenceCase } from "@/lib/format";

type Crumb = { label: string; href?: string };

const READ_ONLY = "Read-only. Values come from the Orion desk API.";

export function PageHeading({ crumbs, title, notice = READ_ONLY, children }: {
  crumbs: Crumb[]; title: string; notice?: string; children?: React.ReactNode;
}) {
  return (
    <div className="sub">
      <div className="c8">
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
      <p className="notice c4">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true">
          <rect x="5" y="11" width="14" height="9" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
        {notice}
      </p>
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

export function Panel({ id, title, meta, className = "", children }: {
  id: string; title: string; meta?: React.ReactNode; className?: string; children: React.ReactNode;
}) {
  return (
    <section className={`panel ${className}`} aria-labelledby={id}>
      <div className="panel-head">
        <h2 id={id}>{title}</h2>
        {meta && <div className="panel-meta">{meta}</div>}
      </div>
      {children}
    </section>
  );
}

export function Facts({ items, className = "" }: { items: [string, React.ReactNode][]; className?: string }) {
  return (
    <dl className={`facts ${className}`}>
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
// `heading`, `cannotLoad` and `refused` name what this page could not show.
export function ApiProblemPanel({ problem, heading, cannotLoad, refused }: {
  problem: ApiProblem; heading: string; cannotLoad: string; refused: string;
}) {
  const isRefused = problem.status === 401;
  const isDown = problem.status === null || problem.status === 503;
  return (
    <section className="panel c12" role="alert" aria-labelledby="api-problem">
      <h2 id="api-problem">{isRefused ? "The desk’s access was refused" : heading}</h2>
      <div className="panel-body">
        {isRefused ? (
          <p>The Orion desk API refused this desk’s token, so {refused}. Ask whoever manages the desk’s API access for a new token.</p>
        ) : isDown ? (
          <p>The Orion desk API isn’t responding, so {cannotLoad}. Reload the page to try again.</p>
        ) : (
          <p>The Orion desk API answered with an error, so {cannotLoad}.</p>
        )}
      </div>
      {!isDown && (
        <Facts className="facts-narrow" items={[
          ["Status", problem.status],
          ["Code", problem.code],
          ["Message", problem.message],
        ]} />
      )}
    </section>
  );
}
