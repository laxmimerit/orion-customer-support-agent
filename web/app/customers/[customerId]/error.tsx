"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

import "./customer.css";

export default function CustomerError({ reset }: { reset: () => void }) {
  return (
    <main className="page is-detail cprof-page">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">This customer could not be shown</p>
          <p className="problem-text">Something went wrong while building this page.</p>
          <RetryButton onRetry={reset} />
        </div>
      </div>
    </main>
  );
}
