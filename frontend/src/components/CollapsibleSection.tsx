"use client";

import { useState } from "react";

type Props = {
  title: string;
  subtitle?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  tone?: "default" | "muted";
};

export function CollapsibleSection({
  title,
  subtitle,
  defaultOpen = false,
  children,
  tone = "default",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section
      className={`ops-panel ${tone === "muted" ? "opacity-90" : ""}`}
    >
      <button
        type="button"
        className="flex w-full items-start justify-between gap-3 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>
          <span className="block text-base font-semibold text-white">
            {title}
          </span>
          {subtitle ? (
            <span className="mt-0.5 block text-sm text-[color:var(--text-muted)]">
              {subtitle}
            </span>
          ) : null}
        </span>
        <span className="status-badge badge-idle shrink-0">
          {open ? "HIDE" : "SHOW"}
        </span>
      </button>
      {open ? <div className="mt-4 border-t border-[color:var(--line)] pt-4">{children}</div> : null}
    </section>
  );
}
