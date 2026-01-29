import "./globals.css";
import { Header } from "@/components/header";

export const metadata = {
  title: "AI Assistant",
  description: "CFO-grade decision system for retail SMEs"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-100 text-ink">
        <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#f8fafc,_#e2e8f0_60%,_#cbd5f5)]">
          <Header />
          <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
