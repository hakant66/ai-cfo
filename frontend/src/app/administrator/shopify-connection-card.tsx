"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { postAuthed, useAuthedSWR } from "@/hooks/useApi";

export default function ShopifyConnectionCard() {
  const [shopDomain, setShopDomain] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [shopifyStatus, setShopifyStatus] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [saving, setSaving] = useState(false);
  const { data: me } = useAuthedSWR<{ role: string }>("/auth/me");
  const canSync = me?.role === "Founder";

  const testShopify = async () => {
    setShopifyStatus(null);
    setSyncStatus(null);
    setLoading(true);
    try {
      const result = await postAuthed<{ mode?: string }>("/connectors/shopify/test", {
        shop_domain: shopDomain,
        access_token: accessToken
      });
      setShopifyStatus(`Connected (${result.mode || "ok"})`);
    } catch (err) {
      setShopifyStatus("Connection failed. Check domain/token or mock status.");
    } finally {
      setLoading(false);
    }
  };

  const syncShopify = async () => {
    setSyncStatus(null);
    setSyncing(true);
    try {
      await postAuthed("/connectors/shopify/sync", {
        shop_domain: shopDomain,
        access_token: accessToken
      });
      setSyncStatus("Sync queued. Refresh the dashboard in a minute.");
    } catch (err) {
      setSyncStatus("Sync failed. Verify credentials and permissions.");
    } finally {
      setSyncing(false);
    }
  };

  const saveShopifySettings = async () => {
    setSaveStatus(null);
    setSaving(true);
    try {
      const result = await postAuthed<{ status: string }>("/connectors/shopify/settings", {
        shop_domain: shopDomain,
        access_token: accessToken
      });
      setSaveStatus(result.status === "saved" ? "Shopify settings saved." : "Shopify settings updated.");
    } catch (err) {
      setSaveStatus("Failed to save Shopify settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div id="shopify-api">
      <Card className="grid gap-4">
      <div>
        <h2 className="text-lg font-semibold">Shopify API</h2>
        <p className="text-sm text-ink/70">Connect a Shopify store and sync orders on demand.</p>
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-semibold text-ink/70">Shop domain</label>
        <Input value={shopDomain} onChange={(event) => setShopDomain(event.target.value)} placeholder="your-store.myshopify.com" />
      </div>
      <div className="grid gap-2">
        <label className="text-sm font-semibold text-ink/70">Admin access token</label>
        <Input value={accessToken} onChange={(event) => setAccessToken(event.target.value)} placeholder="shpat_..." />
      </div>
      {shopifyStatus && <p className="text-sm text-ink/70">{shopifyStatus}</p>}
      {syncStatus && <p className="text-sm text-ink/70">{syncStatus}</p>}
      {saveStatus && <p className="text-sm text-ink/70">{saveStatus}</p>}
      <Button type="button" onClick={testShopify} disabled={loading}>
        {loading ? "Testing..." : "Test connection"}
      </Button>
      <Button type="button" variant="ghost" onClick={saveShopifySettings} disabled={saving || !shopDomain || !accessToken}>
        {saving ? "Saving..." : "Save Shopify settings"}
      </Button>
      {canSync && (
        <Button type="button" variant="ghost" onClick={syncShopify} disabled={syncing || !shopDomain || !accessToken}>
          {syncing ? "Syncing..." : "Sync Shopify"}
        </Button>
      )}
      </Card>
    </div>
  );
}
