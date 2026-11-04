// Shared pieces of the Orion desk (notes/DESIGN.md).
import Link from "next/link";

import { AlertIcon, ApiIcon, ChatIcon, ChevronIcon, EmailIcon, LockIcon, WebIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";
import { SearchField } from "@/components/search";
import type { ApiProblem } from "@/lib/api";
import { NOT_RECORDED, sentenceCase } from "@/lib/format";

export function ViewOnly() {
  return <span className="view-only"><LockIcon />View only</span>;
}

export function TopBar({ children }: { children?: React.ReactNode }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        {children}
        <div className="topbar-end"><ViewOnly /></div>
      </div>
    </header>
  );
}

// Top bar for pages with nothing of their own to search: Enter searches tickets and help articles on the queue.
export function TicketSearchBar() {
  return (
    <TopBar>
      <SearchField label="Search tickets and help articles" placeholder="Search tickets and help articles" action="/" shortcut />
    </TopBar>
  );
}

export function PageHead({ title, description, children }: {
  title: string; description?: string; children?: React.ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-desc">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export function Crumbs({ parent, href, current }: { parent: string; href: string; current: string }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      <Link href={href}>{parent}</Link>
      <ChevronIcon />
      <span aria-current="page">{current}</span>
    </nav>
  );
}

const STATUS_TONES: Record<string, string> = {
  open: "tone-open",
  "in progress": "tone-progress",
  pending: "tone-pending",
  resolved: "tone-resolved",
};

export function StatusPill({ status, fixed = false }: { status: string | null; fixed?: boolean }) {
  const tone = (status && STATUS_TONES[status.toLowerCase()]) || "tone-missing";
  return (
    <span className={`pill ${tone}${fixed ? " is-fixed" : ""}`}>
      <span className="dot" aria-hidden="true" />
      {status ? sentenceCase(status.toLowerCase()) : NOT_RECORDED}
    </span>
  );
}

const PRIORITY_TILES: Record<string, string> = { P1: "tile-p1", P2: "tile-p2", P3: "tile-p3", P4: "tile-p4" };

export function PriorityTile({ priority, size }: { priority: string | null; size?: "sm" | "lg" }) {
  const tone = (priority && PRIORITY_TILES[priority]) || "tile-none";
  return (
    <span className={`tile ${tone}${size ? ` is-${size}` : ""}`}>
      <span className="visually-hidden">Priority </span>
      {priority ?? "None"}
    </span>
  );
}

export function ChannelIcon({ channel }: { channel: string | null }) {
  switch (channel?.toLowerCase()) {
    case "web": return <WebIcon />;
    case "api": return <ApiIcon />;
    case "chat": return <ChatIcon />;
    case "email": return <EmailIcon />;
    default: return null;
  }
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
export function ApiProblemPanel({ problem, title = "The desk API did not return this page" }: {
  problem: ApiProblem; title?: string;
}) {
  return (
    <div className="problem" role="alert">
      <AlertIcon />
      <div>
        <p className="problem-title">{title}</p>
        <p className="problem-text">{problem.message}</p>
        <p className="problem-code">{problem.status ? `HTTP ${problem.status} · ` : ""}{problem.code}</p>
        <RetryButton />
      </div>
    </div>
  );
}

// The body of a route's loading.tsx. `label` is read out; `shape` roughly matches the page to come.
export function PageLoading({ label, shape = ["block", "tall"], detail = false }: {
  label: string; shape?: ("block" | "tall")[]; detail?: boolean;
}) {
  return (
    <>
      <TopBar />
      <main className={`page${detail ? " is-detail" : ""}`}>
        <div className="skeleton" role="status" aria-busy="true" aria-live="polite">
          <span className="visually-hidden">{label}</span>
          <div className="skeleton-title" aria-hidden="true">
            <span className="bone is-title" />
            <span className="bone is-line" />
          </div>
          {shape.map((kind, index) => <span key={index} className={`bone is-${kind}`} aria-hidden="true" />)}
        </div>
      </main>
    </>
  );
}
