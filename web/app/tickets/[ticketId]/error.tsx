"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

export default function CaseError({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="page is-detail">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">This case could not be shown</p>
          <p className="problem-text">Something went wrong while opening this ticket. Nothing on it has changed.</p>
          <RetryButton onRetry={reset} />
        </div>
      </div>
    </main>
  );
}
