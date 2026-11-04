"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

// Asks the server for the page again. `onRetry` replaces that where there is something else to reset.
// `target` finishes the label, "Reload the ticket queue", so each button says what it fetches.
export function RetryButton({ target, onRetry }: { target: string; onRetry?: () => void }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <button type="button" className="button" disabled={pending}
      onClick={() => (onRetry ? onRetry() : start(() => router.refresh()))}>
      {pending ? `Reloading ${target}` : `Reload ${target}`}
    </button>
  );
}
