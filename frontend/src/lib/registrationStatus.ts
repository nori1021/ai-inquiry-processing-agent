/** Parse real tool_results into LDAP/GAC registration views. Never invents hits. */

export type RegFlag = "yes" | "no" | "unknown" | "not_run";

export type CombinedState =
  | "LDAP_AND_GAC"
  | "LDAP_ONLY"
  | "GAC_ONLY"
  | "NEITHER"
  | "UNKNOWN"
  | "INCOMPLETE";

export type ToolResultLike = {
  tool: string;
  arguments?: Record<string, unknown>;
  ok?: boolean;
  result?: unknown;
  error?: string | null;
  status?: string;
};

export type UserRegRow = {
  email: string;
  ldap: RegFlag;
  gac: RegFlag;
  combined: CombinedState;
  ldapDetail?: string;
  gacDetail?: string;
};

export function normalizeRegFlag(raw: unknown): RegFlag {
  if (raw == null) return "unknown";
  const s = String(raw).trim().toLowerCase();
  if (s === "yes" || s === "found" || s === "registered") return "yes";
  if (
    s === "no" ||
    s === "not_registered" ||
    s === "not-registered" ||
    s === "missing"
  ) {
    return "no";
  }
  if (s === "unknown" || s === "error" || s === "unavailable") return "unknown";
  return "unknown";
}

export function flagFromLookupStatus(status: unknown): RegFlag {
  if (status == null) return "unknown";
  const s = String(status).trim().toUpperCase();
  if (s === "FOUND") return "yes";
  if (s === "NOT_REGISTERED") return "no";
  // UNKNOWN and anything else must not look like NOT_REGISTERED
  return "unknown";
}

export function combineFlags(ldap: RegFlag, gac: RegFlag): CombinedState {
  if (ldap === "not_run" || gac === "not_run") return "INCOMPLETE";
  if (ldap === "unknown" || gac === "unknown") return "UNKNOWN";
  if (ldap === "yes" && gac === "yes") return "LDAP_AND_GAC";
  if (ldap === "yes" && gac === "no") return "LDAP_ONLY";
  if (ldap === "no" && gac === "yes") return "GAC_ONLY";
  if (ldap === "no" && gac === "no") return "NEITHER";
  return "UNKNOWN";
}

function emailFromTool(tr: ToolResultLike): string | null {
  const args = tr.arguments || {};
  const result =
    tr.result && typeof tr.result === "object"
      ? (tr.result as Record<string, unknown>)
      : {};
  const candidates = [
    args.email,
    result.query_email,
    result.query,
    result.email,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.includes("@")) {
      return c.trim().toLowerCase();
    }
  }
  return null;
}

function readLdapFlag(tr: ToolResultLike): RegFlag | null {
  if (!tr.ok && tr.status === "error") return "unknown";
  const result =
    tr.result && typeof tr.result === "object"
      ? (tr.result as Record<string, unknown>)
      : {};
  if (tr.tool === "check_ldap_registration") {
    return normalizeRegFlag(result.registered);
  }
  if (tr.tool === "lookup_ldap_user" || tr.tool === "get_ldap_user") {
    return flagFromLookupStatus(result.status);
  }
  return null;
}

function readGacFlag(tr: ToolResultLike): RegFlag | null {
  if (!tr.ok && tr.status === "error") return "unknown";
  const result =
    tr.result && typeof tr.result === "object"
      ? (tr.result as Record<string, unknown>)
      : {};
  if (tr.tool === "check_gac_registration") {
    return normalizeRegFlag(result.registered);
  }
  if (tr.tool === "lookup_gac_user" || tr.tool === "get_gac_user") {
    return flagFromLookupStatus(result.status);
  }
  return null;
}

export function buildRegistrationRows(
  toolResults: ToolResultLike[],
  emailsHint: string[] = []
): UserRegRow[] {
  const map = new Map<
    string,
    {
      ldap: RegFlag;
      gac: RegFlag;
      combined?: CombinedState;
      ldapDetail?: string;
      gacDetail?: string;
    }
  >();

  const ensure = (email: string) => {
    if (!map.has(email)) {
      map.set(email, { ldap: "not_run", gac: "not_run" });
    }
    return map.get(email)!;
  };

  for (const hint of emailsHint) {
    if (hint && hint.includes("@")) ensure(hint.trim().toLowerCase());
  }

  for (const tr of toolResults) {
    if (tr.tool === "check_ldap_gac_registration") {
      const email = emailFromTool(tr);
      if (!email) continue;
      const row = ensure(email);
      const result =
        tr.result && typeof tr.result === "object"
          ? (tr.result as Record<string, unknown>)
          : {};
      const ldap = result.ldap as Record<string, unknown> | undefined;
      const gac = result.gac as Record<string, unknown> | undefined;
      if (ldap) row.ldap = normalizeRegFlag(ldap.registered);
      if (gac) row.gac = normalizeRegFlag(gac.registered);
      const cs = result.combined_state;
      if (typeof cs === "string" && cs) {
        row.combined = cs as CombinedState;
      }
      if (typeof result.detail === "string") {
        row.ldapDetail = result.detail;
      }
      continue;
    }

    const ldap = readLdapFlag(tr);
    const gac = readGacFlag(tr);
    const email = emailFromTool(tr);
    if (!email) continue;
    const row = ensure(email);
    const result =
      tr.result && typeof tr.result === "object"
        ? (tr.result as Record<string, unknown>)
        : {};
    if (ldap != null) {
      row.ldap = ldap;
      if (typeof result.detail === "string") row.ldapDetail = result.detail;
    }
    if (gac != null) {
      row.gac = gac;
      if (typeof result.detail === "string") row.gacDetail = result.detail;
    }
  }

  return Array.from(map.entries()).map(([email, v]) => ({
    email,
    ldap: v.ldap,
    gac: v.gac,
    combined: v.combined || combineFlags(v.ldap, v.gac),
    ldapDetail: v.ldapDetail,
    gacDetail: v.gacDetail,
  }));
}

export function regFlagLabel(flag: RegFlag): string {
  switch (flag) {
    case "yes":
      return "REGISTERED";
    case "no":
      return "NOT REGISTERED";
    case "unknown":
      return "UNKNOWN";
    case "not_run":
      return "NOT RUN";
  }
}

export function combinedLabel(state: CombinedState): string {
  switch (state) {
    case "LDAP_AND_GAC":
      return "BOTH (LDAP+GAC)";
    case "LDAP_ONLY":
      return "LDAP ONLY";
    case "GAC_ONLY":
      return "GAC ONLY";
    case "NEITHER":
      return "NEITHER";
    case "UNKNOWN":
      return "UNKNOWN";
    case "INCOMPLETE":
      return "INCOMPLETE";
  }
}
