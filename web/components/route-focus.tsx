"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

import { isBackToList } from "@/lib/detail-pages";

// tabindex is set here, not on each page's <main>, so the many pages and their error states need no change.
export function focusMain(main: HTMLElement, options?: FocusOptions) {
  main.tabIndex = -1;
  main.focus(options);
}

function focusLost() {
  return !document.activeElement || document.activeElement === document.body;
}

// A loading.tsx fallback is a <main> too, and it is replaced, so focus placed there would be lost again.
function readyMain() {
  const main = document.querySelector<HTMLElement>("main");
  return main && !main.querySelector(":scope > .skeleton") ? main : null;
}

// Back on a list, the row just left is where the reader was. Anywhere else, start at the content.
function placeFocus(main: HTMLElement, from: string, to: string) {
  const link = isBackToList(from, to) ? main.querySelector<HTMLElement>(`a[href="${CSS.escape(from)}"]`) : null;
  link?.focus();
  if (!link || document.activeElement !== link) focusMain(main, { preventScroll: true });
}

// A change of page removes the focused link, which drops focus to <body> and sends the Tab key back to the top.
// Focus that survived, such as on a sidebar link, is left where it is.
export function RouteFocus() {
  const pathname = usePathname();
  const previous = useRef(pathname);

  useEffect(() => {
    const from = previous.current;
    if (from === pathname) return;
    previous.current = pathname;

    function settle() {
      if (!focusLost()) return true;
      const main = readyMain();
      if (main) placeFocus(main, from, pathname);
      return Boolean(main);
    }

    const column = document.getElementById("content");
    if (settle() || !column) return;
    const observer = new MutationObserver(() => {
      if (settle()) observer.disconnect();
    });
    observer.observe(column, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [pathname]);

  return null;
}
