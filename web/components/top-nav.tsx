"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Only pages that exist are listed: no placeholder items.
const ITEMS = [
  { href: "/", label: "Ticket queue", matches: (path: string) => path === "/" || path.startsWith("/tickets") },
  { href: "/reports", label: "Reports", matches: (path: string) => path.startsWith("/reports") },
];

export function TopNav() {
  const pathname = usePathname();
  return (
    <nav className="tabs" aria-label="Main">
      {ITEMS.map((item) => (
        <Link key={item.href} href={item.href} aria-current={item.matches(pathname) ? "page" : undefined}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
