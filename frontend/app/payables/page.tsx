const payables = [
  { vendor: "Packaging Co", due: "2024-10-10", amount: "$2,400", priority: "Critical", recommended: "Pay today" },
  { vendor: "Logistics Partner", due: "2024-10-12", amount: "$5,400", priority: "Deferrable", recommended: "Pay in 3 days" },
];

export default function PayablesPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold">Payables Scheduler</h1>
      <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-100 text-slate-600">
            <tr>
              <th className="px-4 py-3">Vendor</th>
              <th className="px-4 py-3">Due Date</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Recommended Payment</th>
            </tr>
          </thead>
          <tbody>
            {payables.map((bill) => (
              <tr key={bill.vendor} className="border-t">
                <td className="px-4 py-3 font-medium">{bill.vendor}</td>
                <td className="px-4 py-3">{bill.due}</td>
                <td className="px-4 py-3">{bill.amount}</td>
                <td className="px-4 py-3">{bill.priority}</td>
                <td className="px-4 py-3">{bill.recommended}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
