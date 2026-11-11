import {
  UserRegRow,
  buildRegistrationRows,
  ToolResultLike,
} from "@/lib/registrationStatus";
import {
  CombinedBadge,
  InvestigateBadge,
  RegFlagBadge,
} from "@/components/StatusBadge";

type User = {
  email?: string | null;
  role?: string;
  investigate?: string;
  reason?: string;
};

type Props = {
  users: User[];
  toolResults: ToolResultLike[];
};

export function RegistrationSummary({ users, toolResults }: Props) {
  const hints = users
    .map((u) => u.email)
    .filter((e): e is string => Boolean(e && e.includes("@")));
  const rows: UserRegRow[] = buildRegistrationRows(toolResults, hints);
  const byEmail = new Map(users.map((u) => [u.email?.toLowerCase() || "", u]));

  // Prefer users list order; append any tool-only emails
  const orderedEmails: string[] = [];
  for (const u of users) {
    if (u.email) orderedEmails.push(u.email.toLowerCase());
  }
  for (const r of rows) {
    if (!orderedEmails.includes(r.email)) orderedEmails.push(r.email);
  }

  const rowMap = new Map(rows.map((r) => [r.email, r]));

  if (!orderedEmails.length) {
    return (
      <p className="text-xs text-mist/70">
        No users extracted and no registration tool results yet.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="ops-table w-full text-left text-sm">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Investigate</th>
            <th>LDAP</th>
            <th>GAC</th>
            <th>Combined</th>
          </tr>
        </thead>
        <tbody>
          {orderedEmails.map((email) => {
            const user = byEmail.get(email);
            const reg = rowMap.get(email);
            const need = user?.investigate;
            const dim = need === "NOT_REQUIRED";
            return (
              <tr
                key={email}
                className={dim ? "opacity-60" : undefined}
                title={user?.reason || undefined}
              >
                <td className="font-mono text-xs text-white">{email}</td>
                <td className="text-xs text-mist/80">{user?.role || "—"}</td>
                <td>
                  <InvestigateBadge need={need} />
                </td>
                <td>
                  <RegFlagBadge flag={reg?.ldap || "not_run"} source="LDAP" />
                </td>
                <td>
                  <RegFlagBadge flag={reg?.gac || "not_run"} source="GAC" />
                </td>
                <td>
                  <CombinedBadge state={reg?.combined || "INCOMPLETE"} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-mist/55">
        UNKNOWN means source error or unreadable data — never treated as NOT
        REGISTERED. Rows marked NOT_REQUIRED are shown for context only.
      </p>
    </div>
  );
}
