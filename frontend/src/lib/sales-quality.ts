import { z } from "zod";

export const metricSchema = z.object({
  value: z.number().nullable(),
  currency: z.string().nullable().optional(),
  window: z.object({
    start: z.string(),
    end: z.string(),
    timezone: z.string()
  }),
  sources: z.array(z.string()),
  last_refresh: z.string(),
  confidence: z.enum(["High", "Medium", "Low"]),
  missing_data: z.array(z.string()).default([])
});

export const salesQualitySchema = z.object({
  kpis: z.object({
    orders_count: metricSchema,
    net_sales: metricSchema,
    aov: metricSchema,
    upo: metricSchema,
    repeat_purchase_rate: metricSchema,
    top10_sku_share: metricSchema
  }),
  new_vs_returning: z.object({
    new_customer_revenue: metricSchema,
    returning_customer_revenue: metricSchema,
    new_customer_revenue_pct: metricSchema,
    returning_customer_revenue_pct: metricSchema,
    new_customer_orders: metricSchema,
    returning_customer_orders: metricSchema,
    repeat_purchase_rate: metricSchema
  }),
  top_skus: z.array(
    z.object({
      sku: z.string(),
      product_name: z.string(),
      net_sales: metricSchema,
      units: metricSchema,
      revenue_share_pct: metricSchema
    })
  ),
  categories: z.array(
    z.object({
      category: z.string(),
      net_sales: metricSchema,
      revenue_share_pct: metricSchema
    })
  ),
  channel_mix: z.array(
    z.object({
      channel: z.string(),
      net_sales: metricSchema,
      orders: metricSchema,
      revenue_share_pct: metricSchema,
      orders_share_pct: metricSchema
    })
  ),
  geo_mix: z.object({
    countries: z.array(
      z.object({
        country: z.string(),
        net_sales: metricSchema,
        orders: metricSchema,
        revenue_share_pct: metricSchema
      })
    ),
    regions: z.array(
      z.object({
        region: z.string(),
        net_sales: metricSchema,
        orders: metricSchema,
        revenue_share_pct: metricSchema
      })
    ),
    confidence: z.enum(["High", "Medium", "Low"]),
    missing_data: z.array(z.string())
  }),
  currency_mix: z.object({
    items: z.array(
      z.object({
        currency: z.string(),
        net_sales: metricSchema,
        revenue_share_pct: metricSchema
      })
    ),
    confidence: z.enum(["High", "Medium", "Low"]),
    missing_data: z.array(z.string()),
    fx_exposure: z.object({
      enabled: z.boolean(),
      top_non_base_currency: z.string().nullable(),
      share_pct: z.number().nullable()
    })
  }),
  metadata: z.object({
    sources: z.array(z.string()),
    last_refresh: z.string(),
    confidence: z.enum(["High", "Medium", "Low"]),
    window: z.object({
      start: z.string(),
      end: z.string(),
      timezone: z.string()
    })
  })
});

export type SalesQualityResponse = z.infer<typeof salesQualitySchema>;
