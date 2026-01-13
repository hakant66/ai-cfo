const uploadLinks = [
  { label: "Bank CSV", href: "/templates/bank.csv" },
  { label: "Payables CSV", href: "/templates/payables.csv" },
  { label: "Purchase Orders CSV", href: "/templates/purchase_orders.csv" },
];

export default function SetupPage() {
  return (
    <section className="space-y-8">
      <h1 className="text-2xl font-semibold">Company Setup Wizard</h1>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Connect Shopify</h2>
          <p className="text-sm text-slate-500">Enter your Admin API credentials or use demo mode.</p>
          <div className="mt-4 space-y-3">
            <input className="w-full rounded border px-3 py-2" placeholder="Shopify Admin API Key" />
            <input className="w-full rounded border px-3 py-2" placeholder="Shopify Admin API Secret" />
            <button className="rounded bg-slate-900 px-4 py-2 text-white">Test Connection</button>
          </div>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Upload Data</h2>
          <p className="text-sm text-slate-500">Load CSVs for bank, payables, and POs.</p>
          <div className="mt-4 space-y-3">
            {uploadLinks.map((link) => (
              <div key={link.label} className="flex items-center justify-between rounded border px-3 py-2">
                <span className="text-sm">{link.label}</span>
                <a className="text-sm text-blue-600" href={link.href}>
                  Download template
                </a>
              </div>
            ))}
            <input className="w-full rounded border px-3 py-2" type="file" />
          </div>
        </div>
      </div>
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Preferences</h2>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <input className="rounded border px-3 py-2" placeholder="Currency (USD)" />
          <input className="rounded border px-3 py-2" placeholder="Timezone (UTC)" />
          <input className="rounded border px-3 py-2" placeholder="Settlement Lag Days" />
          <input className="rounded border px-3 py-2" placeholder="Stockout Threshold (weeks)" />
        </div>
      </div>
    </section>
  );
}
