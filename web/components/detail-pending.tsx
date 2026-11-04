"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { detailLoadingLabel } from "@/lib/detail-pages";

// Detail pages have no loading.tsx, so that a missing record can answer 404. The old page stays up until the
// new one is ready, and this shows the click was taken. It watches the document, so every detail link is covered.
export function DetailPending() {
  const pathname = usePathname();
  const [opening, setOpening] = useState<{ from: string; label: string } | null>(null);

  // Any change of address ends the wait, including Back and a click on a link to somewhere else.
  if (opening && opening.from !== pathname) setOpening(null);

  useEffect(() => {
    function onClick(event: MouseEvent) {
      // A modified click opens another tab or window, and this page stays where it is.
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = event.target instanceof Element ? event.target.closest<HTMLAnchorElement>("a[href]") : null;
      if (!link || link.target || link.origin !== location.origin || link.pathname === location.pathname) return;
      const label = detailLoadingLabel(link.pathname);
      if (label) setOpening({ from: pathname, label });
    }
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [pathname]);

  return (
    <>
      {opening && <div className="detail-pending" aria-hidden="true" />}
      <div className="visually-hidden" role="status">{opening?.label}</div>
    </>
  );
}
