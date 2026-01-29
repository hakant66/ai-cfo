import { Card } from "@/components/ui/card";

export function MetricCard({ title, value, subtitle }: { title: string; value: string; subtitle: string }) {
  return (
    <Card className="flex h-full flex-col gap-2">
      <span className="text-xs uppercase tracking-[0.2em] text-ink/60">{title}</span>
      <span className="text-2xl font-semibold text-ink">{value}</span>
      <span className="text-xs text-ink/60">{subtitle}</span>
    </Card>
  );
}