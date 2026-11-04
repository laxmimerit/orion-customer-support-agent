"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

import "./customer.css";

// `retry` fetches the page again; `reset` would only redraw what already failed.
export default function CustomerError({ retry }: { retry: () => void }) {
  return (
    <main className="page is-detail cprof-page">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">This customer could not be shown</p>
          <p className="problem-text">Something went wrong while building this page.</p>
          <RetryButton target="this customer" onRetry={retry} />
        </div>
      </div>
    </main>
  );
}
