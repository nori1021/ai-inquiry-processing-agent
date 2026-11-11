import Link from "next/link";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/inquiries/new", label: "New Inquiry" },
  { href: "/evaluations", label: "Evaluations" },
];

export function Shell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6 border-b border-[color:var(--line)] pb-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[color:var(--text-muted)]">
              Ops console
            </p>
            <p className="font-display text-2xl tracking-tight text-white md:text-3xl">
              AI Inquiry Processing
            </p>
          </div>
          <nav className="flex flex-wrap gap-2 text-base">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="border border-[color:var(--line)] px-3 py-2 text-[color:var(--text)] hover:border-[color:var(--accent)] hover:text-white"
              >
                {l.label}
              </Link>
            ))}
          </nav>
        </div>
        <h1 className="mt-4 text-xl font-semibold text-white">{title}</h1>
      </header>
      {children}
    </div>
  );
}
