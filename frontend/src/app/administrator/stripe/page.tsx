"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";
import SetupTabs from "@/app/administrator/setup-tabs";
import { useAuthedSWR } from "@/hooks/useApi";

const API_BASE = resolveApiBase();

type SyncResponse = {
  count: number;
};

type StripeSettings = {
  stripe_account: string | null;
  has_publishable_key: boolean;
  has_secret_key: boolean;
};

type BalancePayoutsResponse = {
  balance_count: number;
  payout_count: number;
  balance_history: BalanceHistoryItem[];
  payouts: PayoutItem[];
};

type BalanceHistoryItem = {
  transaction_id: string;
  date: string;
  amount_gross: number;
  fee: number;
  amount_net: number;
  currency: string;
  status: string;
  type: string;
  source_id?: string | null;
  description?: string | null;
};

type PayoutItem = {
  payout_id: string;
  amount: number;
  currency: string;
  status: string;
  arrival_date?: string | null;
  created_at: string;
  method?: string | null;
  payout_type?: string | null;
};

export default function StripeAdminPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [settingsStatus, setSettingsStatus] = useState<string | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const [stripeAccount, setStripeAccount] = useState("");
  const [publishableKey, setPublishableKey] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [balanceStatus, setBalanceStatus] = useState<string | null>(null);
  const [fetchingBalance, setFetchingBalance] = useState(false);
  const [balanceHistory, setBalanceHistory] = useState<BalanceHistoryItem[]>([]);
  const [payouts, setPayouts] = useState<PayoutItem[]>([]);

  const downloadCsv = (filename: string, rows: Record<string, string | number | null | undefined>[]) => {
    const header = rows.length ? Object.keys(rows[0]) : [];
    const escapeValue = (value: string | number | null | undefined) => {
      if (value === null || value === undefined) return "";
      const text = String(value);
      if (/[",\n]/.test(text)) {
        return `"${text.replace(/"/g, "\"\"")}"`;
      }
      return text;
    };
    const lines = [
      header.join(","),
      ...rows.map((row) => header.map((key) => escapeValue(row[key])).join(","))
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const exportBalanceCsv = () => {
    const dateSuffix = startDate || endDate ? `${startDate || "start"}_${endDate || "end"}` : "last_7_days";
    const companySuffix = settings?.stripe_account ? `_${settings.stripe_account}` : "";
    const rows = balanceHistory.map((item) => ({
      transaction_id: item.transaction_id,
      date: item.date,
      amount_gross: item.amount_gross,
      fee: item.fee,
      amount_net: item.amount_net,
      currency: item.currency,
      status: item.status,
      type: item.type,
      source_id: item.source_id || "",
      description: item.description || ""
    }));
    downloadCsv(`stripe_balance_history${companySuffix}_${dateSuffix}.csv`, rows);
  };

  const exportPayoutsCsv = () => {
    const dateSuffix = startDate || endDate ? `${startDate || "start"}_${endDate || "end"}` : "last_7_days";
    const companySuffix = settings?.stripe_account ? `_${settings.stripe_account}` : "";
    const rows = payouts.map((item) => ({
      payout_id: item.payout_id,
      amount: item.amount,
      currency: item.currency,
      status: item.status,
      arrival_date: item.arrival_date || "",
      created_at: item.created_at,
      method: item.method || "",
      payout_type: item.payout_type || ""
    }));
    downloadCsv(`stripe_payouts${companySuffix}_${dateSuffix}.csv`, rows);
  };

  const { data: settings, mutate: mutateSettings } = useAuthedSWR<StripeSettings>("/connectors/stripe/settings");

  const syncRevenue = async () => {
    setStatus(null);
    setLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/connectors/stripe/sync-revenue`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      const requestId = res.headers.get("x-request-id");
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Sync failed${requestId ? ` (${requestId})` : ""}`);
      }
      const payload = await res.json() as SyncResponse;
      setStatus(`Stripe revenue synced (${payload.count} items).`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Stripe sync failed.";
      setStatus(message);
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async () => {
    setSettingsStatus(null);
    setSavingSettings(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/connectors/stripe/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          stripe_account: stripeAccount || undefined,
          publishable_key: publishableKey || undefined,
          secret_key: secretKey || undefined
        })
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to save Stripe settings.");
      }
      await mutateSettings();
      setPublishableKey("");
      setSecretKey("");
      setSettingsStatus("Stripe settings saved.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save Stripe settings.";
      setSettingsStatus(message);
    } finally {
      setSavingSettings(false);
    }
  };

  const fetchBalancePayouts = async () => {
    setBalanceStatus(null);
    setFetchingBalance(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/connectors/stripe/balance-payouts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          start_date: startDate || undefined,
          end_date: endDate || undefined
        })
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to fetch Stripe balance history.");
      }
      const payload = await res.json() as BalancePayoutsResponse;
      setBalanceStatus(`Balance history: ${payload.balance_count} items. Payouts: ${payload.payout_count} items.`);
      setBalanceHistory(payload.balance_history || []);
      setPayouts(payload.payouts || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to fetch Stripe balance history.";
      setBalanceStatus(message);
    } finally {
      setFetchingBalance(false);
    }
  };

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Stripe API</h1>
        <p className="text-ink/70">Sync the last 30 days of revenue activity.</p>
      </div>

      <SetupTabs />

      <Card className="grid gap-4">
        <div>
          <h2 className="text-lg font-semibold">Connection settings</h2>
          <p className="text-sm text-ink/70">Store Stripe account identifiers and API keys for syncing.</p>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Stripe account (optional)</label>
          <input
            className="w-full rounded-md border border-fog px-3 py-2 text-sm"
            value={stripeAccount}
            onChange={(event) => setStripeAccount(event.target.value)}
            placeholder={settings?.stripe_account || "acct_..."}
          />
          {settings?.stripe_account && !stripeAccount && (
            <p className="text-xs text-ink/60">Stored: {settings.stripe_account}</p>
          )}
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Publishable key</label>
          <input
            className="w-full rounded-md border border-fog px-3 py-2 text-sm"
            value={publishableKey}
            onChange={(event) => setPublishableKey(event.target.value)}
            placeholder={settings?.has_publishable_key ? "pk_... (stored)" : "pk_..."}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Secret key</label>
          <input
            className="w-full rounded-md border border-fog px-3 py-2 text-sm"
            value={secretKey}
            onChange={(event) => setSecretKey(event.target.value)}
            placeholder={settings?.has_secret_key ? "sk_... (stored)" : "sk_..."}
          />
        </div>
        {settingsStatus && <p className="text-sm text-ink/70">{settingsStatus}</p>}
        <Button type="button" onClick={saveSettings} disabled={savingSettings}>
          {savingSettings ? "Saving..." : "Save Stripe settings"}
        </Button>
      </Card>

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">Revenue sync</h2>
        <p className="text-sm text-ink/70">Pull balance transactions, charges, and refunds for online retail revenue reporting.</p>
        {status && <p className="text-sm text-ink/70">{status}</p>}
        <Button type="button" onClick={syncRevenue} disabled={loading}>
          {loading ? "Syncing..." : "Sync revenue"}
        </Button>
      </Card>

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">Balance history + payouts</h2>
        <p className="text-sm text-ink/70">Fetch balance activity and payout transfers for accounting and reconciliation.</p>
        <div className="grid gap-3 md:grid-cols-2">
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Start date</label>
            <input
              className="w-full rounded-md border border-fog px-3 py-2 text-sm"
              type="date"
              value={startDate}
              onChange={(event) => setStartDate(event.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">End date</label>
            <input
              className="w-full rounded-md border border-fog px-3 py-2 text-sm"
              type="date"
              value={endDate}
              onChange={(event) => setEndDate(event.target.value)}
            />
          </div>
        </div>
        {balanceStatus && <p className="text-sm text-ink/70">{balanceStatus}</p>}
        <Button type="button" onClick={fetchBalancePayouts} disabled={fetchingBalance}>
          {fetchingBalance ? "Fetching..." : "Fetch balance + payouts"}
        </Button>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-fog px-4 py-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-ink/60">Balance history</h3>
          <Button type="button" variant="ghost" onClick={exportBalanceCsv} disabled={balanceHistory.length === 0}>
            Export CSV
          </Button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3 text-left">Transaction ID</th>
              <th className="px-4 py-3 text-right">Gross</th>
              <th className="px-4 py-3 text-right">Fee</th>
              <th className="px-4 py-3 text-right">Net</th>
              <th className="px-4 py-3 text-right">Currency</th>
              <th className="px-4 py-3 text-right">Status</th>
              <th className="px-4 py-3 text-right">Type</th>
              <th className="px-4 py-3 text-right">Timestamp</th>
              <th className="px-4 py-3 text-right">Source</th>
            </tr>
          </thead>
          <tbody>
            {balanceHistory.map((item) => (
              <tr key={item.transaction_id} className="border-t border-fog">
                <td className="px-4 py-3 font-semibold">{item.transaction_id}</td>
                <td className="px-4 py-3 text-right">{item.amount_gross.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">{item.fee.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">{item.amount_net.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">{item.currency}</td>
                <td className="px-4 py-3 text-right">{item.status}</td>
                <td className="px-4 py-3 text-right">{item.type}</td>
                <td className="px-4 py-3 text-right">{new Date(item.date).toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{item.source_id || "-"}</td>
              </tr>
            ))}
            {balanceHistory.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-ink/60" colSpan={9}>
                  No balance history loaded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-fog px-4 py-3">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-ink/60">Payouts</h3>
          <Button type="button" variant="ghost" onClick={exportPayoutsCsv} disabled={payouts.length === 0}>
            Export CSV
          </Button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3 text-left">Payout ID</th>
              <th className="px-4 py-3 text-right">Amount</th>
              <th className="px-4 py-3 text-right">Currency</th>
              <th className="px-4 py-3 text-right">Status</th>
              <th className="px-4 py-3 text-right">Arrival date</th>
              <th className="px-4 py-3 text-right">Created</th>
              <th className="px-4 py-3 text-right">Method</th>
              <th className="px-4 py-3 text-right">Type</th>
            </tr>
          </thead>
          <tbody>
            {payouts.map((item) => (
              <tr key={item.payout_id} className="border-t border-fog">
                <td className="px-4 py-3 font-semibold">{item.payout_id}</td>
                <td className="px-4 py-3 text-right">{item.amount.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">{item.currency}</td>
                <td className="px-4 py-3 text-right">{item.status}</td>
                <td className="px-4 py-3 text-right">{item.arrival_date ? new Date(item.arrival_date).toLocaleDateString() : "-"}</td>
                <td className="px-4 py-3 text-right">{new Date(item.created_at).toLocaleString()}</td>
                <td className="px-4 py-3 text-right">{item.method || "-"}</td>
                <td className="px-4 py-3 text-right">{item.payout_type || "-"}</td>
              </tr>
            ))}
            {payouts.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-ink/60" colSpan={8}>
                  No payouts loaded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
