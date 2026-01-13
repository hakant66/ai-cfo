export default function HomePage() {
  return (
    <section className="space-y-6">
      <h1 className="text-3xl font-semibold">Welcome to AI CFO</h1>
      <p className="text-slate-600">
        Launch the Morning CFO Brief or connect your data sources to start.
      </p>
      <div className="flex gap-4">
        <a className="rounded bg-slate-900 px-4 py-2 text-white" href="/login">
          Login
        </a>
        <a className="rounded border border-slate-300 px-4 py-2" href="/setup">
          Company Setup
        </a>
      </div>
    </section>
  );
}
