"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

// `retry` fetches the page again; `reset` would only redraw what already failed.
export default function UnlinkedMailError({ retry }: { retry: () => void }) {
  return (
    <main className="page">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">Unlinked mail could not be shown</p>
          <p className="problem-text">Something went wrong while building this page.</p>
          <RetryButton target="unlinked mail" onRetry={retry} />
        </div>
      </div>
    </main>
  );
}
