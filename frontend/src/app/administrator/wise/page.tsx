"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useAuthedSWRWithBase, postAuthedWithBase, patchAuthedWithBase } from "@/hooks/useApi";
import { apiGetWithBase, resolveApiBase, resolveWiseApiBase } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { Input } from "@/components/ui/input";
import { useCompanyName } from "@/hooks/useCompany";
import SetupTabs from "@/app/administrator/setup-tabs";

type WiseStatus = {
  connected: boolean;
  environment: string | null;
  last_sync_at: string | null;
  token_expires_at: string | null;
  has_client_secret: boolean;
  has_webhook_secret: boolean;
  has_api_token: boolean;
};

type WiseSettings = {
  wise_client_id: string | null;
  wise_environment: string;
  has_client_secret: boolean;
  has_webhook_secret: boolean;
  has_api_token: boolean;
};

const API_BASE = resolveApiBase();
const WISE_API_BASE = resolveWiseApiBase() || API_BASE;

export default function WiseAdminPage() {
  const [environment, setEnvironment] = useState("sandbox");
  const { data, error, mutate } = useAuthedSWRWithBase<WiseStatus>(WISE_API_BASE, `/connectors/wise/status?environment=${environment}`);
  const { data: settings, mutate: mutateSettings } = useAuthedSWRWithBase<WiseSettings>(WISE_API_BASE, `/connectors/wise/settings?environment=${environment}`);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const companyName = useCompanyName();
  const [form, setForm] = useState({
    wise_client_id: "",
    wise_client_secret: "",
    wise_environment: "sandbox",
    webhook_secret: "",
    wise_api_token: "",
    auth_mode: "oauth"
  });

  useEffect(() => {
    if (!settings) return;
    setForm((prev) => ({
      ...prev,
      wise_client_id: prev.wise_client_id || settings.wise_client_id || "",
      wise_environment: settings.wise_environment || prev.wise_environment,
      auth_mode: settings.has_api_token ? "api_token" : prev.auth_mode
    }));
  }, [settings]);

  const startOAuth = () => {
    window.location.href = `${WISE_API_BASE}/connectors/wise/oauth/start?environment=${environment}`;
  };

  const triggerSync = async () => {
    setMessage(null);
    setBusy(true);
    try {
      await postAuthedWithBase(WISE_API_BASE, `/connectors/wise/sync?environment=${environment}`, {});
      setMessage("Sync queued.");
      mutate();
    } catch (err) {
      setMessage("Failed to queue sync.");
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setMessage(null);
    setBusy(true);
    try {
      await postAuthedWithBase(WISE_API_BASE, `/connectors/wise/disconnect?environment=${environment}`, {});
      setMessage("Disconnected.");
      mutate();
    } catch (err) {
      setMessage("Failed to disconnect.");
    } finally {
      setBusy(false);
    }
  };

  const testConnection = async () => {
    setMessage(null);
    setBusy(true);
    try {
      const token = getToken();
      const response = await apiGetWithBase<{ ok: boolean; message?: string }>(
        WISE_API_BASE,
        `/connectors/wise/test?environment=${environment}`,
        token || undefined
      );
      if (response.ok) {
        setMessage("Connection successful.");
      } else {
        setMessage(response.message || "Connection test failed.");
      }
    } catch (err) {
      setMessage("Connection test failed.");
    } finally {
      setBusy(false);
    }
  };

  const saveSettings = async () => {
    setMessage(null);
    setBusy(true);
    try {
      await patchAuthedWithBase(WISE_API_BASE, "/connectors/wise/settings", {
        wise_client_id: form.wise_client_id || undefined,
        wise_client_secret: form.wise_client_secret || undefined,
        wise_environment: form.wise_environment || undefined,
        webhook_secret: form.webhook_secret || undefined,
        wise_api_token: form.wise_api_token || undefined,
        auth_mode: form.auth_mode || undefined
      });
      setForm((prev) => ({ ...prev, wise_client_secret: "", webhook_secret: "", wise_api_token: "" }));
      setMessage("Wise settings saved.");
      mutateSettings();
      mutate();
    } catch (err) {
      setMessage("Failed to save Wise settings.");
    } finally {
      setBusy(false);
    }
  };

  const selectedEnv = environment;
  const canSave = !busy;

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">
          {companyName ? `Wise status - ${companyName}` : "Wise status"}
        </h1>
        <p className="text-sm text-ink/70">Manage the Wise OAuth connection and sync jobs.</p>
      </div>

      <SetupTabs />

      <Card className="grid gap-4">
        {error && <p className="text-sm text-crimson">Failed to load Wise status.</p>}
        {!data && !error && <p className="text-sm text-ink/70">Loading status...</p>}
        {data && (
          <div className="grid gap-2 text-sm">
            <div className="flex items-center gap-2">
              <span className="font-semibold">Connection</span>
              <Badge tone={data.connected ? "neutral" : "danger"}>{data.connected ? "Connected" : "Disconnected"}</Badge>
            </div>
            <div>Environment: {data.environment || "Not set"}</div>
            <div>Last sync: {data.last_sync_at || "Not yet"}</div>
            <div>Token expires: {data.token_expires_at || "Unknown"}</div>
          </div>
        )}

        {message && <p className="text-sm text-ink/70">{message}</p>}

        <div className="flex flex-wrap gap-3">
          <Button type="button" onClick={startOAuth}>
            Connect Wise
          </Button>
          <Button type="button" variant="ghost" onClick={triggerSync} disabled={busy}>
            Sync now
          </Button>
          <Button type="button" variant="danger" onClick={disconnect} disabled={busy}>
            Disconnect
          </Button>
          <Button type="button" variant="ghost" onClick={testConnection} disabled={busy}>
            Test connection
          </Button>
        </div>
      </Card>

      <Card className="grid gap-4">
        <div>
          <h2 className="text-lg font-semibold">Connection settings</h2>
          <p className="text-sm text-ink/60">Secrets are stored encrypted and never displayed.</p>
        </div>
        <div className="grid gap-3">
          <label className="text-sm font-semibold text-ink/70">Auth mode</label>
          <select
            className="rounded-md border border-fog px-3 py-2 text-sm"
            value={form.auth_mode}
            onChange={(event) => setForm({ ...form, auth_mode: event.target.value })}
          >
            <option value="oauth">OAuth</option>
            <option value="api_token">API token</option>
          </select>
        </div>
        {form.auth_mode === "api_token" && (
          <div className="grid gap-3">
            <label className="text-sm font-semibold text-ink/70">API token</label>
            <div className="text-xs text-ink/60">
              API token: {settings?.has_api_token ? "Configured" : "Missing"}
            </div>
            <Input
              type="password"
              value={form.wise_api_token}
              onChange={(event) => setForm({ ...form, wise_api_token: event.target.value })}
              placeholder="Set new API token"
            />
          </div>
        )}
        <div className="grid gap-3">
          <label className="text-sm font-semibold text-ink/70">Wise client ID</label>
          <Input
            value={form.wise_client_id}
            onChange={(event) => setForm({ ...form, wise_client_id: event.target.value })}
            placeholder={settings?.wise_client_id || "Enter client id"}
          />
          <div className="text-xs text-ink/60">
            Client secret: {settings?.has_client_secret ? "Configured" : "Missing"}
          </div>
          <Input
            type="password"
            value={form.wise_client_secret}
            onChange={(event) => setForm({ ...form, wise_client_secret: event.target.value })}
            placeholder="Set new client secret"
          />
        </div>
        <div className="grid gap-3">
          <label className="text-sm font-semibold text-ink/70">Environment</label>
          <select
            className="rounded-md border border-fog px-3 py-2 text-sm"
            value={selectedEnv}
            onChange={(event) => {
              setEnvironment(event.target.value);
              setForm((prev) => ({ ...prev, wise_environment: event.target.value }));
            }}
          >
            <option value="sandbox">sandbox</option>
            <option value="production">production</option>
          </select>
        </div>
        <div className="grid gap-3">
          <label className="text-sm font-semibold text-ink/70">Webhook secret</label>
          <div className="text-xs text-ink/60">
            Webhook secret: {settings?.has_webhook_secret ? "Configured" : "Missing"}
          </div>
          <Input
            type="password"
            value={form.webhook_secret}
            onChange={(event) => setForm({ ...form, webhook_secret: event.target.value })}
            placeholder="Set new webhook secret"
          />
        </div>
        <Button type="button" onClick={saveSettings} disabled={!canSave}>
          Save settings
        </Button>
      </Card>
    </div>
  );
}
