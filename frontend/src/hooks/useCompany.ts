"use client";

import { z } from "zod";
import { useAuthedSWR } from "@/hooks/useApi";

const companySchema = z.object({
  id: z.number(),
  name: z.string()
});

export function useCompanyName() {
  const { data } = useAuthedSWR("/companies/me");
  const parsed = companySchema.safeParse(data);
  return parsed.success ? parsed.data.name : null;
}
