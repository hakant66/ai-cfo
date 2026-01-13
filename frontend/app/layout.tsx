import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "AI CFO",
  description: "CFO-grade decision system for retail SMEs",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen bg-slate-50">
          <header className="border-b bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <div className="text-xl font-semibold">AI CFO</div>
              <nav className="flex gap-4 text-sm text-slate-600">
                <a href="/dashboard" className="hover:text-slate-900">Dashboard</a>
                <a href="/inventory" className="hover:text-slate-900">Inventory</a>
                <a href="/payables" className="hover:text-slate-900">Payables</a>
                <a href="/chat" className="hover:text-slate-900">Ask CFO</a>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
