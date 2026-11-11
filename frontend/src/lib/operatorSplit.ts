/**
 * Derive scannable "AI decided" vs "Needs operator" lists from real workflow data.
 * Never invents tool/model outcomes — only surfaces fields that exist.
 */

import {
  UserRegRow,
  buildRegistrationRows,
  combinedLabel,
  regFlagLabel,
  ToolResultLike,
} from "./registrationStatus";

export type SplitItem = {
  id: string;
  label: string;
  detail: string;
  why?: string;
};

export type OperatorSplit = {
  aiDecided: SplitItem[];
  needsOperator: SplitItem[];
  hasPendingAction: boolean;
};

/** Show LDAP/GAC snapshot when it informs a pending decision. */
export function isRegistrationRelevant(input: {
  state: string;
  toolNames: string[];
  needsItems: Array<{ id: string; label: string }>;
}): boolean {
  const hasRegTool = input.toolNames.some((t) =>
    /ldap|gac|registration/i.test(t || "")
  );
  const needsReg = input.needsItems.some((i) =>
    /registration|ldap|gac|domain|company|identity/i.test(`${i.id} ${i.label}`)
  );
  return (
    hasRegTool ||
    needsReg ||
    input.state.includes("AWAITING_DECISION") ||
    input.state.includes("INVESTIGAT")
  );
}

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

type Approval = {
  id: number;
  approval_type: string;
  status: string;
  summary: string;
};

type AnalysisLike = {
  analysis?: {
    summary?: string;
    intent?: string;
    category?: string;
    confidence?: number | null;
    users?: User[];
  };
  selected_tools?: Array<{ tool: string; reason?: string }>;
  tool_results?: ToolResultLike[];
  rag_references?: Array<{ source?: string; id?: string | null }>;
  review_flags?: ReviewFlag[];
  needs_human_review?: boolean;
  ai_mode?: string;
  provider_error?: string | null;
  provider_status?: string;
};

const FLAG_WHY: Record<string, string> = {
  confidence_gate: "Confidence below auto-pass threshold — human must confirm.",
  confidence_below_threshold:
    "Confidence below auto-pass threshold — human must confirm.",
  similar_domain: "Similar domain match may be a lookalike — verify company.",
  similar_domains: "Similar domain match may be a lookalike — verify company.",
  ldap_gac_conflict: "LDAP and GAC records disagree — reconcile before reply.",
  company_conflict: "Conflicting company information — verify identity.",
  conflicting_company: "Conflicting company information — verify identity.",
  ldap_source_unknown: "LDAP source UNKNOWN (not the same as not registered).",
  gac_source_unknown: "GAC source UNKNOWN (not the same as not registered).",
  tool_limit_truncated: "Tool results were truncated — review may be incomplete.",
  prior_password_reset_failed:
    "User reports prior reset failed; do not re-send standard reset steps.",
};

function whyForFlag(code?: string, message?: string): string {
  if (code && FLAG_WHY[code]) return FLAG_WHY[code];
  if (message) return message;
  return "Validation gate flagged this for human review.";
}

export function buildOperatorSplit(input: {
  state: string;
  approvals: Approval[];
  analysis: AnalysisLike;
  draftTemplateId?: string | null;
}): OperatorSplit {
  const { state, approvals, analysis, draftTemplateId } = input;
  const inner = analysis.analysis || {};
  const users = inner.users || [];
  const flags = analysis.review_flags || [];
  const tools = analysis.selected_tools || [];
  const results = analysis.tool_results || [];
  const rag = analysis.rag_references || [];

  const aiDecided: SplitItem[] = [];
  const needsOperator: SplitItem[] = [];
  const decisionPending =
    state === "AWAITING_DECISION_APPROVAL" ||
    approvals.some(
      (a) =>
        a.status === "pending" &&
        a.approval_type.toLowerCase().includes("decision")
    );
  const emailPending =
    state === "AWAITING_EMAIL_APPROVAL" ||
    approvals.some(
      (a) =>
        a.status === "pending" && a.approval_type.toLowerCase().includes("email")
    );
  // "What to verify" only shows unresolved operator work
  const surfaceDecisionIssues = decisionPending;

  if (inner.category) {
    aiDecided.push({
      id: "category",
      label: "Category",
      detail: inner.category,
    });
  }
  if (inner.intent) {
    aiDecided.push({
      id: "intent",
      label: "Intent",
      detail: inner.intent,
    });
  }
  if (inner.summary) {
    aiDecided.push({
      id: "summary",
      label: "Summary",
      detail: inner.summary,
    });
  }
  if (inner.confidence != null) {
    aiDecided.push({
      id: "confidence",
      label: "Confidence",
      detail: String(inner.confidence),
    });
  }
  if (analysis.ai_mode) {
    aiDecided.push({
      id: "ai_mode",
      label: "AI mode",
      detail: analysis.ai_mode,
    });
  }

  for (const u of users) {
    const email = u.email || "(no email)";
    if (u.investigate === "REQUIRED" || u.investigate === "NOT_REQUIRED") {
      aiDecided.push({
        id: `user-${email}`,
        label: `User · ${u.investigate}`,
        detail: `${email} (${u.role || "unknown"})`,
        why: u.reason || undefined,
      });
    } else if (u.investigate === "UNCERTAIN") {
      const item = {
        id: `uncertain-${email}`,
        label: "Investigation UNCERTAIN",
        detail: `${email} (${u.role || "unknown"})`,
        why:
          u.reason ||
          "AI could not decide whether to investigate — operator judgment required.",
      };
      if (surfaceDecisionIssues) needsOperator.push(item);
      else aiDecided.push({ ...item, label: "Was UNCERTAIN (resolved path)" });
    }
  }

  if (tools.length) {
    aiDecided.push({
      id: "tools",
      label: "Tools selected",
      detail: tools.map((t) => t.tool).join(", "),
    });
  }

  const regRows: UserRegRow[] = buildRegistrationRows(
    results,
    users.map((u) => u.email || "").filter(Boolean)
  );
  for (const row of regRows) {
    if (row.ldap !== "not_run" || row.gac !== "not_run") {
      aiDecided.push({
        id: `reg-${row.email}`,
        label: "Registration result",
        detail: `${row.email}: LDAP ${regFlagLabel(row.ldap)} / GAC ${regFlagLabel(row.gac)} / ${combinedLabel(row.combined)}`,
      });
    }
    if (row.ldap === "unknown" || row.gac === "unknown") {
      const item = {
        id: `reg-unknown-${row.email}`,
        label: "Registration UNKNOWN",
        detail: row.email,
        why: "Source unavailable or unreadable — UNKNOWN is not NOT REGISTERED.",
      };
      if (surfaceDecisionIssues) needsOperator.push(item);
    }
  }

  if (rag.length) {
    const sources = rag
      .map((r) => (r.id ? `${r.source}:${r.id}` : r.source || "ref"))
      .join(", ");
    aiDecided.push({
      id: "rag",
      label: "RAG / template refs",
      detail: sources,
    });
  }

  if (draftTemplateId) {
    aiDecided.push({
      id: "draft-template",
      label: "Draft template suggested",
      detail: draftTemplateId,
    });
  }

  // Validation flags: only unresolved while decision approval is still open
  for (const f of flags) {
    const item = {
      id: `flag-${f.code || "review"}-${needsOperator.length}`,
      label: f.code || "review_flag",
      detail: f.message || "Flagged for review",
      why: whyForFlag(f.code, f.message),
    };
    if (surfaceDecisionIssues) {
      needsOperator.push(item);
    } else {
      aiDecided.push({
        id: item.id,
        label: `Gate reviewed: ${item.label}`,
        detail: item.detail,
      });
    }
  }

  if (surfaceDecisionIssues && analysis.needs_human_review && !flags.length) {
    needsOperator.push({
      id: "needs-review",
      label: "Human review required",
      detail: "needs_human_review=true",
      why: "Gates require operator confirmation before continuing.",
    });
  }

  if (
    analysis.ai_mode === "ollama_unavailable" ||
    analysis.ai_mode === "ollama_error" ||
    analysis.provider_error
  ) {
    needsOperator.push({
      id: "provider-error",
      label: "Ollama provider error",
      detail:
        analysis.provider_error ||
        "Ollama provider error — see provider_error on last_analysis",
      why: "Inference did not complete; do not treat results as successful live AI output.",
    });
  }

  // Pending approvals / workflow waits
  for (const a of approvals.filter((x) => x.status === "pending")) {
    const isDecision = a.approval_type.toLowerCase().includes("decision");
    const isEmail = a.approval_type.toLowerCase().includes("email");
    needsOperator.push({
      id: `approval-${a.id}`,
      label: isEmail
        ? "Pending email approval"
        : isDecision
          ? "Pending decision approval"
          : `Pending ${a.approval_type} approval`,
      detail: a.summary,
      why: isEmail
        ? "Outbound email is blocked until an operator approves this exact draft."
        : "AI could not auto-complete the decision path — approve, reject, or replan.",
    });
  }

  if (state === "AWAITING_DECISION_APPROVAL") {
    if (!needsOperator.some((i) => i.id.startsWith("approval-"))) {
      needsOperator.push({
        id: "state-decision",
        label: "Awaiting decision approval",
        detail: state,
        why: "Workflow paused for operator decision.",
      });
    }
  }
  if (state === "AWAITING_EMAIL_APPROVAL") {
    if (!needsOperator.some((i) => i.label.includes("email approval"))) {
      needsOperator.push({
        id: "state-email",
        label: "Awaiting email approval",
        detail: state,
        why: "Workflow paused until email send is approved.",
      });
    }
  }

  const hasPendingAction =
    needsOperator.length > 0 || decisionPending || emailPending;

  return { aiDecided, needsOperator, hasPendingAction };
}
