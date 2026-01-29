import Link from "next/link";

const links = [
  { href: "/dashboard", label: "Morning Brief" },
  { href: "/sales-quality", label: "Sales Quality" },
  { href: "/inventory", label: "Inventory" },
  { href: "/payables", label: "Payables" },
  { href: "/chat", label: "Ask CFO" }
];

type NavProps = {
  showAdmin?: boolean;
};

export function Nav({ showAdmin }: NavProps) {
  const fullLinks = showAdmin
    ? [...links, { href: "/administrator/companies", label: "Admin" }]
    : links;
  return (
    <nav className="flex flex-wrap items-center gap-4 text-sm font-semibold">
      {fullLinks.map((link) => (
        <Link key={link.href} href={link.href} className="text-ink/80 hover:text-ink">
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
