"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { apiGet, apiPost } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

const schema = z.object({
  company_id: z.string().min(1),
  email: z.string().email(),
  password: z.string().min(6)
});

const companySchema = z.object({
  id: z.number(),
  name: z.string()
});

const companiesSchema = z.array(companySchema);

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ company_id: "", email: "", password: "" });
  const [error, setError] = useState<string | null>(null);
  const [companies, setCompanies] = useState<z.infer<typeof companiesSchema>>([]);
  const [companiesError, setCompaniesError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadCompanies = async () => {
      try {
        const data = await apiGet<z.infer<typeof companiesSchema>>("/companies/public");
        const parsed = companiesSchema.safeParse(data);
        if (!parsed.success) {
          throw new Error("Invalid companies payload");
        }
        if (isMounted) {
          setCompanies(parsed.data);
        }
      } catch (err) {
        if (isMounted) {
          setCompaniesError("Failed to load companies.");
        }
      }
    };
    loadCompanies();
    return () => {
      isMounted = false;
    };
  }, []);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    const parsed = schema.safeParse(form);
    if (!parsed.success) {
      setError("Enter a company, email, and password.");
      return;
    }
    try {
      const payload = {
        company_id: Number(parsed.data.company_id),
        email: parsed.data.email,
        password: parsed.data.password
      };
      const response = await apiPost<{ access_token: string }>("/auth/login", payload);
      setToken(response.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError("Login failed. Check credentials.");
    }
  };

  return (
    <div className="grid max-w-md gap-6">
      <h1 className="text-3xl font-semibold">Welcome back</h1>
      <Card>
        <form className="grid gap-4" onSubmit={onSubmit}>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Company</label>
            <select
              className="rounded-md border border-fog px-3 py-2 text-sm"
              value={form.company_id}
              onChange={(event) => setForm({ ...form, company_id: event.target.value })}
            >
              <option value="">Select company</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
            {companiesError && <p className="text-sm text-crimson">{companiesError}</p>}
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Email</label>
            <Input
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              placeholder="finance@retailco.com"
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Password</label>
            <Input
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </div>
          {error && <p className="text-sm text-crimson">{error}</p>}
          <Button type="submit">Sign in</Button>
        </form>
      </Card>
    </div>
  );
}
