import { ApiProblemPanel } from "@/components/desk";
import { NoteForm } from "@/components/note-form";
import { caseNotes } from "@/lib/api";
import { actionTime } from "@/lib/compose";

// Streams in after the case. Notes stay on this card: no draft, mail or model reads them.
export async function CaseNotes({ ticketId }: { ticketId: string }) {
  const result = await caseNotes(ticketId);
  return (
    <section className="card mail-card" aria-labelledby="notes-title">
      <div className="card-head"><h2 id="notes-title">Internal notes</h2></div>
      <p className="mail-note">For agents only. Notes never reach a draft or a customer. A name is what someone picked, as the desk has no sign-in yet.</p>
      {!result.ok ? (
        <div className="mail-problem">
          <ApiProblemPanel problem={result.problem} title="The desk API did not return the notes" retryTarget="the notes" />
        </div>
      ) : (
        <>
          {result.data.items.length > 0 && (
            <ol className="mail-list">
              {result.data.items.map((note) => (
                <li className="mail-item" key={note.note_id}>
                  <div className="mail-meta">
                    <span className="mail-sender">{note.author}</span>
                    {note.handed_to && <span>Handed to {note.handed_to}</span>}
                    <span>{actionTime(note.noted_at)}</span>
                  </div>
                  <div className="mail-body">{note.body}</div>
                </li>
              ))}
            </ol>
          )}
          <NoteForm ticketId={ticketId} agents={result.data.agents} />
        </>
      )}
    </section>
  );
}
