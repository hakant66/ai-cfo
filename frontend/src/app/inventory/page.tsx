"use client";

import { useAuthedSWR } from "@/hooks/useApi";
import { Badge } from "@/components/ui/badge";
import { useCompanyName } from "@/hooks/useCompany";

export default function InventoryPage() {
  const { data, error } = useAuthedSWR<any>("/metrics/inventory_health");
  const companyName = useCompanyName();

  if (error) {
    return <p className="text-crimson">Failed to load inventory health.</p>;
  }
  if (!data) {
    return <p className="text-ink/70">Loading inventory...</p>;
  }

  return (
    <div className="grid gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-ink/60">
          {companyName ? `Inventory health - ${companyName}` : "Inventory health"}
        </p>
        <h1 className="text-3xl font-semibold">Risk and coverage</h1>
        <p className="text-sm text-ink/60">Confidence: {data.confidence}</p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-fog bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-fog/40 text-left">
            <tr>
              <th className="p-3">SKU</th>
              <th className="p-3">On hand</th>
              <th className="p-3">Avg daily sales</th>
              <th className="p-3">Weeks of cover</th>
              <th className="p-3">Risk flags</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item: any) => (
              <tr key={item.sku} className="border-t border-fog">
                <td className="p-3 font-semibold">{item.sku}</td>
                <td className="p-3">{item.on_hand}</td>
                <td className="p-3">{item.avg_daily_units_sold.toFixed(2)}</td>
                <td className="p-3">{item.weeks_of_cover ?? "N/A"}</td>
                <td className="p-3 flex gap-2">
                  {item.stockout_risk && <Badge tone="danger">Stockout</Badge>}
                  {item.overstock_risk && <Badge tone="warn">Overstock</Badge>}
                  {!item.stockout_risk && !item.overstock_risk && <Badge>Stable</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
