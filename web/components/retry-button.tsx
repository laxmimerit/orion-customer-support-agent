"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

// Asks the server for the page again. `onRetry` replaces that where there is something else to reset.
export function RetryButton({ onRetry }: { onRetry?: () => void }) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <button type="button" className="button" disabled={pending}
      onClick={() => (onRetry ? onRetry() : start(() => router.refresh()))}>
      {pending ? "Trying again" : "Try again"}
    </button>
  );
}
