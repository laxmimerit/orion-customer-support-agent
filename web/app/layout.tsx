import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Image from "next/image";

import { TopNav } from "@/components/top-nav";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["400", "600"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "Orion Service Desk", template: "%s · Orion Service Desk" },
  description: "Orion customer operations: ticket queue, case pages and reports.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <header className="topbar">
          <div className="topbar-in">
            <div className="brand">
              <Image src="/orion-logo.png" alt="Orion" width={114} height={28} priority />
              <span className="product">Service Desk</span>
            </div>
            <TopNav />
          </div>
        </header>
        <main className="page grid">{children}</main>
      </body>
    </html>
  );
}
