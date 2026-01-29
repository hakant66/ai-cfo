"use client";

import { Card } from "@/components/ui/card";
import ShopifyConnectionCard from "@/app/administrator/shopify-connection-card";
import SetupTabs from "@/app/administrator/setup-tabs";

export default function AdministratorPage() {
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Administrator</h1>
        <p className="text-ink/70">Manage setup and demo data in one place.</p>
      </div>

      <SetupTabs />

      <ShopifyConnectionCard />
    </div>
  );
}
