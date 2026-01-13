export default function LoginPage() {
  return (
    <section className="max-w-md space-y-6">
      <h1 className="text-2xl font-semibold">Login</h1>
      <form className="space-y-4 rounded-lg border bg-white p-6 shadow-sm">
        <div className="space-y-2">
          <label className="text-sm font-medium">Email</label>
          <input className="w-full rounded border px-3 py-2" type="email" placeholder="you@company.com" />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium">Password</label>
          <input className="w-full rounded border px-3 py-2" type="password" placeholder="••••••••" />
        </div>
        <button className="w-full rounded bg-slate-900 py-2 text-white" type="button">
          Sign in
        </button>
      </form>
    </section>
  );
}
