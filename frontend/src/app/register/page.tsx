"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { apiPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(6),
  company_name: z.string().min(2),
  role: z.enum(["Founder", "Finance", "Ops", "Marketing", "ReadOnly"])
});

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    email: "",
    password: "",
    company_name: "",
    role: "Founder"
  });
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    const parsed = schema.safeParse(form);
    if (!parsed.success) {
      setError("Complete all fields.");
      return;
    }
    try {
      await apiPost("/auth/register", form);
      router.push("/login");
    } catch (err) {
      setError("Registration failed.");
    }
  };

  return (
    <div className="grid max-w-md gap-6">
      <h1 className="text-3xl font-semibold">Create your AI Assistant</h1>
      <Card>
        <form className="grid gap-4" onSubmit={onSubmit}>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Company name</label>
            <Input
              value={form.company_name}
              onChange={(event) => setForm({ ...form, company_name: event.target.value })}
              placeholder="Northwind Retail"
            />
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Email</label>
            <Input
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              placeholder="founder@northwind.com"
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
          <div className="grid gap-2">
            <label className="text-sm font-semibold text-ink/70">Role</label>
            <select
              className="rounded-md border border-fog px-3 py-2 text-sm"
              value={form.role}
              onChange={(event) => setForm({ ...form, role: event.target.value })}
            >
              <option value="Founder">Founder</option>
              <option value="Finance">Finance</option>
              <option value="Ops">Ops</option>
              <option value="Marketing">Marketing</option>
              <option value="ReadOnly">ReadOnly</option>
            </select>
          </div>
          {error && <p className="text-sm text-crimson">{error}</p>}
          <Button type="submit">Register</Button>
        </form>
      </Card>
    </div>
  );
}
