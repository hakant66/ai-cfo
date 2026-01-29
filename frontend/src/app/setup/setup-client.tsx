"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { deleteAuthed, patchAuthed, postAuthed, postFormAuthed, useAuthedSWR } from "@/hooks/useApi";

export default function SetupClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const companyIdParam = searchParams.get("company_id");
  const companyPath = companyIdParam ? `/companies/${companyIdParam}` : "/companies/me";
  const updatePath = companyIdParam ? `/companies/${companyIdParam}` : "/companies/me";
  const { data: company, mutate: mutateCompany } = useAuthedSWR<any>(companyPath);
  const [companyForm, setCompanyForm] = useState({
    name: "",
    website: "",
    contact_email: "",
    contact_phone: ""
  });
  const [companyStatus, setCompanyStatus] = useState<string | null>(null);
  const [companySaving, setCompanySaving] = useState(false);
  const [companyInitialized, setCompanyInitialized] = useState(false);
  const [defaultsForm, setDefaultsForm] = useState({
    currency: "",
    timezone: "",
    settlement_lag_days: "",
    stockout_weeks: "",
    overstock_weeks: "",
    tracked_currency_pairs: ""
  });
  const [defaultsStatus, setDefaultsStatus] = useState<string | null>(null);
  const [defaultsSaving, setDefaultsSaving] = useState(false);
  const { data: me } = useAuthedSWR<{ role: string }>("/auth/me");
  const [docFile, setDocFile] = useState<File | null>(null);
  const [docStatus, setDocStatus] = useState<string | null>(null);
  const [docUploading, setDocUploading] = useState(false);
  const [docEmbeddingModel, setDocEmbeddingModel] = useState("text-embedding-3-small");
  const [docChunkSize, setDocChunkSize] = useState("");
  const [docReindexing, setDocReindexing] = useState(false);
  const { data: docs, mutate: mutateDocs } = useAuthedSWR<any[]>("/imports/docs", {
    refreshInterval: (data) => {
      if (!Array.isArray(data)) return 0;
      return data.some((doc) => doc.status === "queued" || doc.status === "processing") ? 2000 : 0;
    }
  });
  const isFounder = me?.role === "Founder";
  const { data: companyUsers, mutate: mutateUsers } = useAuthedSWR<any[]>(
    companyIdParam && isFounder ? `/auth/admin/users?company_id=${companyIdParam}` : ""
  );
  const [userEdits, setUserEdits] = useState<Record<string, { email: string; role: string; password: string }>>({});
  const [userStatus, setUserStatus] = useState<string | null>(null);
  const [userSaving, setUserSaving] = useState<number | null>(null);

  const formatDocChunks = (doc: any) => {
    if (doc.status === "indexed") {
      const count = typeof doc.indexed_chunks === "number" ? doc.indexed_chunks : 0;
      return `${count} ${count === 1 ? "chunk" : "chunks"}`;
    }
    if (doc.status === "error") return "Indexing failed";
    if (doc.status === "processing") return "Indexing...";
    return "Queued";
  };

  useEffect(() => {
    if (company && !companyInitialized) {
      setCompanyForm({
        name: company.name || "",
        website: company.website || "",
        contact_email: company.contact_email || "",
        contact_phone: company.contact_phone || ""
      });
      const thresholds = company.thresholds || {};
      const trackedPairs = thresholds.tracked_currency_pairs;
      setDefaultsForm({
        currency: company.currency || "USD",
        timezone: company.timezone || "UTC",
        settlement_lag_days: String(company.settlement_lag_days ?? 2),
        stockout_weeks: String(thresholds.stockout_weeks ?? ""),
        overstock_weeks: String(thresholds.overstock_weeks ?? ""),
        tracked_currency_pairs: Array.isArray(trackedPairs) ? trackedPairs.join(", ") : ""
      });
      setCompanyInitialized(true);
    }
  }, [company, companyInitialized]);

  const saveCompany = async () => {
    setCompanyStatus(null);
    setCompanySaving(true);
    try {
      await patchAuthed(updatePath, {
        name: companyForm.name,
        website: companyForm.website || null,
        contact_email: companyForm.contact_email || null,
        contact_phone: companyForm.contact_phone || null
      });
      setCompanyStatus("Company information saved.");
      mutateCompany();
    } catch (err) {
      setCompanyStatus("Failed to save company information.");
    } finally {
      setCompanySaving(false);
    }
  };

  const uploadDocument = async () => {
    if (!docFile) return;
    setDocStatus(null);
    setDocUploading(true);
    try {
      if (docChunkSize.trim()) {
        const parsed = Number(docChunkSize.trim());
        if (Number.isNaN(parsed) || parsed < 200 || parsed > 5000) {
          setDocStatus("Chunk size must be between 200 and 5000.");
          setDocUploading(false);
          return;
        }
      }
      const form = new FormData();
      form.append("file", docFile);
      form.append("embedding_model", docEmbeddingModel);
      if (docChunkSize.trim()) {
        form.append("chunk_size", docChunkSize.trim());
      }
      await postFormAuthed("/imports/docs", form);
      setDocStatus("Document queued for indexing.");
      setDocFile(null);
      mutateDocs();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to upload document.";
      setDocStatus(message);
    } finally {
      setDocUploading(false);
    }
  };

  const reindexDocuments = async () => {
    setDocStatus(null);
    setDocReindexing(true);
    try {
      await postAuthed("/imports/docs/reindex", {});
      setDocStatus("Reindex queued.");
      mutateDocs();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to queue reindex.";
      setDocStatus(message);
    } finally {
      setDocReindexing(false);
    }
  };

  const deleteDocument = async (id: number) => {
    setDocStatus(null);
    try {
      await deleteAuthed(`/imports/docs/${id}`);
      setDocStatus("Document deleted.");
      mutateDocs();
    } catch (err) {
      setDocStatus("Failed to delete document.");
    }
  };

  const saveDefaults = async () => {
    setDefaultsStatus(null);
    setDefaultsSaving(true);
    try {
      const pairs = defaultsForm.tracked_currency_pairs
        .split(",")
        .map((pair) => pair.replace(/["']/g, "").trim().toUpperCase())
        .filter(Boolean);
      await patchAuthed(updatePath, {
        currency: defaultsForm.currency || null,
        timezone: defaultsForm.timezone || null,
        settlement_lag_days: defaultsForm.settlement_lag_days ? Number(defaultsForm.settlement_lag_days) : null,
        thresholds: {
          stockout_weeks: defaultsForm.stockout_weeks ? Number(defaultsForm.stockout_weeks) : null,
          overstock_weeks: defaultsForm.overstock_weeks ? Number(defaultsForm.overstock_weeks) : null,
          tracked_currency_pairs: pairs.length ? pairs : null
        }
      });
      setDefaultsStatus("Defaults saved.");
      mutateCompany();
    } catch (err) {
      setDefaultsStatus("Failed to save defaults.");
    } finally {
      setDefaultsSaving(false);
    }
  };

  const updateUser = async (userId: number) => {
    const edit = userEdits[String(userId)];
    if (!edit) return;
    setUserSaving(userId);
    setUserStatus(null);
    try {
      await patchAuthed(`/auth/admin/users/${userId}`, {
        email: edit.email || undefined,
        role: edit.role || undefined,
        password: edit.password || undefined
      });
      await mutateUsers();
      setUserStatus("User updated.");
      setUserEdits((prev) => ({ ...prev, [String(userId)]: { ...edit, password: "" } }));
    } catch (err) {
      setUserStatus("Failed to update user.");
    } finally {
      setUserSaving(null);
    }
  };

  const deleteUser = async (userId: number) => {
    setUserSaving(userId);
    setUserStatus(null);
    try {
      await deleteAuthed(`/auth/admin/users/${userId}`);
      await mutateUsers();
      setUserStatus("User deleted.");
    } catch (err) {
      setUserStatus("Failed to delete user.");
    } finally {
      setUserSaving(null);
    }
  };

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-3xl font-semibold">Company setup</h1>
        <p className="text-ink/70">Connect data sources or run in demo mode.</p>
      </div>
      {companyIdParam && (
        <Button type="button" variant="ghost" onClick={() => router.push("/administrator/companies")}>
          Back
        </Button>
      )}

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">Company information</h2>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Company name</label>
          <Input value={companyForm.name} onChange={(event) => setCompanyForm({ ...companyForm, name: event.target.value })} placeholder="Acme Retail Co" />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Company web url</label>
          <Input value={companyForm.website} onChange={(event) => setCompanyForm({ ...companyForm, website: event.target.value })} placeholder="https://example.com" />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Contact person email</label>
          <Input value={companyForm.contact_email} onChange={(event) => setCompanyForm({ ...companyForm, contact_email: event.target.value })} placeholder="finance@example.com" />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Contact person phone</label>
          <Input value={companyForm.contact_phone} onChange={(event) => setCompanyForm({ ...companyForm, contact_phone: event.target.value })} placeholder="+1 415 555 0123" />
        </div>
        {companyStatus && <p className="text-sm text-ink/70">{companyStatus}</p>}
        <Button type="button" onClick={saveCompany} disabled={companySaving || !companyForm.name}>
          {companySaving ? "Saving..." : "Save company info"}
        </Button>
      </Card>

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">Document upload</h2>
        <p className="text-sm text-ink/70">Upload PDF, DOCX, CSV, or XLSX to enable semantic search in Ask CFO.</p>
        <Input type="file" accept=".pdf,.docx,.csv,.xlsx" onChange={(event) => setDocFile(event.target.files?.[0] || null)} />
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Embedding model</label>
          <select
            className="rounded-md border border-fog px-3 py-2 text-sm"
            value={docEmbeddingModel}
            onChange={(event) => setDocEmbeddingModel(event.target.value)}
          >
            <option value="text-embedding-3-large">text-embedding-3-large (better quality, higher cost)</option>
            <option value="text-embedding-3-small">text-embedding-3-small (current, cheaper)</option>
            <option value="text-embedding-ada-002">text-embedding-ada-002 (legacy, generally lower quality than 3-series)</option>
          </select>
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Chunk size</label>
          <Input
            placeholder="1200"
            type="number"
            min={200}
            max={5000}
            value={docChunkSize}
            onChange={(event) => setDocChunkSize(event.target.value)}
          />
          <p className="text-xs text-ink/60">Accepted range: 200-5000 characters.</p>
        </div>
        {docStatus && <p className="text-sm text-ink/70">{docStatus}</p>}
        <Button type="button" onClick={uploadDocument} disabled={docUploading || !docFile}>
          {docUploading ? "Uploading..." : "Upload document"}
        </Button>
        <div className="grid gap-2">
          <p className="text-sm font-semibold text-ink/70">Documents</p>
          {!docs && <p className="text-sm text-ink/70">Loading documents...</p>}
          {docs && docs.length === 0 && <p className="text-sm text-ink/70">No documents uploaded yet.</p>}
          {docs && docs.map((doc) => (
            <div key={doc.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-fog bg-white px-3 py-2 text-sm">
              <div>
                <p className="font-semibold">{doc.filename}</p>
                <p className="text-xs text-ink/60">{doc.file_type.toUpperCase()} - {formatDocChunks(doc)}</p>
              </div>
              <div className="text-xs text-ink/60">
                {doc.status}
                {doc.status === "indexed" && doc.indexed_at ? ` - ${doc.indexed_at}` : ""}
                {doc.status === "error" && doc.error_message ? ` - ${doc.error_message}` : ""}
              </div>
              <Button type="button" variant="ghost" onClick={() => deleteDocument(doc.id)}>
                Delete
              </Button>
            </div>
          ))}
        </div>
        <Button type="button" variant="ghost" onClick={reindexDocuments} disabled={docReindexing}>
          {docReindexing ? "Reindexing..." : "Reindex existing documents"}
        </Button>
      </Card>

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">CSV imports</h2>
        <p className="text-sm text-ink/70">Templates are available in the repository under `backend/templates`.</p>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Bank transactions CSV</label>
          <Input type="file" />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Payables CSV</label>
          <Input type="file" />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Purchase orders CSV</label>
          <Input type="file" />
        </div>
        <Button type="button">Upload CSVs</Button>
      </Card>

      <Card className="grid gap-4">
        <h2 className="text-lg font-semibold">Defaults</h2>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Currency</label>
          <Input
            placeholder="USD"
            value={defaultsForm.currency}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, currency: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Timezone</label>
          <Input
            placeholder="UTC"
            value={defaultsForm.timezone}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, timezone: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Settlement lag (days)</label>
          <Input
            placeholder="2"
            value={defaultsForm.settlement_lag_days}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, settlement_lag_days: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Stockout threshold (weeks)</label>
          <Input
            placeholder="2"
            value={defaultsForm.stockout_weeks}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, stockout_weeks: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Overstock threshold (weeks)</label>
          <Input
            placeholder="12"
            value={defaultsForm.overstock_weeks}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, overstock_weeks: event.target.value })}
          />
        </div>
        <div className="grid gap-2">
          <label className="text-sm font-semibold text-ink/70">Tracked currency pairs</label>
          <Input
            placeholder='EUR/GBP, GBP/USD, EUR/USD'
            value={defaultsForm.tracked_currency_pairs}
            onChange={(event) => setDefaultsForm({ ...defaultsForm, tracked_currency_pairs: event.target.value })}
          />
        </div>
        {defaultsStatus && <p className="text-sm text-ink/70">{defaultsStatus}</p>}
        <Button type="button" onClick={saveDefaults} disabled={defaultsSaving}>
          {defaultsSaving ? "Saving..." : "Save settings"}
        </Button>
      </Card>

      <Card className="grid gap-3">
        <h2 className="text-lg font-semibold">Demo mode</h2>
        <p className="text-sm text-ink/70">Seed a demo company with synthetic data for local testing.</p>
        <Button type="button">Load demo data</Button>
      </Card>

      {companyIdParam && isFounder && (
        <Card className="grid gap-4">
          <h2 className="text-lg font-semibold">Company users</h2>
          <p className="text-sm text-ink/70">Founder-only: manage users for this company.</p>
          {userStatus && <p className="text-sm text-ink/70">{userStatus}</p>}
          {!companyUsers && <p className="text-sm text-ink/70">Loading users...</p>}
          {companyUsers && companyUsers.length === 0 && <p className="text-sm text-ink/70">No users found.</p>}
          {companyUsers && companyUsers.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-fog">
              <table className="w-full text-sm">
                <thead className="bg-fog text-xs uppercase tracking-wide text-ink/60">
                  <tr>
                    <th className="px-3 py-2 text-left">Email</th>
                    <th className="px-3 py-2 text-left">Role</th>
                    <th className="px-3 py-2 text-left">Password reset</th>
                    <th className="px-3 py-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {companyUsers.map((user: any) => {
                    const edit = userEdits[String(user.id)] || { email: user.email, role: user.role, password: "" };
                    return (
                      <tr key={user.id} className="border-t border-fog">
                        <td className="px-3 py-2">
                          <Input
                            value={edit.email}
                            onChange={(event) =>
                              setUserEdits((prev) => ({ ...prev, [String(user.id)]: { ...edit, email: event.target.value } }))
                            }
                          />
                        </td>
                        <td className="px-3 py-2">
                          <select
                            className="w-full rounded-md border border-fog px-2 py-2 text-sm"
                            value={edit.role}
                            onChange={(event) =>
                              setUserEdits((prev) => ({ ...prev, [String(user.id)]: { ...edit, role: event.target.value } }))
                            }
                          >
                            <option value="Founder">Founder</option>
                            <option value="Finance">Finance</option>
                            <option value="Ops">Ops</option>
                            <option value="Marketing">Marketing</option>
                            <option value="ReadOnly">ReadOnly</option>
                          </select>
                        </td>
                        <td className="px-3 py-2">
                          <Input
                            type="password"
                            placeholder="New password"
                            value={edit.password}
                            onChange={(event) =>
                              setUserEdits((prev) => ({ ...prev, [String(user.id)]: { ...edit, password: event.target.value } }))
                            }
                          />
                        </td>
                        <td className="px-3 py-2 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button type="button" variant="ghost" onClick={() => updateUser(user.id)} disabled={userSaving === user.id}>
                              {userSaving === user.id ? "Saving..." : "Save"}
                            </Button>
                            <Button type="button" variant="ghost" onClick={() => deleteUser(user.id)} disabled={userSaving === user.id}>
                              Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
