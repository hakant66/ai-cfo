"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";
import { useAuthedSWR } from "@/hooks/useApi";
import SetupTabs from "@/app/administrator/setup-tabs";

const API_BASE = resolveApiBase();

const rateItemSchema = z.object({
  pair: z.string(),
  rate: z.number(),
  updated_at: z.string(),
  manual_override: z.boolean()
});

const ratesSchema = z.object({
  items: z.array(rateItemSchema)
});

type RateItem = z.infer<typeof rateItemSchema>;

const wantedPairs = [
  "EUR/GBP",
  "GBP/USD",
  "EUR/USD",
  "CNY/USD",
  "CNY/GBP",
  "CNY/EUR",
  "GBP/TRY",
  "USD/TRY",
  "EUR/TRY"
];

async function fetchRates() {
  const token = getToken();
  const res = await fetch(`${API_BASE}/exchange-rates`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: "no-store"
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Request failed");
  }
  const payload = await res.json();
  return ratesSchema.parse(payload).items;
}

export default function ExchangeRatesPage() {
  const router = useRouter();
  const { data, error, mutate } = useSWR("exchange-rates", fetchRates);
  const { data: me } = useAuthedSWR<{ role: string }>("/auth/me");
  const { data: company } = useAuthedSWR<any>("/companies/me");
  const [status, setStatus] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  const canEdit = me?.role === "Founder" || me?.role === "Finance";

  const refreshRates = async () => {
    setStatus(null);
    setRefreshing(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/exchange-rates/refresh`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      const requestId = res.headers.get("x-request-id");
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Refresh failed${requestId ? ` (${requestId})` : ""}`);
      }
      await mutate();
      setStatus("Rates refreshed.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to refresh rates.";
      setStatus(message);
    } finally {
      setRefreshing(false);
    }
  };

  const saveRate = async (pair: string) => {
    const value = editing[pair];
    if (!value) return;
    setSaving(pair);
    setStatus(null);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/exchange-rates/${encodeURIComponent(pair)}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ rate: Number(value) })
      });
      const requestId = res.headers.get("x-request-id");
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Update failed${requestId ? ` (${requestId})` : ""}`);
      }
      await mutate();
      setStatus(`Manual override saved for ${pair}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update rate.";
      setStatus(message);
    } finally {
      setSaving(null);
    }
  };

  const trackedPairs = Array.isArray(company?.thresholds?.tracked_currency_pairs) && company.thresholds.tracked_currency_pairs.length > 0
    ? company.thresholds.tracked_currency_pairs
    : wantedPairs;
  const items = data
    ? trackedPairs.map((pair: string) => data.find((row) => row.pair === pair)).filter(Boolean) as RateItem[]
    : [];
  const trackedLabel = trackedPairs.join(", ");

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Exchange rates</h1>
        <p className="text-ink/70">Capture FX rates from the live provider and store the timestamped snapshot.</p>
      </div>

      <SetupTabs />

      <Card className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Tracked pairs</h2>
            <p className="text-sm text-ink/70">{trackedLabel || "No tracked pairs configured."}</p>
          </div>
          <Button type="button" onClick={refreshRates} disabled={refreshing}>
            {refreshing ? "Capturing..." : "Capture latest rates"}
          </Button>
        </div>
        {status && <p className="text-sm text-ink/70">{status}</p>}
      </Card>

      {error && <p className="text-sm text-crimson">Failed to load rates. {error.message}</p>}
      {!data && !error && <p className="text-sm text-ink/70">Loading rates...</p>}

      {data && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-3 text-left">Pair</th>
                <th className="px-4 py-3 text-right">Rate</th>
                <th className="px-4 py-3 text-right">Source</th>
                <th className="px-4 py-3 text-right">Captured at</th>
                {canEdit && <th className="px-4 py-3 text-right">Manual override</th>}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.pair} className="border-t border-fog">
                  <td className="px-4 py-3 font-semibold">{item.pair}</td>
                  <td className="px-4 py-3 text-right">{item.rate.toFixed(6)}</td>
                  <td className="px-4 py-3 text-right">{item.manual_override ? "Manual" : "Live"}</td>
                  <td className="px-4 py-3 text-right">{item.updated_at}</td>
                  {canEdit && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <input
                          className="w-28 rounded-md border border-fog px-2 py-1 text-right"
                          type="number"
                          step="0.000001"
                          value={editing[item.pair] ?? ""}
                          onChange={(event) => setEditing((prev) => ({ ...prev, [item.pair]: event.target.value }))}
                          placeholder={item.rate.toFixed(6)}
                        />
                        <Button type="button" variant="ghost" onClick={() => saveRate(item.pair)} disabled={saving === item.pair}>
                          {saving === item.pair ? "Saving..." : "Save"}
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-ink/60" colSpan={3}>
                    No rates captured yet. Click "Capture latest rates".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}

      <Button type="button" variant="ghost" onClick={() => router.push("/administrator")}>
        Back
      </Button>
    </div>
  );
}
