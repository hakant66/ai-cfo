"use client";

import { useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Nav } from "@/components/nav";
import { clearToken, getToken } from "@/lib/auth";
import { useAuthedSWR } from "@/hooks/useApi";

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const shouldHide = useMemo(() => pathname === "/" || pathname === "/login", [pathname]);
  const token = shouldHide ? null : getToken();
  const { data: me } = useAuthedSWR<{ email: string; role: string }>(shouldHide ? "" : "/auth/me");
  if (shouldHide) return null;

  const logout = () => {
    clearToken();
    router.push("/login");
  };

  const showAdmin = me?.role === "Founder" || me?.role === "Admin";

  return (
    <header className="sticky top-0 z-10 border-b border-fog/60 bg-white/70 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink text-sm font-semibold text-white">CFO</div>
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-ink/60">AI Assistant</p>
            <p className="text-lg font-semibold">Retail Command Center</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <Nav showAdmin={showAdmin} />
          {token && me?.email && (
            <div className="flex items-center gap-3">
              <span className="text-sm text-ink/70">{me.email}</span>
              <Badge tone={me.role === "Founder" ? "warn" : "neutral"}>{me.role}</Badge>
            </div>
          )}
          {token && (
            <button className="text-sm font-semibold text-ink/70 hover:text-ink" onClick={logout}>
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
