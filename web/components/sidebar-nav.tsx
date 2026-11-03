"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Only pages that exist are listed: no placeholder items.
const ITEMS = [
  { href: "/", label: "Tickets", glyph: "▤", matches: (path: string) => path === "/" || path.startsWith("/tickets") },
  { href: "/settings", label: "Settings", glyph: "▦", matches: (path: string) => path.startsWith("/settings") },
];

export function SidebarNav() {
  const pathname = usePathname();
  return (
    <nav className="nav" aria-label="Workspace">
      <div className="nav-label">WORKSPACE</div>
      {ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="nav-item"
          aria-current={item.matches(pathname) ? "page" : undefined}
        >
          <span className="nav-glyph" aria-hidden="true">{item.glyph}</span>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
