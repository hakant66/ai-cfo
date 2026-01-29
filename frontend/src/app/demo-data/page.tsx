"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";
import { useCompanyName } from "@/hooks/useCompany";
import SetupTabs from "@/app/administrator/setup-tabs";

const API_BASE = resolveApiBase();

export default function DemoDataPage() {
  const router = useRouter();
  const companyName = useCompanyName();
  const [status, setStatus] = useState<string | null>(null);
  const [clearStatus, setClearStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);

  const seedDemoData = async () => {
    setStatus(null);
    setClearStatus(null);
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/demo-data/seed`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      const requestId = res.headers.get("x-request-id");
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed${requestId ? ` (${requestId})` : ""}`);
      }
      const payload = await res.json();
      setStatus(`Demo data queued for ${payload.company_name}. Sync may take a minute.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to seed demo data.";
      setStatus(message);
    } finally {
      setLoading(false);
    }
  };

  const clearDemoData = async () => {
    setClearStatus(null);
    setStatus(null);
    setClearing(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/demo-data/clear`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      const requestId = res.headers.get("x-request-id");
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed${requestId ? ` (${requestId})` : ""}`);
      }
      const payload = await res.json();
      setClearStatus(`Demo data cleared for ${payload.company_name}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to clear demo data.";
      setClearStatus(message);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">
          Demo data{companyName ? ` - ${companyName}` : ""}
        </h1>
        <p className="text-ink/70">Re-seed and resync the demo company with mock Shopify data.</p>
      </div>

      <SetupTabs />

      <Card className="grid gap-3">
        <h2 className="text-lg font-semibold">Seed + sync demo company</h2>
        <p className="text-sm text-ink/70">This clears existing demo data, re-seeds local records, and queues a Shopify sync.</p>
        <Button type="button" onClick={seedDemoData} disabled={loading}>
          {loading ? "Seeding..." : `Create demo mock data${companyName ? ` for ${companyName}` : ""}`}
        </Button>
        {status && <p className="text-sm text-ink/70">{status}</p>}
      </Card>

      <Card className="grid gap-3">
        <h2 className="text-lg font-semibold">Clear demo data</h2>
        <p className="text-sm text-ink/70">Remove seeded demo transactions and snapshots for this company.</p>
        <Button type="button" variant="ghost" onClick={clearDemoData} disabled={clearing}>
          {clearing ? "Clearing..." : `Clear demo mock data${companyName ? ` for ${companyName}` : ""}`}
        </Button>
        {clearStatus && <p className="text-sm text-ink/70">{clearStatus}</p>}
      </Card>

      <Button type="button" variant="ghost" onClick={() => router.push("/administrator")}>
        Back
      </Button>
    </div>
  );
}
