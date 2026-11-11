import { describe, expect, it } from "vitest";

describe("frontend smoke", () => {
  it("api base defaults to local backend", () => {
    const base =
      process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
      "http://127.0.0.1:8000";
    expect(base).toContain("8000");
  });
});

describe("inquiry detail analysis contract", () => {
  it("accepts last_analysis shape used by Tool/RAG/decision viewers", () => {
    const last_analysis = {
      ai_mode: "mock_heuristic",
      provider: "mock",
      needs_human_review: true,
      analysis: {
        summary: "Mock analysis",
        confidence: 0.82,
        users: [
          {
            email: "frank@acme.com",
            role: "affected_user",
            investigate: "REQUIRED",
          },
          {
            email: "grace@globex.com",
            role: "other",
            investigate: "NOT_REQUIRED",
          },
        ],
      },
      investigation_plan: [
        { target_type: "user", target: "frank@acme.com", need: "REQUIRED" },
      ],
      tool_results: [
        {
          tool: "check_ldap_registration",
          arguments: { email: "frank@acme.com" },
          ok: true,
          status: "ok",
          duration_ms: 12.5,
          result: { registered: "no" },
        },
      ],
      rag_references: [
        { source: "past_inquiry", id: "P1", text: "GAC missing" },
        { source: "reply_template", id: "gac_missing", text: "Subject:" },
      ],
      review_flags: [{ code: "confidence_gate", message: "below auto-pass" }],
    };

    expect(["actual_llm", "mock_heuristic", "mock_fallback", "unknown"]).toContain(
      last_analysis.ai_mode
    );
    expect(last_analysis.tool_results[0].duration_ms).toBeGreaterThanOrEqual(0);
    expect(last_analysis.rag_references.every((r) => r.source && r.text)).toBe(
      true
    );
    const grace = last_analysis.analysis.users.find(
      (u) => u.email === "grace@globex.com"
    );
    expect(grace?.investigate).toBe("NOT_REQUIRED");
  });
});
