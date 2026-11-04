"use client";

import { usePathname, useSearchParams } from "next/navigation";
import { useEffect, useRef } from "react";

import { isBackToList } from "@/lib/detail-pages";

function focusLost() {
  return !document.activeElement || document.activeElement === document.body;
}

// A loading.tsx fallback is a <main> too, and it is replaced, so focus placed there would be lost again.
function readyMain() {
  const main = document.querySelector<HTMLElement>("main");
  return main && !main.querySelector(":scope > .skeleton") ? main : null;
}

// A ticket can be listed twice, and a row in a closed section can't take focus, so the first that does wins.
function focusLinkTo(main: HTMLElement, pathname: string) {
  for (const link of main.querySelectorAll<HTMLAnchorElement>("a[href]")) {
    if (link.pathname !== pathname) continue;
    link.focus();
    if (document.activeElement === link) return true;
  }
  return false;
}

// Back on a list, the row just left is where the reader was. Anywhere else, start at the content.
function placeFocus(main: HTMLElement, from: string, to: string) {
  if (isBackToList(from, to) && focusLinkTo(main, from)) return;
  // tabindex is set here, not on each page's <main>, so the many pages and their error states need no change.
  main.tabIndex = -1;
  main.focus({ preventScroll: true });
}

// A change of page removes the focused link, which drops focus to <body> and sends the Tab key back to the top.
// The query counts as a change too: the queue's Next link only changes ?page=. Focus that survived is left alone.
export function RouteFocus() {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const previous = useRef({ pathname, search });

  useEffect(() => {
    const from = previous.current;
    if (from.pathname === pathname && from.search === search) return;
    previous.current = { pathname, search };

    function settle() {
      if (!focusLost()) return true;
      const main = readyMain();
      if (main) placeFocus(main, from.pathname, pathname);
      return Boolean(main);
    }

    const column = document.getElementById("content");
    if (settle() || !column) return;
    const observer = new MutationObserver(() => {
      if (settle()) observer.disconnect();
    });
    observer.observe(column, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [pathname, search]);

  return null;
}
