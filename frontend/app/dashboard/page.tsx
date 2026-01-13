import { MetricCard } from "@/components/metric-card";

const metrics = [
  { title: "Cash Position", value: "$42,000", subtitle: "As of today · Bank" },
  { title: "Net Sales (Yesterday)", value: "$18,450", subtitle: "Net of discounts & refunds" },
  { title: "Refunds", value: "$1,200", subtitle: "Last 24 hours" },
  { title: "Payables Due", value: "$7,800", subtitle: "Due this week" },
];

const alerts = [
  "Spend spike detected in paid media.",
  "Return rate exceeded 8% threshold.",
  "Supplier lead times slipped by 3 days.",
];

export default function DashboardPage() {
  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Morning CFO Brief</h1>
        <button className="rounded border px-4 py-2 text-sm">Refresh</button>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <MetricCard key={metric.title} {...metric} />
        ))}
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold">Inventory Risks</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            <li>SKU-RED-42 is below 1.5 weeks of cover.</li>
            <li>SKU-BLUE-10 has 16 weeks of cover (overstock).</li>
            <li>3 SKUs aged over 180 days.</li>
          </ul>
        </div>
        <div className="rounded-lg border bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold">Alerts</h2>
          <ul className="mt-3 space-y-2 text-sm text-slate-600">
            {alerts.map((alert) => (
              <li key={alert}>{alert}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="text-xs text-slate-400">Last refreshed: 09:15 AM · Confidence: Medium</div>
    </section>
  );
}
