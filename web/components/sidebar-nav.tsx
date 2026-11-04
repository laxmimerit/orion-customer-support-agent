"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { CompanyIcon, CustomersIcon, KnowledgeIcon, ReportsIcon, SettingsIcon, TicketsIcon } from "@/components/icons";

const MAIN = [
  { href: "/", label: "Tickets", Icon: TicketsIcon, matches: (path: string) => path === "/" || path.startsWith("/tickets") },
  { href: "/customers", label: "Customers", Icon: CustomersIcon, matches: (path: string) => path.startsWith("/customers") },
  { href: "/knowledge", label: "Knowledge", Icon: KnowledgeIcon, matches: (path: string) => path.startsWith("/knowledge") },
  { href: "/reports", label: "Reports", Icon: ReportsIcon, matches: (path: string) => path.startsWith("/reports") },
  { href: "/company", label: "Company", Icon: CompanyIcon, matches: (path: string) => path.startsWith("/company") },
];

function NavLink({ item, pathname }: { item: (typeof MAIN)[number]; pathname: string }) {
  return (
    <Link href={item.href} className="side-link" aria-current={item.matches(pathname) ? "page" : undefined}>
      <item.Icon />
      {item.label}
    </Link>
  );
}

// Moves focus itself: a plain jump to #content adds a history entry that the router cannot go Back to.
export function SkipLink() {
  function skip(event: React.MouseEvent<HTMLAnchorElement>) {
    const column = document.getElementById("content");
    if (!column) return;
    event.preventDefault();
    column.focus({ preventScroll: true });
    column.scrollIntoView();
  }
  return <a className="skip-link" href="#content" onClick={skip}>Skip to content</a>;
}

export function SidebarNav() {
  const pathname = usePathname();
  const settings = { href: "/settings", label: "Settings", Icon: SettingsIcon, matches: (path: string) => path.startsWith("/settings") };
  return (
    <>
      <nav className="side-nav" aria-label="Main">
        <span className="side-nav-label">Workspace</span>
        {MAIN.map((item) => <NavLink key={item.href} item={item} pathname={pathname} />)}
      </nav>
      <nav className="side-nav side-nav-foot" aria-label="Desk settings">
        <NavLink item={settings} pathname={pathname} />
      </nav>
    </>
  );
}
