import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Image from "next/image";
import Link from "next/link";

import { DetailPending } from "@/components/detail-pending";
import { RouteFocus } from "@/components/route-focus";
import { SidebarNav, SkipLink } from "@/components/sidebar-nav";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });

export const metadata: Metadata = {
  title: { default: "Orion desk", template: "%s · Orion desk" },
  description: "Orion customer operations: tickets, customers, knowledge, reports and the company handbook.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <SkipLink />
        <DetailPending />
        <RouteFocus />
        <div className="frame">
          <aside className="side" aria-label="Desk navigation">
            <Link className="side-logo" href="/" aria-label="Orion desk, ticket queue">
              {/* Served as the file itself: /_next/image answers 404 on the Vercel deployment. The file's own size; CSS sets 24px high. */}
              <Image src="/orion-logo.png" alt="Orion" width={1040} height={256} priority unoptimized />
            </Link>
            <div className="side-navs">
              <SidebarNav />
            </div>
          </aside>
          <div className="column" id="content" tabIndex={-1}>{children}</div>
        </div>
      </body>
    </html>
  );
}
