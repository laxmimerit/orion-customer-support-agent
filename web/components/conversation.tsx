"use client";

import { useState } from "react";

import { LockIcon } from "@/components/icons";
import type { Message } from "@/lib/api";
import { NOT_RECORDED, initial, plural } from "@/lib/format";

type Who = "all" | "customer" | "agent";

const FILTERS: [Who, string][] = [["all", "All"], ["customer", "Customer"], ["agent", "Agent"]];

export function Conversation({ messages, request, company, agentId }: {
  messages: Message[];
  request: string | null;
  company: string | null;
  agentId: string | null;
}) {
  const [who, setWho] = useState<Who>("all");

  // With no messages stored, the ticket's own text stands in as the customer's opening message.
  const openingOnly = messages.length === 0 && request !== null;
  const thread: Message[] = openingOnly
    ? [{ message_id: "request", author_role: "customer", body: request }]
    : messages;
  const shown = who === "all" ? thread : thread.filter((message) => message.author_role === who);
  const total = plural(thread.length, "message");
  const count = openingOnly ? "opening request only"
    : who === "all" || thread.length === 0 ? total : `${shown.length} of ${total}`;
  const emptyTitle = thread.length === 0 ? "No messages recorded" : `No ${who} messages`;
  // One string, so a screen reader hears the whole line each time the filter changes.
  const filterResult = shown.length === 0
    ? emptyTitle
    : `Showing ${shown.length} of ${total}${who === "all" ? "" : ` from the ${who}`}`;

  return (
    <section className="card case-conv" aria-labelledby="conv-title">
      <div className="card-head">
        <h2 id="conv-title">Conversation <span>· {count}</span></h2>
        <div className="segmented" role="group" aria-label="Show messages from">
          {FILTERS.map(([key, label]) => (
            <button key={key} type="button" aria-pressed={who === key} onClick={() => setWho(key)}>{label}</button>
          ))}
        </div>
      </div>

      {/* Always mounted: a live region that arrives with its text often isn't read out. */}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{filterResult}</p>

      {shown.length === 0 ? (
        <div className="empty">
          <p className="empty-title">{emptyTitle}</p>
          <p className="empty-hint">
            {thread.length === 0 ? "This ticket has no messages and no request text." : `This ticket has nothing from the ${who}.`}
          </p>
        </div>
      ) : (
        <ol className="conv-list">
          {shown.map((message) => {
            const isAgent = message.author_role === "agent";
            const isCustomer = message.author_role === "customer";
            const author = isAgent ? agentId : isCustomer ? company : null;
            return (
              <li key={message.message_id} className={`conv-item${isAgent ? " is-agent" : ""}`}>
                <span className="conv-avatar" aria-hidden="true">{isAgent ? (agentId ?? "?") : initial(author)}</span>
                <div className="conv-col">
                  <div className="conv-meta">
                    <span className="conv-author">{author ?? NOT_RECORDED}</span>
                    <span>{isAgent ? "Agent" : isCustomer ? "Customer" : `Role: ${NOT_RECORDED}`}</span>
                    {!openingOnly && <span>· {message.message_id}</span>}
                  </div>
                  <div className="conv-bubble">{message.body ?? NOT_RECORDED}</div>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      <div className="conv-note">
        <LockIcon size={18} strokeWidth={2} />
        <span>This desk is view only. You can read and follow the conversation here; replies aren&apos;t sent from this screen.</span>
      </div>
    </section>
  );
}
