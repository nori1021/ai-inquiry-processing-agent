const STEPS = [
  "RECEIVED",
  "ANALYZING",
  "INVESTIGATING",
  "AWAITING_DECISION_APPROVAL",
  "DRAFTING",
  "AWAITING_EMAIL_APPROVAL",
  "COMPLETED",
] as const;

const LABELS: Record<string, string> = {
  RECEIVED: "Received",
  ANALYZING: "Analyzing",
  INVESTIGATING: "Investigating",
  AWAITING_DECISION_APPROVAL: "Decision approval",
  DRAFTING: "Drafting",
  AWAITING_EMAIL_APPROVAL: "Email approval",
  COMPLETED: "Completed",
  REPLANNING: "Replanning",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

function stepIndex(state: string): number {
  if (state === "REPLANNING") return 2;
  if (state === "FAILED" || state === "CANCELLED") return -1;
  const i = STEPS.indexOf(state as (typeof STEPS)[number]);
  return i;
}

export function WorkflowProgress({ state }: { state: string }) {
  const idx = stepIndex(state);
  return (
    <div className="ops-panel" aria-label="Workflow progress">
      <p className="ops-panel-title">Workflow progress</p>
      <ol className="flex flex-wrap gap-2">
        {STEPS.map((step, i) => {
          const done = idx > i || state === "COMPLETED";
          const current = idx === i;
          const cls = current
            ? "badge-action"
            : done
              ? "badge-found"
              : "badge-idle";
          return (
            <li key={step} className={`status-badge ${cls}`}>
              {i + 1}. {LABELS[step] || step}
              {current ? " (current)" : ""}
            </li>
          );
        })}
      </ol>
      {state === "FAILED" || state === "CANCELLED" ? (
        <p className="mt-2 text-base text-[color:var(--unknown-fg)]">
          Terminal state: {LABELS[state] || state}
        </p>
      ) : null}
    </div>
  );
}
