"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

import "./customers.css";

export default function CustomersError({ reset }: { reset: () => void }) {
  return (
    <main className="page clist-page">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">The customer list could not be shown</p>
          <p className="problem-text">Something went wrong while building this page.</p>
          <RetryButton onRetry={reset} />
        </div>
      </div>
    </main>
  );
}
