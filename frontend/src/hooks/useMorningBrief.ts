"use client";

import { useAuthedSWR } from "@/hooks/useApi";
import type { MorningBriefData } from "@/types/morning-brief";

export function useMorningBrief(date: string) {
  return useAuthedSWR<MorningBriefData>(`/metrics/morning_brief?date=${date}`);
}
