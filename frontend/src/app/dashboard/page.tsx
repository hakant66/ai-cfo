"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { MetricCard } from "@/components/metric-card";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuthedSWR } from "@/hooks/useApi";
import { useCompanyName } from "@/hooks/useCompany";

function formatCurrency(value: number | null, currency: string | null) {
  if (value === null || value === undefined) return "Missing";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: currency || "USD" }).format(value);
}

function formatLastRefresh(value: string | null | undefined) {
  if (!value) return "Not available";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toISOString().replace("T", " ").slice(0, 19);
}

export default function DashboardPage() {
  const date = useMemo(() => new Date().toISOString().slice(0, 10), []);
  const { data, error } = useAuthedSWR<any>(`/metrics/morning_brief?date=${date}`);
  const companyName = useCompanyName();
  const [showChatbot, setShowChatbot] = useState(true);
  const [chatbotMinimized, setChatbotMinimized] = useState(false);
  const [pillPosition, setPillPosition] = useState({ x: 24, y: 24 });
  const draggingRef = useRef(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });
  const pillRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const storedShow = window.localStorage.getItem("difyChatVisible");
    const storedMinimized = window.localStorage.getItem("difyChatMinimized");
    const storedPosition = window.localStorage.getItem("difyChatPillPosition");
    if (storedShow !== null) {
      setShowChatbot(storedShow === "true");
    }
    if (storedMinimized !== null) {
      setChatbotMinimized(storedMinimized === "true");
    }
    if (storedPosition) {
      try {
        const parsed = JSON.parse(storedPosition) as { x: number; y: number };
        if (typeof parsed.x === "number" && typeof parsed.y === "number") {
          setPillPosition(parsed);
        }
      } catch {
        // ignore malformed storage
      }
    }
  }, []);

  useEffect(() => {
    window.localStorage.setItem("difyChatVisible", String(showChatbot));
  }, [showChatbot]);

  useEffect(() => {
    window.localStorage.setItem("difyChatMinimized", String(chatbotMinimized));
  }, [chatbotMinimized]);

  useEffect(() => {
    window.localStorage.setItem("difyChatPillPosition", JSON.stringify(pillPosition));
  }, [pillPosition]);

  useEffect(() => {
    const handleMove = (event: globalThis.MouseEvent) => {
      if (!draggingRef.current) return;
      const nextX = window.innerWidth - event.clientX - dragOffsetRef.current.x;
      const nextY = window.innerHeight - event.clientY - dragOffsetRef.current.y;
      setPillPosition({
        x: Math.max(12, Math.min(nextX, window.innerWidth - 120)),
        y: Math.max(12, Math.min(nextY, window.innerHeight - 60))
      });
    };
    const handleUp = () => {
      draggingRef.current = false;
    };
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, []);

  const startDrag = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!pillRef.current) return;
    draggingRef.current = true;
    const rect = pillRef.current.getBoundingClientRect();
    dragOffsetRef.current = {
      x: rect.right - event.clientX,
      y: rect.bottom - event.clientY
    };
  };

  if (error) {
    return <p className="text-crimson">Failed to load morning brief. Confirm login and data imports.</p>;
  }

  if (!data) {
    return <p className="text-ink/70">Loading morning brief...</p>;
  }

  const cash = data.cash_position;
  const cashBreakdown = data.cash_position_breakdown;
  const netSales = data.yesterday_performance.net_sales;
  const cogs = data.yesterday_performance.cogs;
  const refunds = data.yesterday_performance.refunds;
  const discounts = data.yesterday_performance.discounts;
  const adSpend = data.yesterday_performance.ad_spend;
  const otherExpenses = data.yesterday_performance.other_expenses;
  const grossMargin = data.yesterday_performance.gross_margin;
  const contribution = data.yesterday_performance.contribution_margin;
  const expected7d = data.expected_cash["7d"];
  const expected14d = data.expected_cash["14d"];
  const expected30d = data.expected_cash["30d"];
  const payables7d = data.payables["7d"];

  return (
    <>
      <div className="grid gap-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-ink/60">
            {companyName ? `Morning CFO brief - ${companyName}` : "Morning CFO brief"}
          </p>
          <h1 className="text-3xl font-semibold">Daily financial position</h1>
          <p className="text-sm text-ink/60">Last refreshed: {formatLastRefresh(cash.last_refresh)}</p>
        </div>
        <Badge>{data.confidence} confidence</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="Total cash position" value={formatCurrency(cash.value, cash.currency)} subtitle={`Sources: ${cash.sources.join(", ")}`} />
        {cashBreakdown && (
          <>
            <MetricCard
              title="Cash position Bank"
              value={formatCurrency(cashBreakdown.bank.value, cashBreakdown.bank.currency)}
              subtitle={`Sources: ${cashBreakdown.bank.sources.join(", ")}`}
            />
            <MetricCard
              title="Cash position Wise"
              value={formatCurrency(cashBreakdown.wise.value, cashBreakdown.wise.currency)}
              subtitle={`Sources: ${cashBreakdown.wise.sources.join(", ")}`}
            />
          </>
        )}
        <MetricCard title="Expected cash (7d)" value={formatCurrency(expected7d.value, expected7d.currency)} subtitle="Forecast expected" />
        <MetricCard title="Expected cash (14d)" value={formatCurrency(expected14d.value, expected14d.currency)} subtitle="Forecast expected" />
        <MetricCard title="Expected cash (30d)" value={formatCurrency(expected30d.value, expected30d.currency)} subtitle="Forecast expected" />
        <MetricCard title="Payables due (7d)" value={formatCurrency(payables7d.value, payables7d.currency)} subtitle="Open bills" />
        <MetricCard title="Net sales (yesterday)" value={formatCurrency(netSales.value, netSales.currency)} subtitle={`Window: ${netSales.time_window}`} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="COGS (mock)" value={formatCurrency(cogs.value, cogs.currency)} subtitle={`Window: ${cogs.time_window}`} />
        <MetricCard title="Refunds" value={formatCurrency(refunds.value, refunds.currency)} subtitle={`Window: ${refunds.time_window}`} />
        <MetricCard title="Discounts" value={formatCurrency(discounts.value, discounts.currency)} subtitle={`Window: ${discounts.time_window}`} />
        <MetricCard title="Ad spend (mock)" value={formatCurrency(adSpend.value, adSpend.currency)} subtitle={`Window: ${adSpend.time_window}`} />
        <MetricCard title="Other expenses (mock)" value={formatCurrency(otherExpenses.value, otherExpenses.currency)} subtitle={`Window: ${otherExpenses.time_window}`} />
        <MetricCard title="Gross margin" value={formatCurrency(grossMargin.value, grossMargin.currency)} subtitle={`Window: ${grossMargin.time_window}`} />
        <MetricCard title="Contribution margin" value={formatCurrency(contribution.value, contribution.currency)} subtitle={`Window: ${contribution.time_window}`} />
      </div>

      <Card className="grid gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Alerts</h2>
          <span className="text-xs text-ink/60">{data.alerts.length} active</span>
        </div>
        <div className="grid gap-3">
          {data.alerts.length === 0 && <p className="text-sm text-ink/70">No alerts today.</p>}
          {data.alerts.map((alert: any) => (
            <div key={alert.id} className="flex items-center justify-between rounded-lg border border-fog bg-white px-4 py-3">
              <div>
                <p className="text-sm font-semibold">{alert.type}</p>
                <p className="text-xs text-ink/60">{alert.message}</p>
              </div>
              <Badge tone={alert.severity === "High" ? "danger" : alert.severity === "Medium" ? "warn" : "neutral"}>
                {alert.severity}
              </Badge>
            </div>
          ))}
        </div>
      </Card>
      </div>
      {showChatbot ? (
        <>
          {chatbotMinimized ? (
            <div
              ref={pillRef}
              onMouseDown={startDrag}
              className="fixed z-50 hidden cursor-grab items-center gap-2 rounded-full border border-fog bg-white px-3 py-2 shadow-xl lg:flex"
              style={{ right: pillPosition.x, bottom: pillPosition.y }}
            >
              <button
                type="button"
                onClick={() => setChatbotMinimized(false)}
                className="rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white"
              >
                Open Dify
              </button>
              <button
                type="button"
                onClick={() => setShowChatbot(false)}
                className="rounded-full border border-fog bg-white px-2 py-2 text-xs font-semibold text-ink"
              >
                Close
              </button>
            </div>
          ) : (
            <div className="fixed bottom-6 right-6 z-50 hidden overflow-hidden rounded-2xl border border-fog bg-white shadow-xl lg:block">
              <button
                type="button"
                onClick={() => setShowChatbot(false)}
                className="absolute right-3 top-3 rounded-full border border-fog bg-white px-2 py-1 text-xs font-semibold text-ink shadow-sm"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => setChatbotMinimized(true)}
                className="absolute right-16 top-3 rounded-full border border-fog bg-white px-2 py-1 text-xs font-semibold text-ink shadow-sm"
              >
                Minimize
              </button>
              <iframe
                title="Dify Chatbot"
                src={`${(process.env.NEXT_PUBLIC_DIFY_BASE || "http://localhost").replace(/\\/+$/, "")}/chatbot/OFVzpQeBmvdFUA7E`}
                className="h-[520px] w-[360px]"
              />
            </div>
          )}
        </>
      ) : (
        <button
          type="button"
          onClick={() => {
            setShowChatbot(true);
            setChatbotMinimized(false);
          }}
          className="fixed bottom-6 right-6 z-50 hidden rounded-full bg-ink px-4 py-2 text-xs font-semibold text-white shadow-xl lg:block"
        >
          Open Chatbot
        </button>
      )}
    </>
  );
}
