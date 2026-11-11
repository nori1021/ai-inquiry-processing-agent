import { SplitItem } from "@/lib/operatorSplit";

/** Compact list used inside collapsed "AI decided" section. */
export function AiDecidedPanel({ items }: { items: SplitItem[] }) {
  return (
    <section aria-label="AI decided">
      {!items.length ? (
        <p className="text-base text-[color:var(--text-muted)]">
          No structured AI decisions recorded yet for this inquiry.
        </p>
      ) : (
        <ul className="divide-y divide-[color:var(--line)]">
          {items.map((item) => (
            <li key={item.id} className="flex flex-wrap gap-2 py-2.5 text-base">
              <span className="status-badge badge-found shrink-0">{item.label}</span>
              <span className="min-w-0 flex-1 text-[color:var(--text)]">
                {item.detail}
                {item.why ? (
                  <span className="mt-0.5 block text-sm text-[color:var(--text-muted)]">
                    {item.why}
                  </span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
