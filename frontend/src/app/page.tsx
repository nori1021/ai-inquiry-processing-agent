import Link from "next/link";
import { Shell } from "@/components/Shell";
import { ApprovalStateBadge, WorkflowStateBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

export default async function DashboardPage() {
  let workflows: Awaited<ReturnType<typeof api.listWorkflows>> = [];
  let error = "";
  try {
    workflows = await api.listWorkflows();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load workflows";
  }

  const pendingDecision = workflows.filter((w) =>
    w.state.includes("AWAITING_DECISION")
  ).length;
  const pendingEmail = workflows.filter((w) =>
    w.state.includes("AWAITING_EMAIL")
  ).length;
  const pendingTotal = workflows.filter((w) =>
    w.approvals?.some((a) => a.status === "pending")
  ).length;

  return (
    <Shell title="Operator dashboard">
      {error ? (
        <p className="ops-panel mb-4 border-[color:var(--unknown-border)] text-sm text-[color:var(--unknown-fg)]">
          Backend unreachable at NEXT_PUBLIC_API_BASE. Start FastAPI on :8000.
          <br />
          {error}
        </p>
      ) : null}

      <div className="mb-4 grid gap-3 sm:grid-cols-3">
        <div className={`ops-panel ${pendingDecision ? "pending-row" : ""}`}>
          <p className="text-[11px] uppercase tracking-wide text-[color:var(--text-muted)]">
            Decision approvals
          </p>
          <p className="mt-1 text-2xl font-semibold text-white">{pendingDecision}</p>
        </div>
        <div className={`ops-panel ${pendingEmail ? "pending-row" : ""}`}>
          <p className="text-[11px] uppercase tracking-wide text-[color:var(--text-muted)]">
            Email approvals
          </p>
          <p className="mt-1 text-2xl font-semibold text-white">{pendingEmail}</p>
        </div>
        <div className="ops-panel">
          <p className="text-[11px] uppercase tracking-wide text-[color:var(--text-muted)]">
            Total inquiries
          </p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {workflows.length}
          </p>
          {pendingTotal ? (
            <p className="mt-1 text-xs text-[color:var(--action-fg)]">
              {pendingTotal} with pending approval records
            </p>
          ) : null}
        </div>
      </div>

      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm text-[color:var(--text-muted)]">
          Pending items highlighted — open to review LDAP/GAC and approve
        </p>
        <Link
          href="/inquiries/new"
          className="bg-[color:var(--accent)] px-3 py-2 text-sm font-semibold text-[color:var(--bg0)]"
        >
          New Inquiry
        </Link>
      </div>

      <div className="overflow-hidden border border-[color:var(--line)]">
        <table className="ops-table w-full text-left text-sm">
          <thead>
            <tr>
              <th>ID</th>
              <th>Subject</th>
              <th>State</th>
              <th>Approvals</th>
            </tr>
          </thead>
          <tbody>
            {workflows.map((w) => {
              const pending = (w.approvals || []).filter(
                (a) => a.status === "pending"
              );
              const needsAction = pending.length > 0 || w.state.includes("AWAITING");
              return (
                <tr
                  key={w.id}
                  className={needsAction ? "pending-row" : undefined}
                >
                  <td className="px-2 py-2">
                    <Link
                      href={`/inquiries/${w.id}`}
                      className="font-mono text-[color:var(--accent)] underline-offset-2 hover:underline"
                    >
                      #{w.id}
                    </Link>
                  </td>
                  <td className="px-2 py-2 text-[color:var(--text)]">
                    {w.subject || "(no subject)"}
                  </td>
                  <td className="px-2 py-2">
                    <WorkflowStateBadge state={w.state} />
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex flex-wrap gap-1">
                      {pending.length ? (
                        pending.map((a) => (
                          <ApprovalStateBadge
                            key={a.id}
                            status={a.status}
                            type={a.approval_type}
                          />
                        ))
                      ) : (
                        <span className="text-xs text-[color:var(--text-muted)]">
                          —
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
            {!workflows.length && !error ? (
              <tr>
                <td
                  className="px-3 py-6 text-[color:var(--text-muted)]"
                  colSpan={4}
                >
                  No inquiries yet. Create one or run scripts\seed-and-start.bat.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </Shell>
  );
}
