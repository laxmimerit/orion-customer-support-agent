"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { type PreviewResult, ticketPreview } from "@/app/actions";
import { ChannelIcon, Facts, PageHead, PriorityTile, StatusPill, TopBar } from "@/components/desk";
import { AlertIcon, CheckIcon, FilterIcon, ForwardIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";
import { SearchField } from "@/components/search";
import type { TicketPage, TicketSummary } from "@/lib/api";
import { queueHref, ticketHref } from "@/lib/detail-pages";
import { NOT_RECORDED, channelLabel, duration, isResolved, orNotRecorded, plural, sentenceCase } from "@/lib/format";
import { lateLabel, slaResult, toHours } from "@/lib/sla";

type Lane = "now" | "next" | "pending" | "done" | "missing";
type QueueTicket = TicketSummary & { lane: Lane; rank: number };

const PRIORITIES = ["P1", "P2", "P3", "P4"];
const STATUSES = ["open", "in progress", "pending", "resolved"];
const NOT_LISTED = PRIORITIES.length + STATUSES.length;

function statusOf(ticket: TicketSummary) {
  return ticket.status?.toLowerCase() ?? "";
}

function place(list: string[], value: string | null) {
  const at = list.indexOf(value ?? "");
  return at === -1 ? NOT_LISTED : at;
}

// A ticket missing the status or priority that would rank it gets its own lane, so no lane heading
// claims something the ticket does not record.
function laneOf(priority: string | null, status: string): Lane {
  if (status === "resolved") return "done";
  if (status === "pending") return "pending";
  if (status !== "open" && status !== "in progress") return "missing";
  if (priority === "P1" || priority === "P2") return "now";
  return priority === "P3" || priority === "P4" ? "next" : "missing";
}

// Priority first, then status, then the API's order. Only tickets waiting on an agent get a rank.
function rankTickets(items: TicketSummary[]): QueueTicket[] {
  const ranked = items
    .map((ticket) => ({ ...ticket, lane: laneOf(ticket.priority, statusOf(ticket)), rank: 0 }))
    .sort((a, b) => place(PRIORITIES, a.priority) - place(PRIORITIES, b.priority)
      || place(STATUSES, statusOf(a)) - place(STATUSES, statusOf(b)));
  ranked.filter((ticket) => ticket.lane === "now" || ticket.lane === "next")
    .forEach((ticket, index) => { ticket.rank = index + 1; });
  return ranked;
}

function categoryLabel(category: string | null) {
  return category ? sentenceCase(category) : NOT_RECORDED;
}

function subjectOf(ticket: TicketSummary) {
  return ticket.subject ?? "No subject recorded";
}

function SearchBar({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const router = useRouter();
  return (
    <TopBar>
      <SearchField
        label="Search tickets and help articles"
        placeholder="Search tickets and help articles"
        value={value}
        onChange={onChange}
        action="/"
        shortcut
        onSubmit={(words) => {
          const query = words.trim();
          router.push(query ? `/?q=${encodeURIComponent(query)}` : "/");
        }}
      />
    </TopBar>
  );
}

// The top bar on the search results and when the queue failed: there is no list here to filter.
export function QueueSearch({ initial }: { initial: string }) {
  const [words, setWords] = useState(initial);
  return <SearchBar value={words} onChange={setWords} />;
}

export function Queue({ items, page, page_size, total, description, children }: TicketPage & {
  description: string;
  children: React.ReactNode;
}) {
  const [words, setWords] = useState("");
  const [cell, setCell] = useState<string | null>(null);
  const [pickedId, setPickedId] = useState<string | null>(null);
  const [doneOpen, setDoneOpen] = useState<boolean | null>(null);
  const panel = useRef<HTMLDivElement>(null);

  const all = useMemo(() => rankTickets(items), [items]);
  const selected = all.find((ticket) => ticket.ticket_id === pickedId)
    ?? all.find((ticket) => ticket.rank === 1) ?? all[0] ?? null;

  const needle = words.trim().toLowerCase();
  const narrowed = Boolean(cell || needle);
  const shown = all.filter((ticket) =>
    (!cell || `${ticket.priority}|${statusOf(ticket)}` === cell)
    && (!needle || [ticket.subject, ticket.ticket_id, ticket.customer_id, ticket.agent_id]
      .join(" ").toLowerCase().includes(needle)));
  const lane = (name: Lane) => shown.filter((ticket) => ticket.lane === name);
  const nowItems = lane("now");
  const nextItems = lane("next");
  const pendingItems = lane("pending");
  const missingItems = lane("missing");
  const doneItems = lane("done");
  const showDone = doneOpen ?? narrowed;
  const visible = showDone ? shown.length : shown.length - doneItems.length;

  const needCount = all.filter((ticket) => ticket.rank > 0).length;
  const nowCount = all.filter((ticket) => ticket.lane === "now").length;
  const pages = Math.max(1, Math.ceil(total / page_size));

  // On a phone the panel sits under the list, so a tap would otherwise change nothing in view.
  function pick(ticketId: string) {
    setPickedId(ticketId);
    if (window.matchMedia("(max-width: 799px)").matches) panel.current?.scrollIntoView({ block: "start" });
  }

  const rowProps = { page, selectedId: selected?.ticket_id ?? null, onPick: pick };
  const [cellPriority, cellStatus] = cell ? cell.split("|") : ["", ""];

  return (
    <>
      <SearchBar value={words} onChange={setWords} />
      <main className="page">
        <PageHead title="Ticket queue" description={description}>
          <div className="queue-need">
            <span className="queue-need-count">{needCount}</span>
            <span>{needCount === 1 ? "needs" : "need"} an agent on this page · {nowCount} now</span>
          </div>
        </PageHead>

        {children}

        <p className="visually-hidden" role="status">
          {plural(visible, "ticket")} shown on this page{cell && `, ${cellPriority} ${sentenceCase(cellStatus)} only`}
        </p>

        {cell && (
          <div className="queue-filter">
            <FilterIcon />
            <span>Showing <strong>{cellPriority} · {sentenceCase(cellStatus)}</strong></span>
            <button type="button" onClick={() => setCell(null)}>Clear</button>
          </div>
        )}

        {all.length > 0 && (nowItems.length > 0 || !narrowed) && (
          <section className="queue-now" aria-labelledby="queue-lane-now">
            <div className="queue-lane-head">
              <h2 id="queue-lane-now" className="is-large"><span className="queue-lane-dot is-now" />Needs an agent now</h2>
              <span>P1 and P2, open or in progress</span>
            </div>
            {nowItems.length ? (
              <ul className="queue-cards">
                {nowItems.map((ticket) => <li key={ticket.ticket_id}><NowCard ticket={ticket} {...rowProps} /></li>)}
              </ul>
            ) : <p className="queue-lane-empty">No P1 or P2 ticket is waiting on this page.</p>}
          </section>
        )}

        <div className="split queue-split">
          <div className="split-main">
            <section className="card queue-list" aria-label="Rest of the queue">
              {all.length === 0 && <NoTickets total={total} pages={pages} />}

              {all.length > 0 && shown.length === 0 && (
                <div className="empty">
                  <p className="empty-title">No tickets on this page match</p>
                  <p className="empty-hint">Clear the search or the filter, or press Enter to search the whole desk.</p>
                </div>
              )}

              {all.length > 0 && (nextItems.length > 0 || !narrowed) && (
                <div className="queue-lane">
                  <div className="queue-lane-head">
                    <h2><span className="queue-lane-dot is-next" />Up next</h2>
                    <span>P3 and P4, open or in progress · {nextItems.length}</span>
                  </div>
                  {nextItems.length ? (
                    <ul className="queue-rows">
                      {nextItems.map((ticket) => <li key={ticket.ticket_id}><QueueRow ticket={ticket} {...rowProps} /></li>)}
                    </ul>
                  ) : <p className="queue-lane-empty">No P3 or P4 ticket is waiting on this page.</p>}
                </div>
              )}

              {all.length > 0 && (pendingItems.length > 0 || !narrowed) && (
                <div className="queue-lane is-pending">
                  <div className="queue-lane-head">
                    <h2 className="is-small"><span className="queue-lane-dot is-pending" />Pending</h2>
                    <span>Not waiting on an agent right now · {pendingItems.length}</span>
                  </div>
                  {pendingItems.length ? (
                    <ul className="queue-minis">
                      {pendingItems.map((ticket) => (
                        <li key={ticket.ticket_id}>
                          <MiniRow ticket={ticket} {...rowProps} lead={<PriorityTile priority={ticket.priority} size="sm" />}
                            detail={<>{orNotRecorded(ticket.customer_id)} · <AgentText agent={ticket.agent_id} /></>} />
                        </li>
                      ))}
                    </ul>
                  ) : <p className="queue-lane-empty">No pending tickets on this page.</p>}
                </div>
              )}

              {missingItems.length > 0 && (
                <div className="queue-lane">
                  <div className="queue-lane-head">
                    <h2 className="is-small"><span className="queue-lane-dot is-missing" />Status or priority not recorded</h2>
                    <span>Not ranked · {missingItems.length}</span>
                  </div>
                  <ul className="queue-minis">
                    {missingItems.map((ticket) => (
                      <li key={ticket.ticket_id}>
                        <MiniRow ticket={ticket} {...rowProps} lead={<PriorityTile priority={ticket.priority} size="sm" />}
                          detail={<>{orNotRecorded(ticket.customer_id)} · <AgentText agent={ticket.agent_id} /></>}
                          end={<StatusPill status={ticket.status} />} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {all.length > 0 && (doneItems.length > 0 || !narrowed) && (
                <div className="queue-done">
                  {/* The list only exists while open, so the toggle only points at it then. */}
                  <button type="button" className="queue-done-toggle" aria-expanded={showDone}
                    aria-controls={showDone ? "queue-done-list" : undefined}
                    onClick={() => setDoneOpen(!showDone)}>
                    <span className="queue-lane-dot is-done" />
                    <span className="queue-done-title">Resolved</span>
                    <span className="queue-done-count">{doneItems.length} on this page</span>
                    <span className="queue-done-action">{showDone ? "Hide" : "Show"}</span>
                  </button>
                  {showDone && (doneItems.length ? (
                    <ul id="queue-done-list" className="queue-minis is-done">
                      {doneItems.map((ticket) => (
                        <li key={ticket.ticket_id}>
                          <MiniRow ticket={ticket} {...rowProps} lead={<span className="queue-check"><CheckIcon /></span>}
                            detail={<>{orNotRecorded(ticket.priority)} · <AgentText agent={ticket.agent_id} /></>} />
                        </li>
                      ))}
                    </ul>
                  ) : <p id="queue-done-list" className="queue-lane-empty">No resolved tickets on this page.</p>)}
                </div>
              )}

              <nav className="queue-paging" aria-label="Queue pages">
                <span>Page {page} of {pages} · {page_size} tickets per page · {total} in all</span>
                <div className="queue-paging-links">
                  <PageLink page={page - 1} disabled={page <= 1}>Previous</PageLink>
                  <PageLink page={page + 1} disabled={page >= pages}>Next</PageLink>
                </div>
              </nav>
            </section>
          </div>

          {selected && (
            <aside className="split-rail queue-rail" aria-label="Triage and preview">
              <Glance tickets={all} cell={cell} onCell={setCell} />
              <div className="queue-panel-anchor" ref={panel}>
                <Preview
                  ticket={selected}
                  page={page}
                  similar={all.filter((ticket) =>
                    ticket.subject !== null && ticket.subject === selected.subject && ticket.ticket_id !== selected.ticket_id)}
                  onPick={pick}
                />
              </div>
            </aside>
          )}
        </div>
      </main>
    </>
  );
}

function NoTickets({ total, pages }: { total: number; pages: number }) {
  if (total === 0) {
    return <div className="empty"><p className="empty-title">There are no tickets in the desk</p></div>;
  }
  return (
    <div className="empty">
      <p className="empty-title">No tickets on this page</p>
      <p className="empty-hint">The queue has {plural(pages, "page")}.</p>
      <Link className="button" href="/">Go to the first page</Link>
    </div>
  );
}

function PageLink({ page, disabled, children }: { page: number; disabled: boolean; children: React.ReactNode }) {
  if (disabled) return <span className="button" role="link" aria-disabled="true">{children}</span>;
  return <Link className="button" href={queueHref(page)}>{children}</Link>;
}

type RowProps = { ticket: QueueTicket; page: number; selectedId: string | null; onPick: (ticketId: string) => void };

// Covers the whole row or card to select it. The subject link sits above it and opens the ticket.
function PickButton({ ticket, selected, onPick }: { ticket: TicketSummary; selected: boolean; onPick: (id: string) => void }) {
  return (
    <button type="button" className="queue-pick" aria-pressed={selected}
      aria-label={`Preview ${ticket.ticket_id}`} onClick={() => onPick(ticket.ticket_id)} />
  );
}

function SubjectLink({ ticket, page, className }: { ticket: TicketSummary; page: number; className: string }) {
  return (
    <Link className={`queue-subject ${className}`} href={ticketHref(ticket.ticket_id, page)} prefetch={false}>
      {subjectOf(ticket)}
    </Link>
  );
}

function Rank({ rank, solid = false }: { rank: number; solid?: boolean }) {
  return (
    <span className={`queue-rank${solid ? " is-solid" : ""}`}>
      <span className="visually-hidden">Rank </span>{rank}
    </span>
  );
}

function AgentBadge({ agent, soft = false }: { agent: string | null; soft?: boolean }) {
  return (
    <span className={`queue-agent${soft ? " is-soft" : ""}${agent ? "" : " is-missing"}`}>
      {agent ?? NOT_RECORDED}
    </span>
  );
}

// An agent ID inside a line of text. Only a screen reader needs the word.
function AgentText({ agent }: { agent: string | null }) {
  return <><span className="visually-hidden">Agent </span>{orNotRecorded(agent)}</>;
}

// The words and the icon say it, so the colour is never the only sign.
function LateMark({ ticket }: { ticket: TicketSummary }) {
  const label = lateLabel(ticket);
  return label && <span className="queue-late"><AlertIcon size={13} />{label}</span>;
}

function NowCard({ ticket, page, selectedId, onPick }: RowProps) {
  const selected = ticket.ticket_id === selectedId;
  const tone = selected ? " is-selected" : ticket.priority === "P1" ? " is-p1" : " is-p2";
  return (
    <div className={`queue-card${tone}`}>
      <PickButton ticket={ticket} selected={selected} onPick={onPick} />
      <span className="queue-card-top">
        <Rank rank={ticket.rank} solid />
        <PriorityTile priority={ticket.priority} size="lg" />
        <span className="queue-card-status"><StatusPill status={ticket.status} /></span>
      </span>
      <SubjectLink ticket={ticket} page={page} className="queue-card-title" />
      <span className="row-sub">
        <strong>{ticket.ticket_id}</strong> · {categoryLabel(ticket.category)} · {orNotRecorded(ticket.customer_id)}
      </span>
      <LateMark ticket={ticket} />
      <span className="queue-card-foot">
        <span className="queue-channel"><ChannelIcon channel={ticket.channel} />{channelLabel(ticket.channel)}</span>
        <span className="queue-channel">Agent<AgentBadge agent={ticket.agent_id} /></span>
      </span>
    </div>
  );
}

function QueueRow({ ticket, page, selectedId, onPick }: RowProps) {
  const selected = ticket.ticket_id === selectedId;
  return (
    <div className={`row queue-row${selected ? " is-selected" : ""}`}>
      <PickButton ticket={ticket} selected={selected} onPick={onPick} />
      <span className="queue-row-lead">
        <Rank rank={ticket.rank} />
        <PriorityTile priority={ticket.priority} />
      </span>
      <span className="row-text">
        <SubjectLink ticket={ticket} page={page} className="queue-row-title" />
        <span className="row-sub queue-clip">
          <strong>{ticket.ticket_id}</strong> · {categoryLabel(ticket.category)} · {orNotRecorded(ticket.customer_id)}
          {" · "}{channelLabel(ticket.channel)}
        </span>
        <LateMark ticket={ticket} />
      </span>
      <span className="queue-row-end">
        <StatusPill status={ticket.status} fixed />
        <span className="visually-hidden">Agent </span>
        <AgentBadge agent={ticket.agent_id} soft />
      </span>
    </div>
  );
}

function MiniRow({ ticket, page, selectedId, onPick, lead, detail, end }: RowProps & {
  lead: React.ReactNode; detail: React.ReactNode; end?: React.ReactNode;
}) {
  const selected = ticket.ticket_id === selectedId;
  return (
    <div className={`queue-mini${selected ? " is-selected" : ""}`}>
      <PickButton ticket={ticket} selected={selected} onPick={onPick} />
      {lead}
      <span className="queue-mini-text">
        <SubjectLink ticket={ticket} page={page} className="queue-mini-title" />
        <span className="queue-mini-sub">{ticket.ticket_id} · {detail}</span>
        <LateMark ticket={ticket} />
      </span>
      {end}
    </div>
  );
}

function Glance({ tickets, cell, onCell }: {
  tickets: QueueTicket[]; cell: string | null; onCell: (cell: string | null) => void;
}) {
  const left = tickets.filter((ticket) =>
    !PRIORITIES.includes(ticket.priority ?? "") || !STATUSES.includes(statusOf(ticket))).length;
  return (
    <div className="card queue-glance">
      <div className="queue-glance-head">
        <h2 className="card-title">This page at a glance</h2>
        <span className="card-meta">Tap a cell to filter</span>
      </div>
      <div className="queue-matrix" role="group" aria-label="Filter this page by priority and status">
        <span />
        {STATUSES.map((status) => <span key={status} className="queue-matrix-col">{sentenceCase(status)}</span>)}
        {PRIORITIES.map((priority) => [
          <span key={priority} className="queue-matrix-row">{priority}</span>,
          ...STATUSES.map((status) => {
            const key = `${priority}|${status}`;
            const count = tickets.filter((ticket) => ticket.priority === priority && statusOf(ticket) === status).length;
            const active = cell === key;
            const heat = count === 0 ? "is-zero" : `is-${laneOf(priority, status)}${priority === "P1" ? " is-p1" : ""}`;
            return (
              <button key={key} type="button" className={`queue-cell ${heat}`} aria-pressed={active}
                aria-label={`${priority} ${status}: ${plural(count, "ticket")}`}
                onClick={() => onCell(active ? null : key)}>
                {count}
              </button>
            );
          }),
        ])}
      </div>
      <div className="queue-glance-key">
        <span><span className="queue-swatch is-now" aria-hidden="true" />Needs an agent now</span>
        <span><span className="queue-swatch is-next" aria-hidden="true" />Up next</span>
        <span><span className="queue-swatch is-pending" aria-hidden="true" />Pending</span>
        <span><span className="queue-swatch is-done" aria-hidden="true" />Resolved</span>
      </div>
      {left > 0 && <p className="card-meta">{plural(left, "ticket")} with no status or priority left out of this grid.</p>}
    </div>
  );
}

function Preview({ ticket, page, similar, onPick }: {
  ticket: QueueTicket; page: number; similar: QueueTicket[]; onPick: (ticketId: string) => void;
}) {
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<{ key: string; result: PreviewResult } | null>(null);
  const ticketId = ticket.ticket_id;
  const key = `${ticketId}:${attempt}`;

  // `current` turns false when the selection moves on, so a slow answer cannot overwrite a newer one.
  useEffect(() => {
    let current = true;
    ticketPreview(ticketId)
      .catch((): PreviewResult => ({ ok: false, message: "The desk did not answer this request." }))
      .then((result) => { if (current) setLoaded({ key, result }); });
    return () => { current = false; };
  }, [key, ticketId]);

  const result = loaded?.key === key ? loaded.result : null;
  const company = result?.ok ? result.preview.company : null;

  return (
    <section className="card queue-preview" aria-labelledby="queue-preview-title">
      <p className="visually-hidden" role="status">Previewing {ticketId}, {subjectOf(ticket)}</p>
      <div className="queue-preview-head">
        <span className="queue-preview-id">{ticketId} · {channelLabel(ticket.channel)}</span>
        <h2 id="queue-preview-title">{subjectOf(ticket)}</h2>
        <div className="queue-preview-tags">
          <StatusPill status={ticket.status} />
          <PriorityTile priority={ticket.priority} />
          <span className="pill">{categoryLabel(ticket.category)}</span>
        </div>
      </div>

      <Facts items={[
        ["Customer", company ?? orNotRecorded(ticket.customer_id)],
        ["Agent", orNotRecorded(ticket.agent_id)],
        ["Channel", channelLabel(ticket.channel)],
        ["Category", categoryLabel(ticket.category)],
      ]} />

      <div className="queue-sla">
        {result === null && (
          <div className="queue-sla-loading" role="status" aria-busy="true">
            <span className="visually-hidden">Loading the reply and resolution targets for {ticketId}</span>
            <span className="bone" aria-hidden="true" />
            <span className="bone" aria-hidden="true" />
          </div>
        )}
        {result?.ok === false && (
          <div className="problem queue-preview-problem" role="alert">
            <AlertIcon />
            <div>
              <p className="problem-title">The targets for {ticketId} did not load</p>
              <p className="problem-text">{result.message}</p>
              <RetryButton target={`the targets for ${ticketId}`} onRetry={() => setAttempt((count) => count + 1)} />
            </div>
          </div>
        )}
        {result?.ok && <SlaBars status={ticket.status} {...result.preview} />}
      </div>

      {similar.length > 0 && (
        <div className="queue-similar">
          <h3>Same subject on this page</h3>
          <ul>
            {similar.map((other) => (
              <li key={other.ticket_id}>
                <button type="button" onClick={() => onPick(other.ticket_id)}>
                  <span>
                    <strong>{other.ticket_id}</strong> · {orNotRecorded(other.customer_id)} · <AgentText agent={other.agent_id} />
                  </span>
                  <StatusPill status={other.status} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link className="button is-primary" href={ticketHref(ticketId, page)} prefetch={false}>
        Open case<ForwardIcon />
      </Link>
    </section>
  );
}

// Both bars share one scale, so a long first reply and a short resolution read true against each other.
function SlaBars({ status, first_response_hours, sla_response_hours, resolution_hours, sla_resolution_hours }: {
  status: string | null;
  first_response_hours: string | null;
  sla_response_hours: string | null;
  resolution_hours: string | null;
  sla_resolution_hours: string | null;
}) {
  const firstReply = toHours(first_response_hours);
  const firstTarget = toHours(sla_response_hours);
  const resolved = toHours(resolution_hours);
  const resolveTarget = toHours(sla_resolution_hours);
  const scale = Math.max(firstReply ?? 0, firstTarget ?? 0, resolved ?? 0, resolveTarget ?? 0);
  // A ticket still in the queue has simply not got there yet; only a resolved one is missing a value.
  const closed = isResolved(status);
  return (
    <>
      <SlaBar label="First reply" spoken="First reply took" missing={closed ? NOT_RECORDED : "none yet"}
        value={firstReply} target={firstTarget} scale={scale} />
      <SlaBar label={resolved === null ? "Resolution" : "Resolved in"} spoken="Resolved in" missing={closed ? NOT_RECORDED : "not yet"}
        value={resolved} target={resolveTarget} scale={scale} />
    </>
  );
}

function SlaBar({ label, spoken, missing, value, target, scale }: {
  label: string; spoken: string; missing: string; value: number | null; target: number | null; scale: number;
}) {
  const result = slaResult(value, target);
  const verdict = result ? ` · ${result}` : "";
  const share = (part: number) => `${scale > 0 ? Math.round((part / scale) * 1000) / 10 : 0}%`;
  const took = value === null ? `${label}: ${missing}` : `${spoken} ${duration(value)}`;
  const against = target === null ? "no target recorded" : `against a ${duration(target)} target`;

  return (
    <div className="queue-sla-item">
      <div className="queue-sla-line">
        <span>{label} <strong>{value === null ? missing : duration(value)}</strong></span>
        <span className={result ? `is-${result}` : undefined}>
          {target === null ? "No target recorded" : `target ${duration(target)}${verdict}`}
        </span>
      </div>
      <div className="queue-sla-track" role="img" aria-label={`${took}, ${against}`}>
        {value !== null && <span className={`queue-sla-fill${result === "missed" ? " is-missed" : ""}`} style={{ width: share(value) }} />}
        {target !== null && <span className="queue-sla-mark" style={{ left: `calc(${share(target)} - 1px)` }} />}
      </div>
    </div>
  );
}
