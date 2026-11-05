"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { syncMailbox } from "@/app/actions";
import { mailSyncSentence } from "@/lib/mail";

type Outcome = { failed: boolean; text: string };

// Copies new mail into the desk, then asks the server for the page again so the new mail shows.
export function MailSyncButton() {
  const router = useRouter();
  const [running, start] = useTransition();
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  function sync() {
    setOutcome(null);
    start(async () => {
      // A throw here would reach the page's error boundary and take the page down with it.
      try {
        const result = await syncMailbox();
        if (result.ok) {
          setOutcome({ failed: false, text: mailSyncSentence(result.sync) });
          router.refresh();
        } else {
          setOutcome({ failed: true, text: result.message });
        }
      } catch {
        setOutcome({ failed: true, text: "The desk did not answer. Check the connection and try again." });
      }
    });
  }

  return (
    <div className="mail-sync">
      <button className="button" type="button" disabled={running} onClick={sync}>Sync mail</button>
      <p className="mail-sync-hint">Copies new mail into the desk. Nothing is sent.</p>
      {/* Always mounted: a live region that arrives with its text often isn't read out. */}
      <p className={`mail-sync-status${outcome?.failed ? " is-failed" : ""}`} aria-live="polite" aria-atomic="true">
        {running ? "Syncing mail…" : outcome?.text}
      </p>
    </div>
  );
}
