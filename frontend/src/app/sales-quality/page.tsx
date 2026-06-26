"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { MetricCard } from "@/components/metric-card";
import { useSalesQuality } from "@/hooks/useSalesQuality";
import { SalesQualityResponse } from "@/lib/sales-quality";
import { useCompanyName } from "@/hooks/useCompany";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";

type Metric = SalesQualityResponse["kpis"]["net_sales"];

type TrueNetMarginItem = {
  gross_amount: number;
  net_amount: number;
  stripe_fee: number;
  margin_pct: number;
  currency: string;
  date: string;
};

type TrueNetMarginResponse = {
  items: TrueNetMarginItem[];
  count: number;
};

const API_BASE = resolveApiBase();

function formatCurrency(value: number | null, currency?: string | null) {
  if (value === null || value === undefined) return "Not available";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency || "USD", maximumFractionDigits: 2 }).format(value);
}

function formatLastRefresh(value: string | null | undefined) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").slice(0, 19);
}

function formatNumber(value: number | null) {
  if (value === null || value === undefined) return "Not available";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}

function formatPercent(value: number | null) {
  if (value === null || value === undefined) return "Not available";
  return `${formatNumber(value)}%`;
}

function metricLabel(metric: Metric, formatter: (value: number | null, currency?: string | null) => string, fallback = "Not available") {
  if (metric.value === null || metric.value === undefined) return fallback;
  return formatter(metric.value, metric.currency);
}

function metricNote(metric: Metric) {
  if (!metric.missing_data?.length) return null;
  return `Missing: ${metric.missing_data.join(", ")}`;
}

function rangeLabel(metric: Metric) {
  return `${metric.window.start} to ${metric.window.end} (${metric.window.timezone})`;
}

function toneForConfidence(confidence: string) {
  if (confidence === "High") return "neutral";
  if (confidence === "Medium") return "warn";
  return "danger";
}

function isoDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function skeletonRow(count: number) {
  return Array.from({ length: count }).map((_, idx) => (
    <div key={idx} className="h-24 animate-pulse rounded-lg border border-fog bg-white/60" />
  ));
}

export default function SalesQualityPage() {
  const defaultRange = useMemo(() => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    return { start: isoDate(yesterday), end: isoDate(yesterday) };
  }, []);

  const [range, setRange] = useState(defaultRange);
  const [skuSort, setSkuSort] = useState<"desc" | "asc">("desc");
  const isInvalidRange = range.start > range.end;
  const queryPath = isInvalidRange ? null : `/metrics/sales_quality?start=${range.start}&end=${range.end}`;
  const { data, error } = useSalesQuality(queryPath);
  const companyName = useCompanyName();
  const [trueNetData, setTrueNetData] = useState<TrueNetMarginResponse | null>(null);
  const [trueNetLoading, setTrueNetLoading] = useState(false);
  const [trueNetStatus, setTrueNetStatus] = useState<string | null>(null);

  const trueNetSummary = useMemo(() => {
    if (!trueNetData?.items?.length) return null;
    const summary = trueNetData.items.reduce(
      (acc, item) => ({
        gross: acc.gross + item.gross_amount,
        net: acc.net + item.net_amount,
        fee: acc.fee + item.stripe_fee,
        currency: acc.currency || item.currency,
        marginSum: acc.marginSum + item.margin_pct,
      }),
      { gross: 0, net: 0, fee: 0, currency: "", marginSum: 0 }
    );
    const absGross = Math.abs(summary.gross);
    const blendedMarginPct = absGross > 1e-9 ? (summary.net / summary.gross) * 100 : null;
    const avgMargin = trueNetData.items.length ? summary.marginSum / trueNetData.items.length : 0;
    return { ...summary, blendedMarginPct, avgMargin, count: trueNetData.count };
  }, [trueNetData]);

  const loadTrueNetMargin = async () => {
    if (isInvalidRange) return;
    setTrueNetStatus(null);
    setTrueNetLoading(true);
    try {
      const token = getToken();
      const res = await fetch(`${API_BASE}/connectors/stripe/metrics/true-net-margin?start_date=${range.start}&end_date=${range.end}&limit=500`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to load True Net Margin.");
      }
      const payload = await res.json();
      setTrueNetData(payload);
      setTrueNetStatus(`Loaded ${payload.count} Stripe transactions.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load True Net Margin.";
      setTrueNetStatus(message);
    } finally {
      setTrueNetLoading(false);
    }
  };

  useEffect(() => {
    loadTrueNetMargin();
  }, [range.start, range.end]);

  const preset = useMemo(() => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);
    const last7 = new Date(today);
    last7.setDate(today.getDate() - 7);
    const last30 = new Date(today);
    last30.setDate(today.getDate() - 30);
    const last90 = new Date(today);
    last90.setDate(today.getDate() - 90);
    const last365 = new Date(today);
    last365.setDate(today.getDate() - 365);
    if (range.start === isoDate(yesterday) && range.end === isoDate(yesterday)) return "Yesterday";
    if (range.start === isoDate(last7) && range.end === isoDate(yesterday)) return "Last 7 days";
    if (range.start === isoDate(last30) && range.end === isoDate(yesterday)) return "Last 30 days";
    if (range.start === isoDate(last90) && range.end === isoDate(yesterday)) return "Last 90 days";
    if (range.start === isoDate(last365) && range.end === isoDate(yesterday)) return "Last 365 days";
    return "Custom";
  }, [range]);

  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-ink/60">
            {companyName ? `Sales quality - ${companyName}` : "Sales quality"}
          </p>
          <h1 className="text-3xl font-semibold">Channel and customer mix</h1>
          <p className="text-sm text-ink/60">Track repeat demand, mix concentration, and exposure.</p>
        </div>
        <Badge tone={data ? toneForConfidence(data.metadata.confidence) : "neutral"}>
          {data ? `${data.metadata.confidence} confidence` : "Loading confidence"}
        </Badge>
      </div>

      <Card className="grid gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant={preset === "Yesterday" ? "primary" : "ghost"}
            onClick={() => setRange({ start: defaultRange.start, end: defaultRange.end })}
          >
            Yesterday
          </Button>
          <Button
            variant={preset === "Last 7 days" ? "primary" : "ghost"}
            onClick={() => {
              const today = new Date();
              const start = new Date(today);
              start.setDate(today.getDate() - 7);
              const end = new Date(today);
              end.setDate(today.getDate() - 1);
              setRange({ start: isoDate(start), end: isoDate(end) });
            }}
          >
            Last 7 days
          </Button>
          <Button
            variant={preset === "Last 30 days" ? "primary" : "ghost"}
            onClick={() => {
              const today = new Date();
              const start = new Date(today);
              start.setDate(today.getDate() - 30);
              const end = new Date(today);
              end.setDate(today.getDate() - 1);
              setRange({ start: isoDate(start), end: isoDate(end) });
            }}
          >
            Last 30 days
          </Button>
          <Button
            variant={preset === "Last 90 days" ? "primary" : "ghost"}
            onClick={() => {
              const today = new Date();
              const start = new Date(today);
              start.setDate(today.getDate() - 90);
              const end = new Date(today);
              end.setDate(today.getDate() - 1);
              setRange({ start: isoDate(start), end: isoDate(end) });
            }}
          >
            Last 90 days
          </Button>
          <Button
            variant={preset === "Last 365 days" ? "primary" : "ghost"}
            onClick={() => {
              const today = new Date();
              const start = new Date(today);
              start.setDate(today.getDate() - 365);
              const end = new Date(today);
              end.setDate(today.getDate() - 1);
              setRange({ start: isoDate(start), end: isoDate(end) });
            }}
          >
            Last 365 days
          </Button>
        </div>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="text-xs font-semibold text-ink/60">Start date</label>
            <Input type="date" value={range.start} onChange={(event) => setRange({ ...range, start: event.target.value })} />
          </div>
          <div>
            <label className="text-xs font-semibold text-ink/60">End date</label>
            <Input type="date" value={range.end} onChange={(event) => setRange({ ...range, end: event.target.value })} />
          </div>
          {isInvalidRange && <span className="text-sm text-crimson">Start date must be before end date.</span>}
        </div>
      </Card>

      <section
        aria-labelledby="true-net-heading"
        className="min-w-0 overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-[0_12px_40px_-24px_rgba(15,23,42,0.35)] ring-1 ring-black/[0.04]"
      >
        <div className="border-b border-fog bg-gradient-to-r from-slate-50 to-violet-50/60 px-6 py-5 md:px-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="grid min-w-0 max-w-2xl gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md border border-violet-200 bg-white px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider text-violet-800">
                  Stripe
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-ink/45">True net margin</span>
                {trueNetData != null && (
                  <span className="text-xs text-ink/50">
                    {trueNetData.count} stored {trueNetData.count === 1 ? "transaction" : "transactions"}
                  </span>
                )}
              </div>
              <h2 id="true-net-heading" className="text-xl font-semibold tracking-tight text-ink md:text-2xl">
                True Net Margin (Stripe)
              </h2>
              <p className="text-sm leading-relaxed text-ink/65">
                Read from <span className="font-medium text-ink/80">Postgres</span> (
                <code className="rounded bg-fog px-1 py-0.5 text-xs">stripe_metrics</code>) for the selected range. Includes synthetic webhook rows in dev.
              </p>
              <p className="text-xs text-ink/50">
                Date range: <span className="font-medium text-ink/70">{range.start}</span> →{" "}
                <span className="font-medium text-ink/70">{range.end}</span>
                {isInvalidRange ? <span className="text-crimson"> · Invalid range</span> : null}
              </p>
            </div>
            <div className="flex shrink-0 flex-col items-stretch gap-2 sm:flex-row sm:items-center">
              <Button type="button" onClick={loadTrueNetMargin} disabled={trueNetLoading || isInvalidRange}>
                {trueNetLoading ? "Loading…" : "Refresh from database"}
              </Button>
            </div>
          </div>
        </div>

        <div className="grid gap-6 px-6 py-6 md:px-8 md:py-8">
          {trueNetStatus && (
            <p className={`text-sm ${trueNetStatus.startsWith("Loaded") ? "text-emerald-800" : "text-ink/80"}`}>{trueNetStatus}</p>
          )}
          {trueNetLoading && <p className="text-sm text-ink/50">Loading stored metrics…</p>}
          {!trueNetSummary && !trueNetLoading && !isInvalidRange && (
            <p className="text-sm text-ink/55">
              No rows in this window yet. Adjust dates or run a Stripe sync / mock webhook, then refresh.
            </p>
          )}

          {trueNetSummary && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-fog bg-slate-50/50 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-ink/50">Gross (window)</p>
                <p className="mt-1 text-xl font-semibold tabular-nums text-ink md:text-2xl">
                  {formatCurrency(trueNetSummary.gross, trueNetSummary.currency)}
                </p>
                <p className="mt-2 text-xs text-ink/55">Sum of gross_amount</p>
              </div>
              <div className="rounded-xl border border-fog bg-slate-50/50 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-ink/50">Net (after fees)</p>
                <p className="mt-1 text-xl font-semibold tabular-nums text-ink md:text-2xl">
                  {formatCurrency(trueNetSummary.net, trueNetSummary.currency)}
                </p>
                <p className="mt-2 text-xs text-ink/55">After Stripe fees</p>
              </div>
              <div className="rounded-xl border border-fog bg-slate-50/50 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-ink/50">Stripe fees (total)</p>
                <p className="mt-1 text-xl font-semibold tabular-nums text-ink md:text-2xl">
                  {formatCurrency(trueNetSummary.fee, trueNetSummary.currency)}
                </p>
                <p className="mt-2 text-xs text-ink/55">Sum of stripe_fee</p>
              </div>
              <div className="rounded-xl border border-fog bg-violet-50/40 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-ink/50">Blended margin</p>
                <p className="mt-1 text-xl font-semibold tabular-nums text-violet-950 md:text-2xl">
                  {trueNetSummary.blendedMarginPct === null || trueNetSummary.blendedMarginPct === undefined
                    ? "—"
                    : formatPercent(trueNetSummary.blendedMarginPct)}
                </p>
                <p className="mt-2 text-xs text-ink/55">Net ÷ gross (window)</p>
                <p className="mt-1 text-[11px] text-ink/45">Avg. row: {formatPercent(trueNetSummary.avgMargin)}</p>
              </div>
            </div>
          )}

          <div className="max-h-[min(28rem,55vh)] overflow-auto rounded-xl border border-fog">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-fog bg-fog/80 px-4 py-2.5">
              <span className="text-xs font-semibold uppercase tracking-wide text-ink/55">Transaction detail</span>
              <span className="text-xs text-ink/45">Stripe API order</span>
            </div>
            <table className="w-full min-w-[520px] text-sm">
              <thead className="sticky top-0 z-[1] bg-white text-xs uppercase tracking-wide text-ink/55 shadow-sm">
                <tr className="border-b border-fog">
                  <th className="px-4 py-3 text-left font-semibold">Date</th>
                  <th className="px-4 py-3 text-right font-semibold">Gross</th>
                  <th className="px-4 py-3 text-right font-semibold">Fee</th>
                  <th className="px-4 py-3 text-right font-semibold">Net</th>
                  <th className="px-4 py-3 text-right font-semibold">Margin %</th>
                  <th className="px-4 py-3 text-right font-semibold">CCY</th>
                </tr>
              </thead>
              <tbody className="bg-white">
                {trueNetData?.items?.map((item, idx) => (
                  <tr key={`${item.date}-${idx}`} className="border-t border-fog/80 odd:bg-slate-50/40">
                    <td className="whitespace-nowrap px-4 py-2.5 text-ink/80">{new Date(item.date).toLocaleDateString()}</td>
                    <td className="px-4 py-2.5 text-right font-medium tabular-nums text-ink">{item.gross_amount.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink/75">{item.stripe_fee.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-right font-medium tabular-nums text-ink">{item.net_amount.toFixed(2)}</td>
                    <td className="px-4 py-2.5 text-right tabular-nums text-ink/80">{formatPercent(item.margin_pct)}</td>
                    <td className="px-4 py-2.5 text-right text-xs font-semibold uppercase text-ink/60">{item.currency}</td>
                  </tr>
                ))}
                {!trueNetData?.items?.length && (
                  <tr>
                    <td className="px-4 py-10 text-center text-sm text-ink/50" colSpan={6}>
                      No metrics in range. Widen dates or refresh after ingesting Stripe data.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {data && (
        <Card className="grid gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">New vs returning</h2>
            <Badge tone={toneForConfidence(data.new_vs_returning.repeat_purchase_rate.confidence)}>
              {data.new_vs_returning.repeat_purchase_rate.confidence}
            </Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <MetricCard
              title="New customer revenue"
              value={metricLabel(data.new_vs_returning.new_customer_revenue, formatCurrency)}
              subtitle={metricNote(data.new_vs_returning.new_customer_revenue) || rangeLabel(data.new_vs_returning.new_customer_revenue)}
            />
            <MetricCard
              title="Returning customer revenue"
              value={metricLabel(data.new_vs_returning.returning_customer_revenue, formatCurrency)}
              subtitle={metricNote(data.new_vs_returning.returning_customer_revenue) || rangeLabel(data.new_vs_returning.returning_customer_revenue)}
            />
            <MetricCard
              title="New customer orders"
              value={metricLabel(data.new_vs_returning.new_customer_orders, (value) => formatNumber(value))}
              subtitle={metricNote(data.new_vs_returning.new_customer_orders) || rangeLabel(data.new_vs_returning.new_customer_orders)}
            />
            <MetricCard
              title="Returning customer orders"
              value={metricLabel(data.new_vs_returning.returning_customer_orders, (value) => formatNumber(value))}
              subtitle={metricNote(data.new_vs_returning.returning_customer_orders) || rangeLabel(data.new_vs_returning.returning_customer_orders)}
            />
          </div>
          <div className="grid gap-2 text-sm text-ink/70">
            <span>New revenue share: {formatPercent(data.new_vs_returning.new_customer_revenue_pct.value)}</span>
            <span>Returning revenue share: {formatPercent(data.new_vs_returning.returning_customer_revenue_pct.value)}</span>
          </div>
        </Card>
      )}

      {error && (
        <Card className="grid gap-2 border-crimson/40 bg-crimson/5 text-crimson">
          <h2 className="text-lg font-semibold">Sales quality failed to load</h2>
          <p className="text-sm">{error.message}</p>
          {(error as Error & { requestId?: string }).requestId && (
            <p className="text-xs text-crimson/80">Request id: {(error as Error & { requestId?: string }).requestId}</p>
          )}
        </Card>
      )}

      {!data && !error && <div className="grid gap-4 md:grid-cols-3">{skeletonRow(6)}</div>}

      {data && (
        <>
          {(() => {
            const sortedSkus = [...data.top_skus].sort((a, b) => {
              const left = a.net_sales.value || 0;
              const right = b.net_sales.value || 0;
              return skuSort === "desc" ? right - left : left - right;
            });
            return (
              <>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard title="Orders" value={metricLabel(data.kpis.orders_count, (value) => formatNumber(value))} subtitle={rangeLabel(data.kpis.orders_count)} />
            <MetricCard title="Net sales" value={metricLabel(data.kpis.net_sales, formatCurrency)} subtitle={rangeLabel(data.kpis.net_sales)} />
            <MetricCard title="AOV" value={metricLabel(data.kpis.aov, formatCurrency)} subtitle={metricNote(data.kpis.aov) || rangeLabel(data.kpis.aov)} />
            <MetricCard title="Units per order" value={metricLabel(data.kpis.upo, (value) => formatNumber(value))} subtitle={metricNote(data.kpis.upo) || rangeLabel(data.kpis.upo)} />
            <MetricCard title="Repeat purchase rate" value={metricLabel(data.kpis.repeat_purchase_rate, (value) => formatPercent(value))} subtitle={metricNote(data.kpis.repeat_purchase_rate) || rangeLabel(data.kpis.repeat_purchase_rate)} />
            <MetricCard title="Top 10 SKU share" value={metricLabel(data.kpis.top10_sku_share, (value) => formatPercent(value))} subtitle={metricNote(data.kpis.top10_sku_share) || rangeLabel(data.kpis.top10_sku_share)} />
          </div>

          <Card className="grid gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Channel mix</h2>
              <Badge tone={toneForConfidence(data.channel_mix[0]?.net_sales.confidence || "Low")}>
                {data.channel_mix[0]?.net_sales.confidence || "Low"}
              </Badge>
            </div>
              <div className="grid gap-3">
                {data.channel_mix.length === 0 && <p className="text-sm text-ink/60">Not available.</p>}
                {data.channel_mix.map((item) => (
                  <div key={item.channel} className="grid gap-2 rounded-lg border border-fog bg-white px-4 py-3">
                    <div className="flex items-center justify-between text-sm font-semibold">
                      <span>{item.channel}</span>
                      <span>{formatCurrency(item.net_sales.value, item.net_sales.currency)}</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-fog">
                      <div
                        className="h-2 rounded-full bg-ink/80"
                        style={{ width: `${Math.min(item.revenue_share_pct.value || 0, 100)}%` }}
                      />
                    </div>
                    <div className="text-xs text-ink/60">
                      {formatPercent(item.revenue_share_pct.value)} revenue, {formatPercent(item.orders_share_pct.value)} orders
                    </div>
                  </div>
                ))}
              </div>
              {data.channel_mix.length > 0 && (
                <div className="overflow-hidden rounded-lg border border-fog">
                  <table className="w-full text-sm">
                    <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
                      <tr>
                        <th className="px-3 py-2 text-left">Channel</th>
                        <th className="px-3 py-2 text-right">Orders</th>
                        <th className="px-3 py-2 text-right">Net sales</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.channel_mix.map((item) => (
                        <tr key={`${item.channel}-table`} className="border-t border-fog">
                          <td className="px-3 py-2 font-semibold">{item.channel}</td>
                          <td className="px-3 py-2 text-right">{formatNumber(item.orders.value)}</td>
                          <td className="px-3 py-2 text-right">{formatCurrency(item.net_sales.value, item.net_sales.currency)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="grid gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Top SKUs</h2>
                <Badge tone={toneForConfidence(data.kpis.top10_sku_share.confidence)}>{data.kpis.top10_sku_share.confidence}</Badge>
              </div>
              {data.top_skus.length === 0 ? (
                <p className="text-sm text-ink/60">Not available. {metricNote(data.kpis.top10_sku_share)}</p>
              ) : (
                <div className="overflow-hidden rounded-lg border border-fog">
                  <table className="w-full text-sm">
                    <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
                      <tr>
                        <th className="px-3 py-2 text-left">SKU</th>
                        <th className="px-3 py-2 text-left">Product</th>
                        <th className="px-3 py-2 text-right">
                          <button
                            className="font-semibold uppercase tracking-wide text-ink/60"
                            onClick={() => setSkuSort((current) => (current === "desc" ? "asc" : "desc"))}
                          >
                            Net sales {skuSort === "desc" ? "v" : "^"}
                          </button>
                        </th>
                        <th className="px-3 py-2 text-right">Units</th>
                        <th className="px-3 py-2 text-right">Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedSkus.map((sku) => (
                        <tr key={sku.sku} className="border-t border-fog">
                          <td className="px-3 py-2 font-semibold">{sku.sku}</td>
                          <td className="px-3 py-2 text-ink/70">{sku.product_name}</td>
                          <td className="px-3 py-2 text-right">{formatCurrency(sku.net_sales.value, sku.net_sales.currency)}</td>
                          <td className="px-3 py-2 text-right">{formatNumber(sku.units.value)}</td>
                          <td className="px-3 py-2 text-right">{formatPercent(sku.revenue_share_pct.value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card className="grid gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Categories</h2>
                <Badge tone={toneForConfidence(data.kpis.top10_sku_share.confidence)}>{data.kpis.top10_sku_share.confidence}</Badge>
              </div>
              {data.categories.length === 0 ? (
                <p className="text-sm text-ink/60">Not available. Missing product categories.</p>
              ) : (
                <div className="overflow-hidden rounded-lg border border-fog">
                  <table className="w-full text-sm">
                    <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
                      <tr>
                        <th className="px-3 py-2 text-left">Category</th>
                        <th className="px-3 py-2 text-right">Net sales</th>
                        <th className="px-3 py-2 text-right">Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.categories.map((category) => (
                        <tr key={category.category} className="border-t border-fog">
                          <td className="px-3 py-2 font-semibold">{category.category}</td>
                          <td className="px-3 py-2 text-right">{formatCurrency(category.net_sales.value, category.net_sales.currency)}</td>
                          <td className="px-3 py-2 text-right">{formatPercent(category.revenue_share_pct.value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="grid gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Geography mix</h2>
                <Badge tone={toneForConfidence(data.geo_mix.confidence)}>{data.geo_mix.confidence}</Badge>
              </div>
              {data.geo_mix.countries.length === 0 ? (
                <p className="text-sm text-ink/60">Not available. Missing shipping country data.</p>
              ) : (
                <div className="grid gap-3">
                  {data.geo_mix.countries.map((country) => (
                    <div key={country.country} className="rounded-lg border border-fog bg-white px-4 py-3">
                      <div className="flex items-center justify-between text-sm font-semibold">
                        <span>{country.country}</span>
                        <span>{formatCurrency(country.net_sales.value, country.net_sales.currency)}</span>
                      </div>
                      <div className="mt-2 h-2 w-full rounded-full bg-fog">
                        <div
                          className="h-2 rounded-full bg-ink/80"
                          style={{ width: `${Math.min(country.revenue_share_pct.value || 0, 100)}%` }}
                        />
                      </div>
                      <div className="mt-1 text-xs text-ink/60">{formatPercent(country.revenue_share_pct.value)} revenue share</div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="grid gap-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Currency mix</h2>
                <Badge tone={toneForConfidence(data.currency_mix.confidence)}>{data.currency_mix.confidence}</Badge>
              </div>
              {data.currency_mix.items.length === 0 ? (
                <p className="text-sm text-ink/60">Not available. Missing currency codes on orders.</p>
              ) : (
                <div className="grid gap-3">
                  {data.currency_mix.items.map((currency) => (
                    <div key={currency.currency} className="rounded-lg border border-fog bg-white px-4 py-3">
                      <div className="flex items-center justify-between text-sm font-semibold">
                        <span>{currency.currency}</span>
                        <span>{formatCurrency(currency.net_sales.value, currency.net_sales.currency)}</span>
                      </div>
                      <div className="mt-2 h-2 w-full rounded-full bg-fog">
                        <div
                          className="h-2 rounded-full bg-ink/80"
                          style={{ width: `${Math.min(currency.revenue_share_pct.value || 0, 100)}%` }}
                        />
                      </div>
                      <div className="mt-1 text-xs text-ink/60">{formatPercent(currency.revenue_share_pct.value)} revenue share</div>
                    </div>
                  ))}
                </div>
              )}
              {data.currency_mix.fx_exposure.enabled && (
                <div className="rounded-lg border border-fog bg-fog px-4 py-3 text-sm text-ink/70">
                  FX exposure: {data.currency_mix.fx_exposure.top_non_base_currency} at{" "}
                  {formatPercent(data.currency_mix.fx_exposure.share_pct)}
                </div>
              )}
            </Card>
          </div>

          <Card className="grid gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-ink/70">
              <span>Sources: {data.metadata.sources.join(", ") || "Not available"}</span>
              <span>Window: {data.metadata.window.start} to {data.metadata.window.end} ({data.metadata.window.timezone})</span>
              <span>Last refreshed: {formatLastRefresh(data.metadata.last_refresh)}</span>
              <Badge tone={toneForConfidence(data.metadata.confidence)}>{data.metadata.confidence}</Badge>
            </div>
          </Card>
              </>
            );
          })()}
        </>
      )}
    </div>
  );
}
