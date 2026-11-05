"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";

import { saveNote } from "@/app/actions";

import "./mail.css";

export function NoteForm({ ticketId, agents }: { ticketId: string; agents: string[] }) {
  const router = useRouter();
  const [author, setAuthor] = useState(agents[0] ?? "");
  const [handedTo, setHandedTo] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setProblem(null);
    try {
      const result = await saveNote(ticketId, author, body, handedTo || null);
      if (result.ok) {
        setBody("");
        setHandedTo("");
        router.refresh();
      } else {
        setProblem(result.message);
      }
    } catch {
      setProblem("The desk did not answer. Check the connection and try again.");
    }
    setBusy(false);
  }

  return (
    <form className="note-form" onSubmit={submit}>
      <label>Your name
        <select value={author} onChange={(event) => setAuthor(event.target.value)}>
          {agents.map((name) => <option key={name}>{name}</option>)}
        </select>
      </label>
      <label>Note
        <textarea required maxLength={4000} rows={3} value={body} onChange={(event) => setBody(event.target.value)} />
      </label>
      <label>Hand off to
        <select value={handedTo} onChange={(event) => setHandedTo(event.target.value)}>
          <option value="">Nobody, just a note</option>
          {agents.filter((name) => name !== author).map((name) => <option key={name}>{name}</option>)}
        </select>
      </label>
      <button className="button" type="submit" disabled={busy || !body.trim()}>{handedTo ? "Hand off" : "Add note"}</button>
      {problem && <p className="mail-tools-result is-failed" role="alert">{problem}</p>}
    </form>
  );
}
