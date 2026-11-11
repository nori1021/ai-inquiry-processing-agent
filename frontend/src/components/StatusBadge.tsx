import {
  CombinedState,
  RegFlag,
  combinedLabel,
  regFlagLabel,
} from "@/lib/registrationStatus";

/** Text + color badges — never color-only. */

const REG_STYLES: Record<RegFlag, string> = {
  yes: "badge-found",
  no: "badge-missing",
  unknown: "badge-unknown",
  not_run: "badge-idle",
};

const COMBINED_STYLES: Record<CombinedState, string> = {
  LDAP_AND_GAC: "badge-found",
  LDAP_ONLY: "badge-partial",
  GAC_ONLY: "badge-partial",
  NEITHER: "badge-missing",
  UNKNOWN: "badge-unknown",
  INCOMPLETE: "badge-idle",
};

const INVESTIGATE_STYLES: Record<string, string> = {
  REQUIRED: "badge-action",
  NOT_REQUIRED: "badge-idle",
  UNCERTAIN: "badge-warn",
};

export function RegFlagBadge({
  flag,
  source,
}: {
  flag: RegFlag;
  source?: "LDAP" | "GAC";
}) {
  const label = source
    ? `${source}: ${regFlagLabel(flag)}`
    : regFlagLabel(flag);
  return (
    <span className={`status-badge ${REG_STYLES[flag]}`} title={label}>
      {label}
    </span>
  );
}

export function CombinedBadge({ state }: { state: CombinedState }) {
  const label = combinedLabel(state);
  return (
    <span className={`status-badge ${COMBINED_STYLES[state]}`} title={label}>
      {label}
    </span>
  );
}

export function InvestigateBadge({ need }: { need?: string }) {
  const key = need || "UNCERTAIN";
  const style = INVESTIGATE_STYLES[key] || "badge-warn";
  return (
    <span className={`status-badge ${style}`} title={`Investigate: ${key}`}>
      {key}
    </span>
  );
}

export function ApprovalStateBadge({
  status,
  type,
}: {
  status: string;
  type?: string;
}) {
  const pending = status === "pending";
  const approved = status === "approved";
  const style = pending
    ? "badge-action"
    : approved
      ? "badge-found"
      : status === "rejected"
        ? "badge-missing"
        : "badge-idle";
  const label = type ? `${type}: ${status.toUpperCase()}` : status.toUpperCase();
  return <span className={`status-badge ${style}`}>{label}</span>;
}

export function WorkflowStateBadge({ state }: { state: string }) {
  const awaiting = state.includes("AWAITING");
  const done = state === "COMPLETED" || state === "FAILED";
  const style = awaiting
    ? "badge-action"
    : state === "COMPLETED"
      ? "badge-found"
      : state === "FAILED"
        ? "badge-missing"
        : "badge-idle";
  return (
    <span className={`status-badge ${style} font-mono`} title={state}>
      {state}
      {awaiting && !done ? " — ACTION NEEDED" : ""}
    </span>
  );
}
