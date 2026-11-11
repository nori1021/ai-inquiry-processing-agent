const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type Workflow = {
  id: number;
  state: string;
  subject: string;
  body: string;
  from_email?: string | null;
  context: Record<string, unknown>;
  approvals: Array<{
    id: number;
    approval_type: string;
    status: string;
    summary: string;
  }>;
  transitions: Array<{
    from_state: string;
    to_state: string;
    reason: string;
    created_at?: string;
  }>;
  email_requires_approval: boolean;
};

export type EmailDraft = {
  id: number;
  workflow_id: number;
  version: number;
  template_id: string;
  to_email: string;
  subject: string;
  body: string;
  content_hash: string;
  sent: boolean;
};

export type EvalSummary = {
  run_id: string;
  total: number;
  passed: number;
  failed: number;
  metrics: Record<string, number>;
  note: string;
  results: Array<Record<string, unknown>>;
};

export const api = {
  listWorkflows: () => request<Workflow[]>("/api/v1/workflows"),
  getWorkflow: (id: number) => request<Workflow>(`/api/v1/workflows/${id}`),
  createWorkflow: (body: {
    subject: string;
    body: string;
    from_email?: string;
    auto_advance?: boolean;
  }) =>
    request<Workflow>("/api/v1/workflows", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  decide: (
    workflowId: number,
    approvalId: number,
    payload: { decision: string; note?: string; request_replan?: boolean }
  ) =>
    request<Workflow>(
      `/api/v1/workflows/${workflowId}/approvals/${approvalId}/decide`,
      { method: "POST", body: JSON.stringify(payload) }
    ),
  getDraft: (workflowId: number) =>
    request<EmailDraft>(`/api/v1/emails/workflows/${workflowId}/draft`),
  updateDraft: (
    workflowId: number,
    payload: { subject?: string; body?: string; to_email?: string }
  ) =>
    request<EmailDraft>(`/api/v1/emails/workflows/${workflowId}/draft`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  submitDraft: (workflowId: number) =>
    request<Workflow>(
      `/api/v1/emails/workflows/${workflowId}/draft/submit-for-approval`,
      { method: "POST" }
    ),
  runEval: () =>
    request<EvalSummary>("/api/v1/evaluations/run", { method: "POST" }),
  latestEval: () => request<EvalSummary>("/api/v1/evaluations/latest"),
};
