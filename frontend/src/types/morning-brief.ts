/** Mirrors backend morning brief payload used by the dashboard. */
export interface MorningBriefMetric {
  value: number | null;
  currency: string | null;
  time_window: string;
  sources: string[];
}

export interface MorningBriefCash extends MorningBriefMetric {
  last_refresh?: string | null;
}

export interface MorningBriefData {
  cash_position: MorningBriefCash;
  cash_position_breakdown?: {
    bank: MorningBriefMetric;
    wise: MorningBriefMetric;
  };
  expected_cash: Record<"7d" | "14d" | "30d", MorningBriefMetric>;
  yesterday_performance: {
    net_sales: MorningBriefMetric;
    cogs: MorningBriefMetric;
    refunds: MorningBriefMetric;
    discounts: MorningBriefMetric;
    ad_spend: MorningBriefMetric;
    other_expenses: MorningBriefMetric;
    gross_margin: MorningBriefMetric;
    contribution_margin: MorningBriefMetric;
  };
  payables: Record<string, MorningBriefMetric>;
  alerts: Array<{ id: number; type: string; severity: string; message: string }>;
  confidence: string;
}
