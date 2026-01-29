"use client";

import { useAuthedSWR } from "@/hooks/useApi";
import { Badge } from "@/components/ui/badge";
import { useCompanyName } from "@/hooks/useCompany";

export default function PayablesPage() {
  const { data, error } = useAuthedSWR<any[]>("/payables");
  const companyName = useCompanyName();

  if (error) {
    return <p className="text-crimson">Failed to load payables.</p>;
  }
  if (!data) {
    return <p className="text-ink/70">Loading payables...</p>;
  }

  return (
    <div className="grid gap-6">
      <div>
        <p className="text-xs uppercase tracking-[0.3em] text-ink/60">
          {companyName ? `Payables - ${companyName}` : "Payables"}
        </p>
        <h1 className="text-3xl font-semibold">Bills and payment timing</h1>
      </div>

      <div className="overflow-x-auto rounded-xl border border-fog bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-fog/40 text-left">
            <tr>
              <th className="p-3">Vendor</th>
              <th className="p-3">Amount</th>
              <th className="p-3">Due date</th>
              <th className="p-3">Criticality</th>
              <th className="p-3">Recommended payment</th>
            </tr>
          </thead>
          <tbody>
            {data.map((bill) => (
              <tr key={bill.id} className="border-t border-fog">
                <td className="p-3 font-semibold">{bill.vendor}</td>
                <td className="p-3">${bill.amount.toFixed(2)}</td>
                <td className="p-3">{bill.due_date}</td>
                <td className="p-3">
                  <Badge tone={bill.criticality === "critical" ? "danger" : "neutral"}>{bill.criticality}</Badge>
                </td>
                <td className="p-3">{bill.recommended_payment_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
