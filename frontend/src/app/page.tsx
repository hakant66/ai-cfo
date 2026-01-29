import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="grid gap-6">
      <div className="grid gap-3">
        <p className="text-xs uppercase tracking-[0.3em] text-ink/60">CFO-grade decisioning</p>
        <h1 className="text-4xl font-semibold">Build daily financial clarity without the spreadsheet chaos.</h1>
        <p className="text-lg text-ink/70">
          Connect your commerce, banking, and payables to produce an executive morning brief with accountable numbers.
        </p>
      </div>
      <div className="flex gap-3">
        <Link href="/login">
          <Button>Sign in</Button>
        </Link>
        <Link href="/setup">
          <Button variant="ghost">Start setup</Button>
        </Link>
      </div>
    </div>
  );
}