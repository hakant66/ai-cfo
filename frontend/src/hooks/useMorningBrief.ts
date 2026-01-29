import useSWR from "swr";
import { apiGet } from "@/lib/api";

export function useMorningBrief(date: string) {
  return useSWR([`/metrics/morning_brief?date=${date}`], ([url]) => apiGet(url));
}