import { Suspense } from "react";
import SetupClient from "@/app/setup/setup-client";

export default function SetupPage() {
  return (
    <Suspense fallback={<p className="text-sm text-ink/70">Loading setup...</p>}>
      <SetupClient />
    </Suspense>
  );
}
