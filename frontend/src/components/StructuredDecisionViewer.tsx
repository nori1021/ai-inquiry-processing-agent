import { InvestigateBadge } from "@/components/StatusBadge";

type User = {
  email?: string | null;
  role?: string;
  reason?: string;
  investigate?: string;
};

type ReviewFlag = {
  code?: string;
  message?: string;
  severity?: string;
};

type PlanItem = {
  target_type?: string;
  target?: string;
  need?: string;
  role?: string | null;
  reason?: string;
};

type Props = {
  users: User[];
  plan: PlanItem[];
  flags: ReviewFlag[];
  needsHumanReview?: boolean;
  confidence?: number | null;
  summary?: string;
};

export function StructuredDecisionViewer({
  users,
  plan,
  flags,
  needsHumanReview,
  confidence,
  summary,
}: Props) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-[color:var(--text-muted)]">
          confidence:{" "}
          <span className="font-mono text-[color:var(--text)]">
            {confidence ?? "n/a"}
          </span>
        </span>
        <span
          className={`status-badge ${needsHumanReview ? "badge-action" : "badge-found"}`}
        >
          {needsHumanReview ? "NEEDS HUMAN REVIEW" : "AUTO-PASS CANDIDATE"}
        </span>
      </div>
      {summary ? (
        <p className="text-sm leading-snug text-[color:var(--text)]">{summary}</p>
      ) : null}

      <div>
        <h3 className="ops-panel-title mb-1">Users and investigation</h3>
        <table className="ops-table w-full">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Need</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u, i) => (
              <tr
                key={`${u.email}-${i}`}
                className={u.investigate === "NOT_REQUIRED" ? "opacity-60" : undefined}
              >
                <td className="font-mono text-xs text-white">
                  {u.email || "(no email)"}
                </td>
                <td className="text-xs">{u.role || "unknown"}</td>
                <td>
                  <InvestigateBadge need={u.investigate} />
                </td>
                <td className="text-[11px] text-[color:var(--text-muted)]">
                  {u.reason || "—"}
                </td>
              </tr>
            ))}
            {!users.length ? (
              <tr>
                <td colSpan={4} className="text-xs text-[color:var(--text-muted)]">
                  No users extracted
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <h3 className="ops-panel-title mb-1">Investigation plan</h3>
          <ul className="space-y-1 text-xs text-[color:var(--text)]">
            {plan.map((p, i) => (
              <li key={`${p.target}-${i}`} className="font-mono">
                <InvestigateBadge need={p.need} />{" "}
                <span className="text-[color:var(--text-muted)]">
                  {p.target_type}:
                </span>{" "}
                {p.target}
              </li>
            ))}
            {!plan.length ? (
              <li className="text-[color:var(--text-muted)]">No plan items</li>
            ) : null}
          </ul>
        </div>
        <div>
          <h3 className="ops-panel-title mb-1">Validation flags</h3>
          <ul className="space-y-1 text-xs">
            {flags.map((f, i) => (
              <li key={`${f.code}-${i}`}>
                <span className="status-badge badge-warn">{f.code}</span>{" "}
                <span className="text-[color:var(--text)]">{f.message}</span>
              </li>
            ))}
            {!flags.length ? (
              <li className="text-[color:var(--text-muted)]">No review flags</li>
            ) : null}
          </ul>
        </div>
      </div>
    </div>
  );
}
