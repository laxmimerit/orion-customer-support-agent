import type { Metadata } from "next";
import Image from "next/image";

import { SidebarNav } from "@/components/sidebar-nav";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Orion Service Desk", template: "%s · Orion Service Desk" },
  description: "Orion customer operations: ticket queue, case pages and settings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="frame">
          <header className="masthead">
            <Image className="masthead-logo" src="/orion-logo.png" alt="Orion" width={120} height={30} priority />
            <div className="masthead-product">
              <strong>Service Desk</strong>
              <span>Customer operations</span>
            </div>
            <div className="masthead-tag">PROTOTYPE</div>
          </header>
          <div className="body-row">
            <aside className="sidebar">
              <SidebarNav />
            </aside>
            <main className="main">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
