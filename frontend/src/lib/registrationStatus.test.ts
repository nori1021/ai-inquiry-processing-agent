import { describe, expect, it } from "vitest";
import {
  buildRegistrationRows,
  combineFlags,
  flagFromLookupStatus,
  normalizeRegFlag,
  regFlagLabel,
} from "./registrationStatus";

describe("registrationStatus mapping", () => {
  it("never maps unknown lookup to not-registered", () => {
    expect(flagFromLookupStatus("UNKNOWN")).toBe("unknown");
    expect(flagFromLookupStatus("NOT_REGISTERED")).toBe("no");
    expect(flagFromLookupStatus("FOUND")).toBe("yes");
    expect(normalizeRegFlag("unknown")).toBe("unknown");
    expect(regFlagLabel("unknown")).toBe("UNKNOWN");
    expect(regFlagLabel("no")).toBe("NOT REGISTERED");
  });

  it("combines LDAP/GAC flags including UNKNOWN vs NEITHER", () => {
    expect(combineFlags("yes", "yes")).toBe("LDAP_AND_GAC");
    expect(combineFlags("yes", "no")).toBe("LDAP_ONLY");
    expect(combineFlags("no", "yes")).toBe("GAC_ONLY");
    expect(combineFlags("no", "no")).toBe("NEITHER");
    expect(combineFlags("unknown", "no")).toBe("UNKNOWN");
    expect(combineFlags("not_run", "yes")).toBe("INCOMPLETE");
  });

  it("builds rows only from real tool_results", () => {
    const rows = buildRegistrationRows(
      [
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
      ["frank@acme.com", "grace@globex.com"]
    );
    const frank = rows.find((r) => r.email === "frank@acme.com");
    const grace = rows.find((r) => r.email === "grace@globex.com");
    expect(frank?.combined).toBe("GAC_ONLY");
    expect(grace?.ldap).toBe("not_run");
    expect(grace?.gac).toBe("not_run");
  });
});
