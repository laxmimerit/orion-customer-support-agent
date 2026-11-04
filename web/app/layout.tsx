import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Image from "next/image";
import Link from "next/link";

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
        <div className="frame">
          <aside className="side" aria-label="Desk navigation">
            <Link className="side-logo" href="/" aria-label="Orion desk, ticket queue">
              {/* Served as the file itself: /_next/image answers 404 on the Vercel deployment. */}
              <Image src="/orion-logo.png" alt="Orion" width={98} height={24} priority unoptimized />
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
