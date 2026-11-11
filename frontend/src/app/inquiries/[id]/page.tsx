"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { Shell } from "@/components/Shell";
import { AiModeBadge } from "@/components/AiModeBadge";
import { ToolExecutionViewer } from "@/components/ToolExecutionViewer";
import { RagReferenceViewer } from "@/components/RagReferenceViewer";
import { StructuredDecisionViewer } from "@/components/StructuredDecisionViewer";
import { RegistrationSummary } from "@/components/RegistrationSummary";
import { AiDecidedPanel } from "@/components/OperatorActionPanel";
import { CollapsibleSection } from "@/components/CollapsibleSection";
import { WorkflowProgress } from "@/components/WorkflowProgress";
import {
  ApprovalStateBadge,
  WorkflowStateBadge,
} from "@/components/StatusBadge";
import {
  buildOperatorSplit,
  isRegistrationRelevant,
} from "@/lib/operatorSplit";
import { api, EmailDraft, Workflow } from "@/lib/api";

type AnalysisPayload = {
  analysis?: {
    summary?: string;
    confidence?: number | null;
    category?: string;
    users?: Array<{
      email?: string | null;
      role?: string;
      reason?: string;
      investigate?: string;
    }>;
    intent?: string;
  };
  investigation_plan?: Array<{
    target_type?: string;
    target?: string;
    need?: string;
    role?: string | null;
    reason?: string;
  }>;
  selected_tools?: Array<{ tool: string; arguments?: Record<string, unknown> }>;
  tool_results?: Array<{
    tool: string;
    arguments?: Record<string, unknown>;
    ok?: boolean;
    result?: unknown;
    error?: string | null;
    provider?: string;
    duration_ms?: number;
    status?: string;
  }>;
  rag_references?: Array<{ source?: string; id?: string | null; text?: string }>;
  review_flags?: Array<{ code?: string; message?: string; severity?: string }>;
  needs_human_review?: boolean;
  ai_mode?: string;
  provider?: string;
  provider_status?: string;
  provider_error?: string | null;
};

export default function InquiryDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const [wf, setWf] = useState<Workflow | null>(null);
  const [draft, setDraft] = useState<EmailDraft | null>(null);
  const [draftBody, setDraftBody] = useState("");
  const [error, setError] = useState("");
  const [note, setNote] = useState("Approved from UI");
  const [busyId, setBusyId] = useState<number | null>(null);

  async function reload() {
    const w = await api.getWorkflow(id);
    setWf(w);
    try {
      const d = await api.getDraft(id);
      setDraft(d);
      setDraftBody(d.body);
    } catch {
      setDraft(null);
    }
  }

  useEffect(() => {
    reload().catch((e) => setError(e.message));
  }, [id]);

  const analysis = (wf?.context?.last_analysis || {}) as AnalysisPayload;
  const inner = analysis.analysis || {};
  const pending = wf?.approvals.filter((a) => a.status === "pending") || [];
  const resolved = wf?.approvals.filter((a) => a.status !== "pending") || [];

  const split = useMemo(() => {
    if (!wf) {
      return { aiDecided: [], needsOperator: [], hasPendingAction: false };
    }
    return buildOperatorSplit({
      state: wf.state,
      approvals: wf.approvals,
      analysis,
      draftTemplateId: draft?.template_id,
    });
  }, [wf, analysis, draft?.template_id]);

  const showRegistration =
    !!wf &&
    isRegistrationRelevant({
      state: wf.state,
      toolNames: (analysis.tool_results || []).map((t) => t.tool),
      needsItems: split.needsOperator,
    });

  async function decide(approvalId: number, decision: "approved" | "rejected") {
    setBusyId(approvalId);
    try {
      await api.decide(id, approvalId, { decision, note });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Decision failed");
    } finally {
      setBusyId(null);
    }
  }

  if (!wf) {
    return (
      <Shell title={`Inquiry #${id}`}>
        <p className="text-base">{error || "Loading…"}</p>
      </Shell>
    );
  }

  return (
    <Shell title={`Inquiry #${wf.id}`}>
      {/* Compact identity strip */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <h2 className="text-xl font-semibold text-white md:text-2xl">
          {wf.subject || "Untitled"}
        </h2>
        <WorkflowStateBadge state={wf.state} />
        <AiModeBadge
          aiMode={analysis.ai_mode}
          provider={analysis.provider}
          providerStatus={analysis.provider_status}
          providerError={analysis.provider_error}
        />
        <span className="text-sm text-[color:var(--text-muted)]">
          From {wf.from_email || "—"}
        </span>
      </div>

      {analysis.provider_error ? (
        <div className="ops-panel mb-4 border-[color:var(--unknown-border)]">
          <p className="text-sm font-semibold uppercase tracking-wide text-[color:var(--unknown-fg)]">
            Provider error (not mocked silently)
          </p>
          <p className="mt-1 text-base text-white">{analysis.provider_error}</p>
          <p className="mt-1 text-sm text-[color:var(--text-muted)]">
            status={analysis.provider_status || "error"} · Check
            /api/v1/provider and Ollama (`ollama list`, base URL).
          </p>
        </div>
      ) : null}

      <div className="mb-4">
        <WorkflowProgress state={wf.state} />
      </div>

      {/* PRIMARY: what to verify + actions */}
      <section
        className="ops-panel mb-4 border-[color:var(--action-border)] pending-row"
        aria-label="What to verify and approve"
      >
        <p className="text-sm font-semibold uppercase tracking-[0.08em] text-[color:var(--action-fg)]">
          What to verify
        </p>
        <h3 className="mt-1 text-xl font-semibold text-white">
          {pending.length
            ? "Review these points, then Approve or Reject"
            : split.needsOperator.length
              ? "Items still needing operator judgment"
              : "No pending operator action"}
        </h3>

        {split.needsOperator.length ? (
          <ol className="mt-4 list-decimal space-y-3 pl-5">
            {split.needsOperator.map((item) => (
              <li key={item.id} className="text-base leading-snug text-white">
                <span className="font-semibold">{item.label}</span>
                <span className="text-[color:var(--text)]"> — {item.detail}</span>
                {item.why ? (
                  <p className="mt-1 text-sm font-medium text-[color:var(--action-fg)]">
                    Why: {item.why}
                  </p>
                ) : null}
              </li>
            ))}
          </ol>
        ) : (
          <p className="mt-3 text-base text-[color:var(--text-muted)]">
            Nothing is blocked on human judgment right now.
          </p>
        )}

        {showRegistration ? (
          <div className="mt-5 border-t border-[color:var(--line)] pt-4">
            <p className="mb-2 text-base font-semibold text-white">
              LDAP / GAC status (for this decision)
            </p>
            <RegistrationSummary
              users={inner.users || []}
              toolResults={analysis.tool_results || []}
            />
          </div>
        ) : null}

        {pending.length && draft && wf.state.includes("EMAIL") ? (
          <div className="mt-5 border-t border-[color:var(--line)] pt-4">
            <p className="mb-1 text-base font-semibold text-white">
              Email draft to approve
            </p>
            <p className="text-sm text-[color:var(--text-muted)]">
              To: {draft.to_email} · template: {draft.template_id}
            </p>
            <p className="mt-2 text-base font-medium text-white">{draft.subject}</p>
            <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap border border-[color:var(--line)] bg-[color:var(--bg0)] p-3 text-sm leading-relaxed text-[color:var(--text)]">
              {draft.body}
            </pre>
          </div>
        ) : null}

        {pending.length ? (
          <div className="mt-6 border-t border-[color:var(--action-border)] pt-4">
            <label className="block text-sm font-semibold text-white">
              Decision note
            </label>
            <input
              className="mt-2 w-full border border-[color:var(--line-strong)] bg-[color:var(--bg0)] px-3 py-2.5 text-base text-[color:var(--text)]"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div className="mt-4 space-y-3">
              {pending.map((a) => (
                <div
                  key={a.id}
                  className="flex flex-col gap-3 border border-[color:var(--action-border)] bg-[color:var(--bg0)] p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <ApprovalStateBadge
                      status={a.status}
                      type={a.approval_type}
                    />
                    <p className="mt-2 text-base text-[color:var(--text)]">
                      {a.summary}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      className="min-w-[8rem] bg-[color:var(--accent)] px-5 py-3 text-base font-bold text-[color:var(--bg0)] disabled:opacity-50"
                      disabled={busyId === a.id}
                      onClick={() => decide(a.id, "approved")}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="min-w-[8rem] border-2 border-[color:var(--missing-border)] px-5 py-3 text-base font-bold text-[color:var(--missing-fg)] disabled:opacity-50"
                      disabled={busyId === a.id}
                      onClick={() => decide(a.id, "rejected")}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-sm text-[color:var(--text-muted)]">
              Click Approve or Reject above. Email send stays blocked until email
              approval is granted.
            </p>
          </div>
        ) : null}
      </section>

      {/* Short inquiry context — open by default (needed to verify) */}
      <div className="mb-4">
        <CollapsibleSection
          title="Inquiry message"
          subtitle="Original request text"
          defaultOpen
        >
          <p className="whitespace-pre-wrap text-base leading-relaxed text-[color:var(--text)]">
            {wf.body}
          </p>
        </CollapsibleSection>
      </div>

      {/* Email draft editor — open when drafting / awaiting email */}
      {draft ? (
        <div className="mb-4">
          <CollapsibleSection
            title={`Email draft (v${draft.version}${draft.sent ? ", sent" : ""})`}
            subtitle={
              draft.sent
                ? "Already sent via mock provider"
                : "Edit if needed before email approval"
            }
            defaultOpen={
              !draft.sent &&
              (wf.state.includes("EMAIL") || wf.state.includes("DRAFT"))
            }
          >
            <p className="text-sm text-[color:var(--text-muted)]">
              To: {draft.to_email} · template: {draft.template_id}
            </p>
            <p className="mt-2 text-base font-semibold text-white">
              {draft.subject}
            </p>
            <textarea
              className="mt-2 min-h-36 w-full border border-[color:var(--line)] bg-[color:var(--bg0)] px-3 py-2 text-base leading-relaxed text-[color:var(--text)]"
              value={draftBody}
              onChange={(e) => setDraftBody(e.target.value)}
              disabled={draft.sent}
            />
            <button
              type="button"
              className="mt-3 border border-[color:var(--line-strong)] px-4 py-2 text-base font-semibold hover:border-[color:var(--accent)]"
              disabled={draft.sent}
              onClick={async () => {
                await api.updateDraft(id, { body: draftBody });
                await api.submitDraft(id);
                await reload();
              }}
            >
              Save edit (invalidates approval)
            </button>
          </CollapsibleSection>
        </div>
      ) : null}

      {/* Collapsed internals — processing evidence */}
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-[color:var(--text-muted)]">
          Internal processing (collapsed)
        </p>

        <CollapsibleSection
          title="AI decided"
          subtitle={`${split.aiDecided.length} recorded decisions`}
          defaultOpen={false}
          tone="muted"
        >
          <AiDecidedPanel items={split.aiDecided} />
        </CollapsibleSection>

        <CollapsibleSection
          title="Structured AI detail"
          subtitle="Users, plan, validation flags"
          defaultOpen={false}
          tone="muted"
        >
          <StructuredDecisionViewer
            users={inner.users || []}
            plan={analysis.investigation_plan || []}
            flags={analysis.review_flags || []}
            needsHumanReview={analysis.needs_human_review}
            confidence={inner.confidence}
            summary={inner.summary}
          />
        </CollapsibleSection>

        <CollapsibleSection
          title="Tool executions"
          subtitle={`${(analysis.tool_results || []).length} real registry runs`}
          defaultOpen={false}
          tone="muted"
        >
          <ToolExecutionViewer results={analysis.tool_results || []} />
        </CollapsibleSection>

        <CollapsibleSection
          title="RAG references"
          subtitle={`${(analysis.rag_references || []).length} retrieved refs`}
          defaultOpen={false}
          tone="muted"
        >
          <RagReferenceViewer refs={analysis.rag_references || []} />
        </CollapsibleSection>

        <CollapsibleSection
          title="Workflow timeline"
          subtitle={`${wf.transitions.length} transitions`}
          defaultOpen={false}
          tone="muted"
        >
          <ol className="space-y-2 text-base">
            {wf.transitions.map((t, i) => (
              <li
                key={`${t.from_state}-${t.to_state}-${i}`}
                className="flex flex-wrap gap-2"
              >
                <span className="font-mono text-sm text-[color:var(--accent)]">
                  {t.from_state} → {t.to_state}
                </span>
                <span className="text-[color:var(--text-muted)]">{t.reason}</span>
              </li>
            ))}
          </ol>
        </CollapsibleSection>

        <CollapsibleSection
          title="Resolved approvals"
          subtitle={
            resolved.length
              ? `${resolved.length} already decided`
              : "None yet"
          }
          defaultOpen={false}
          tone="muted"
        >
          <ul className="space-y-2">
            {resolved.map((a) => (
              <li key={a.id} className="border border-[color:var(--line)] p-3">
                <ApprovalStateBadge status={a.status} type={a.approval_type} />
                <p className="mt-2 text-base text-[color:var(--text)]">
                  {a.summary}
                </p>
              </li>
            ))}
            {!resolved.length ? (
              <li className="text-base text-[color:var(--text-muted)]">
                No resolved approvals
              </li>
            ) : null}
          </ul>
        </CollapsibleSection>
      </div>

      {error ? (
        <p className="mt-4 text-base text-[color:var(--unknown-fg)]">{error}</p>
      ) : null}
    </Shell>
  );
}
