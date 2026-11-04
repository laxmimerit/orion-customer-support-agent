"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { Facts, PriorityTile } from "@/components/desk";
import { ChevronIcon, ForwardIcon } from "@/components/icons";
import type { SimilarTicket } from "@/lib/api";
import { NOT_RECORDED, channelLabel, duration, matchedPhrase, orNotRecorded, plural, sentenceCase } from "@/lib/format";
import { slaResult, slaVerdict, toHours } from "@/lib/sla";

function why(fields: string[]) {
  return fields.length > 0 ? matchedPhrase(fields) : "Close in meaning; no recorded field is the same";
}

export function SimilarList({ items, topReply }: { items: SimilarTicket[]; topReply: string | null }) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <ol className="similar-list">
      {items.map((item) => (
        <Row key={item.ticket_id} item={item} topReply={topReply} isOpen={open === item.ticket_id}
          onToggle={() => setOpen(open === item.ticket_id ? null : item.ticket_id)} />
      ))}
    </ol>
  );
}

function Row({ item, topReply, isOpen, onToggle }: {
  item: SimilarTicket; topReply: string | null; isOpen: boolean; onToggle: () => void;
}) {
  const detailId = useId();
  const resolved = toHours(item.resolution_hours);
  const target = toHours(item.sla_resolution_hours);
  const result = slaResult(resolved, target);
  const rating = item.csat === null ? NOT_RECORDED : `${item.csat} / 5`;
  const reopened = item.reopened_count === null ? NOT_RECORDED : plural(item.reopened_count, "time");
  const sameReply = item.last_author_role === "agent" && item.last_body !== null && item.last_body === topReply;
  return (
    <li className={`similar-row${isOpen ? " is-open" : ""}`}>
      <button type="button" className="similar-toggle" aria-expanded={isOpen} aria-controls={detailId} onClick={onToggle}>
        <span className="similar-line">
          <PriorityTile priority={item.priority} size="sm" />
          <span className="similar-id">{item.ticket_id}</span>
          <span className="similar-match">{Math.round(item.similarity * 100)}% match</span>
          <ChevronIcon />
        </span>
        <span className="similar-result">
          <span>{item.resolution_hours === null ? `Resolution time: ${NOT_RECORDED}` : `Resolved in ${duration(item.resolution_hours)}`}</span>
          {result && <span className={result === "missed" ? "is-late" : "is-met"}>{slaVerdict(resolved, target)}</span>}
        </span>
        <span className="similar-outcome">Rating: {rating} · Reopened {reopened}</span>
        <span className="similar-why">{why(item.matched_on)}</span>
      </button>
      <div id={detailId} className="similar-detail" hidden={!isOpen}>
        <Facts items={[
          ["First reply", item.first_response_hours === null ? NOT_RECORDED : duration(item.first_response_hours)],
          ["Messages", String(item.message_count)],
          ["Agent", orNotRecorded(item.agent_id)],
          ["Escalated", item.escalated === null ? NOT_RECORDED : item.escalated > 0 ? "Yes" : "No"],
          ["Plan", item.plan_id ? sentenceCase(item.plan_id) : NOT_RECORDED],
          ["Channel", channelLabel(item.channel)],
        ]} />
        <div>
          <p className="similar-label">Last message · {item.last_author_role ? sentenceCase(item.last_author_role) : NOT_RECORDED}</p>
          <p className="similar-text">{sameReply ? "The same reply as above." : orNotRecorded(item.last_body)}</p>
        </div>
        <Link className="button similar-open" href={`/tickets/${encodeURIComponent(item.ticket_id)}`}>
          Open case {item.ticket_id}<ForwardIcon />
        </Link>
      </div>
    </li>
  );
}
