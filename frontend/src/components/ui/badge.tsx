import { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "danger" | "warn" }) {
  const toneClass =
    tone === "danger" ? "bg-crimson/10 text-crimson" : tone === "warn" ? "bg-amber/10 text-amber" : "bg-fog text-ink";
  return <span className={cn("rounded-full px-3 py-1 text-xs font-semibold", toneClass)}>{children}</span>;
}