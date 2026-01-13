const inventoryRows = [
  { sku: "SKU-RED-42", onHand: 120, avgDaily: 8, weeks: 2.1, stockout: true, overstock: false },
  { sku: "SKU-BLUE-10", onHand: 480, avgDaily: 4, weeks: 17.1, stockout: false, overstock: true },
  { sku: "SKU-GREEN-07", onHand: 90, avgDaily: 6, weeks: 2.1, stockout: false, overstock: false },
];

export default function InventoryPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Inventory Health</h1>
      <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="px-4 py-3">SKU</th>
              <th className="px-4 py-3">On Hand</th>
              <th className="px-4 py-3">Avg Daily Sales</th>
              <th className="px-4 py-3">Weeks of Cover</th>
              <th className="px-4 py-3">Risk Flags</th>
            </tr>
          </thead>
          <tbody>
            {inventoryRows.map((row) => (
              <tr key={row.sku} className="border-t">
                <td className="px-4 py-3 font-medium">{row.sku}</td>
                <td className="px-4 py-3">{row.onHand}</td>
                <td className="px-4 py-3">{row.avgDaily}</td>
                <td className="px-4 py-3">{row.weeks}</td>
                <td className="px-4 py-3">
                  {row.stockout && <span className="mr-2 rounded bg-red-100 px-2 py-1 text-xs text-red-700">Stockout</span>}
                  {row.overstock && <span className="rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-700">Overstock</span>}
                  {!row.stockout && !row.overstock && <span className="text-xs text-slate-400">Healthy</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
