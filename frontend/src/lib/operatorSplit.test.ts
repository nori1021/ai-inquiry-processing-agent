import { describe, expect, it } from "vitest";
import { buildOperatorSplit, isRegistrationRelevant } from "./operatorSplit";

describe("buildOperatorSplit", () => {
  it("separates AI decided from needs-operator with why text", () => {
    const split = buildOperatorSplit({
      state: "AWAITING_DECISION_APPROVAL",
      approvals: [
        {
          id: 1,
          approval_type: "decision",
          status: "pending",
          summary: "Decision approval required: confidence_gate",
        },
      ],
      analysis: {
        ai_mode: "mock_heuristic",
        needs_human_review: true,
        analysis: {
          category: "it_helpdesk",
          intent: "gac_registration",
          summary: "Mock analysis",
          confidence: 0.82,
          users: [
            {
              email: "frank@acme.com",
              role: "affected_user",
              investigate: "REQUIRED",
            },
            {
              email: "mystery@acme.com",
              role: "other",
              investigate: "UNCERTAIN",
              reason: "role unclear",
            },
            {
              email: "grace@globex.com",
              role: "other",
              investigate: "NOT_REQUIRED",
            },
          ],
        },
        selected_tools: [{ tool: "check_ldap_registration" }],
        tool_results: [
          {
            tool: "check_ldap_registration",
            arguments: { email: "frank@acme.com" },
            ok: true,
            result: { registered: "no", query_email: "frank@acme.com" },
          },
          {
            tool: "check_gac_registration",
            arguments: { email: "frank@acme.com" },
            ok: true,
            result: { registered: "yes", query_email: "frank@acme.com" },
          },
        ],
        review_flags: [
          {
            code: "confidence_gate",
            message: "confidence 0.82 <= 0.99",
          },
          {
            code: "prior_password_reset_failed",
            message:
              "User reports prior reset failed; do not re-send standard reset steps.",
          },
        ],
        rag_references: [{ source: "reply_template", id: "gac_missing" }],
      },
      draftTemplateId: "gac_missing",
    });

    expect(split.hasPendingAction).toBe(true);
    expect(split.aiDecided.some((i) => i.label === "Category")).toBe(true);
    expect(split.aiDecided.some((i) => i.detail.includes("GAC ONLY"))).toBe(
      true
    );
    expect(
      split.aiDecided.some((i) => i.detail.includes("grace@globex.com"))
    ).toBe(true);

    const uncertain = split.needsOperator.find((i) =>
      i.label.includes("UNCERTAIN")
    );
    expect(uncertain?.why).toMatch(/role unclear|could not decide/i);

    const gate = split.needsOperator.find((i) => i.label === "confidence_gate");
    expect(gate?.why).toMatch(/auto-pass/i);

    const prior = split.needsOperator.find(
      (i) => i.label === "prior_password_reset_failed"
    );
    expect(prior?.why).toMatch(/do not re-send standard reset steps/i);

    const pending = split.needsOperator.find((i) =>
      i.label.includes("decision approval")
    );
    expect(pending?.why).toMatch(/approve|reject|replan/i);
  });

  it("marks registration snapshot relevant for decision awaits", () => {
    expect(
      isRegistrationRelevant({
        state: "AWAITING_DECISION_APPROVAL",
        toolNames: ["check_ldap_registration"],
        needsItems: [],
      })
    ).toBe(true);
    expect(
      isRegistrationRelevant({
        state: "COMPLETED",
        toolNames: ["search_past_inquiries"],
        needsItems: [],
      })
    ).toBe(false);
  });

  it("does not invent registration when tools did not run", () => {
    const split = buildOperatorSplit({
      state: "ANALYZING",
      approvals: [],
      analysis: {
        analysis: {
          users: [
            {
              email: "alice@acme.com",
              role: "requester",
              investigate: "REQUIRED",
            },
          ],
        },
        tool_results: [],
      },
    });
    expect(split.aiDecided.some((i) => i.label === "Registration result")).toBe(
      false
    );
  });
});
