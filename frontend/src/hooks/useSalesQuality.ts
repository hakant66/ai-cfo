"use client";

import useSWR from "swr";
import { salesQualitySchema, SalesQualityResponse } from "@/lib/sales-quality";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";

const API_BASE = resolveApiBase();

async function fetchSalesQuality(path: string, token: string | null) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    cache: "no-store"
  });
  const requestId = res.headers.get("x-request-id");
  if (!res.ok) {
    const text = await res.text();
    const error = new Error(text || "Request failed");
    (error as Error & { requestId?: string }).requestId = requestId || undefined;
    throw error;
  }
  const json = await res.json();
  return salesQualitySchema.parse(json);
}

export function useSalesQuality(path: string | null) {
  const token = getToken();
  return useSWR<SalesQualityResponse, Error, [string, string | null] | null>(
    path ? [path, token] : null,
    ([url, tokenValue]) => fetchSalesQuality(url, tokenValue ?? null)
  );
}
