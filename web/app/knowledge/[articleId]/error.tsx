"use client";

import { AlertIcon } from "@/components/icons";
import { RetryButton } from "@/components/retry-button";

// `retry` fetches the page again; `reset` would only redraw what already failed.
export default function ArticleError({ retry }: { retry: () => void }) {
  return (
    <main className="page is-detail">
      <div className="problem" role="alert">
        <AlertIcon />
        <div>
          <p className="problem-title">This article could not be shown</p>
          <p className="problem-text">Something went wrong while opening this page.</p>
          <RetryButton target="this article" onRetry={retry} />
        </div>
      </div>
    </main>
  );
}
