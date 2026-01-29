"use client";

import { Suspense, useState } from "react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getToken } from "@/lib/auth";
import { resolveApiBase } from "@/lib/api";
import { useAuthedSWR } from "@/hooks/useApi";
import SetupClient from "@/app/setup/setup-client";
import SetupTabs from "@/app/administrator/setup-tabs";

const API_BASE = resolveApiBase();

const companySchema = z.object({
  id: z.number(),
  name: z.string(),
  website: z.string().nullable(),
  contact_email: z.string().nullable(),
  contact_phone: z.string().nullable(),
  currency: z.string(),
  timezone: z.string(),
  settlement_lag_days: z.number(),
  thresholds: z.record(z.any())
});

type Company = z.infer<typeof companySchema>;

export default function CompaniesAdminPage() {
  const token = getToken();
  const { data, error, mutate } = useAuthedSWR<Company[]>("/companies");
  const [form, setForm] = useState({ name: "", website: "", contact_email: "", contact_phone: "" });
  const [userForm, setUserForm] = useState({ company_id: "", email: "", password: "", role: "Founder" });
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);

  const userTypeOptions = [
    { label: "Admin", value: "Founder" },
    { label: "Finance", value: "Finance" },
    { label: "Read-only", value: "ReadOnly" },
    { label: "Partner", value: "Ops" }
  ];

  const createCompany = async () => {
    if (!form.name) return;
    setStatus(null);
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/companies`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          name: form.name,
          website: form.website || null,
          contact_email: form.contact_email || null,
          contact_phone: form.contact_phone || null
        })
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to create company");
      }
      setForm({ name: "", website: "", contact_email: "", contact_phone: "" });
      await mutate();
      setStatus("Company created.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create company.";
      setStatus(message);
    } finally {
      setSaving(false);
    }
  };

  const deleteCompany = async (companyId: number) => {
    setStatus(null);
    setDeleting(companyId);
    try {
      const res = await fetch(`${API_BASE}/companies/${companyId}`, {
        method: "DELETE",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || "Failed to delete company");
      }
      await mutate();
      setStatus("Company deleted.");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete company.";
      setStatus(message);
    } finally {
      setDeleting(null);
    }
  };

  const items = data ? z.array(companySchema).parse(data) : [];
  const companyOptions = items.map((company) => ({ id: company.id, name: company.name }));

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Companies</h1>
        <p className="text-ink/70">Founder-only company administration.</p>
      </div>

      <SetupTabs />

      <Suspense fallback={<p className="text-sm text-ink/70">Loading setup...</p>}>
        <SetupClient />
      </Suspense>

      <Card className="grid gap-3">
        <h2 className="text-lg font-semibold">Add company</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <Input placeholder="Company name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <Input placeholder="Website" value={form.website} onChange={(event) => setForm({ ...form, website: event.target.value })} />
          <Input placeholder="Contact email" value={form.contact_email} onChange={(event) => setForm({ ...form, contact_email: event.target.value })} />
          <Input placeholder="Contact phone" value={form.contact_phone} onChange={(event) => setForm({ ...form, contact_phone: event.target.value })} />
        </div>
        <Button type="button" onClick={createCompany} disabled={saving || !form.name}>
          {saving ? "Creating..." : "Create company"}
        </Button>
        {status && <p className="text-sm text-ink/70">{status}</p>}
      </Card>

      <Card className="grid gap-3">
        <h2 className="text-lg font-semibold">Add user to company</h2>
        <div className="grid gap-3 md:grid-cols-2">
          <select
            className="rounded-md border border-fog px-3 py-2 text-sm"
            value={userForm.company_id}
            onChange={(event) => setUserForm({ ...userForm, company_id: event.target.value })}
          >
            <option value="">Select company</option>
            {companyOptions.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
          <Input placeholder="User email" value={userForm.email} onChange={(event) => setUserForm({ ...userForm, email: event.target.value })} />
          <Input placeholder="Temp password" type="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} />
          <div className="grid gap-2">
            <span className="text-xs font-semibold text-ink/70">Userr Type</span>
            <select
              className="rounded-md border border-fog px-3 py-2 text-sm"
              value={userForm.role}
              onChange={(event) => setUserForm({ ...userForm, role: event.target.value })}
            >
              {userTypeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button
          type="button"
          onClick={async () => {
            if (!userForm.company_id || !userForm.email || !userForm.password) return;
            setStatus(null);
            setSaving(true);
            try {
              const res = await fetch(`${API_BASE}/auth/admin/users`, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                  ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                  company_id: Number(userForm.company_id),
                  email: userForm.email,
                  password: userForm.password,
                  role: userForm.role
                })
              });
              if (!res.ok) {
                const text = await res.text();
                throw new Error(text || "Failed to create user");
              }
              setUserForm({ company_id: "", email: "", password: "", role: "Founder" });
              setStatus("User created.");
            } catch (err) {
              const message = err instanceof Error ? err.message : "Failed to create user.";
              setStatus(message);
            } finally {
              setSaving(false);
            }
          }}
          disabled={saving || !userForm.company_id || !userForm.email || !userForm.password}
        >
          {saving ? "Creating..." : "Create user"}
        </Button>
        {status && <p className="text-sm text-ink/70">{status}</p>}
      </Card>

      {error && <p className="text-sm text-crimson">Failed to load companies. {error.message}</p>}
      {!data && !error && <p className="text-sm text-ink/70">Loading companies...</p>}

      {data && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Website</th>
                <th className="px-4 py-3 text-left">Contact</th>
                <th className="px-4 py-3 text-right">Currency</th>
                <th className="px-4 py-3 text-right">Timezone</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((company) => (
                <tr key={company.id} className="border-t border-fog">
                  <td className="px-4 py-3 font-semibold">
                    <a className="text-ink hover:text-ink/70" href={`/setup?company_id=${company.id}`}>
                      {company.name}
                    </a>
                  </td>
                  <td className="px-4 py-3 text-ink/70">{company.website || "-"}</td>
                  <td className="px-4 py-3 text-ink/70">
                    {company.contact_email || "-"}
                    {company.contact_phone ? ` • ${company.contact_phone}` : ""}
                  </td>
                  <td className="px-4 py-3 text-right">{company.currency}</td>
                  <td className="px-4 py-3 text-right">{company.timezone}</td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => deleteCompany(company.id)}
                      disabled={deleting === company.id}
                    >
                      {deleting === company.id ? "Deleting..." : "Delete"}
                    </Button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-ink/60">
                    No companies found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
