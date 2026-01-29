"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Card } from "@/components/ui/card";

export default function SetupTabs() {
  const pathname = usePathname();
  const [hash, setHash] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleHash = () => setHash(window.location.hash || "");
    handleHash();
    window.addEventListener("hashchange", handleHash);
    return () => window.removeEventListener("hashchange", handleHash);
  }, []);

  const activeTab = useMemo(() => {
    if (pathname === "/administrator/companies") return "companies";
    if (pathname === "/exchange-rates") return "fx";
    if (pathname === "/administrator/stripe") return "stripe";
    if (pathname === "/administrator/wise") return "wise";
    if (pathname === "/demo-data") return "demo";
    if (hash === "#shopify-api") return "shopify";
    return "setup";
  }, [hash, pathname]);

  const tabClass = (key: string) =>
    `text-sm font-semibold ${activeTab === key ? "rounded-full bg-ink/5 px-3 py-1 text-ink" : "text-ink/70 hover:text-ink"}`;

  const setupClass =
    activeTab === "setup"
      ? "rounded-full border border-ink/10 bg-ink/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-ink"
      : "rounded-full bg-ink px-4 py-2 text-xs font-semibold uppercase tracking-[0.3em] text-white";

  return (
    <Card className="flex flex-wrap items-center gap-4">
      <span className={setupClass}>Setup</span>
      <Link href="/administrator/companies" className={tabClass("companies")}>
        Companies
      </Link>
      <Link href="/exchange-rates" className={tabClass("fx")}>
        FX Rates
      </Link>
      <Link href="/administrator#shopify-api" className={tabClass("shopify")}>
        Shopify API
      </Link>
      <Link href="/administrator/stripe" className={tabClass("stripe")}>
        Stripe API
      </Link>
      <Link href="/administrator/wise" className={tabClass("wise")}>
        Wise API
      </Link>
      <Link href="/demo-data" className={tabClass("demo")}>
        Load Demo Data
      </Link>
    </Card>
  );
}
