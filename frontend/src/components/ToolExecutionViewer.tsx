type ToolResult = {
  tool: string;
  arguments?: Record<string, unknown>;
  ok?: boolean;
  result?: unknown;
  error?: string | null;
  provider?: string;
  duration_ms?: number;
  status?: string;
};

function previewResult(result: unknown): string {
  if (result == null) return "—";
  try {
    const s = JSON.stringify(result);
    return s.length > 180 ? `${s.slice(0, 180)}…` : s;
  } catch {
    return String(result);
  }
}

export function ToolExecutionViewer({ results }: { results: ToolResult[] }) {
  if (!results.length) {
    return (
      <p className="text-xs text-[color:var(--text-muted)]">
        No tool executions recorded (none fabricated).
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="ops-table w-full text-left">
        <thead>
          <tr>
            <th>Tool</th>
            <th>Status</th>
            <th>ms</th>
            <th>Args</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r, i) => {
            const ok = r.status === "ok" || r.ok;
            return (
              <tr key={`${r.tool}-${i}`}>
                <td className="font-mono text-xs text-white">
                  {r.tool}
                  {r.provider ? (
                    <span className="mt-0.5 block text-[10px] text-[color:var(--text-muted)]">
                      {r.provider}
                    </span>
                  ) : null}
                </td>
                <td>
                  <span
                    className={`status-badge ${ok ? "badge-found" : "badge-unknown"}`}
                  >
                    {r.status || (ok ? "ok" : "error")}
                  </span>
                </td>
                <td className="font-mono text-xs">
                  {typeof r.duration_ms === "number"
                    ? r.duration_ms.toFixed(0)
                    : "—"}
                </td>
                <td className="max-w-[12rem] truncate font-mono text-[10px] text-[color:var(--text-muted)]"
                  title={JSON.stringify(r.arguments ?? {})}
                >
                  {JSON.stringify(r.arguments ?? {})}
                </td>
                <td
                  className="max-w-[16rem] truncate font-mono text-[10px]"
                  title={
                    r.error ||
                    (typeof r.result === "string"
                      ? r.result
                      : JSON.stringify(r.result ?? null))
                  }
                >
                  {r.error ? (
                    <span className="text-[color:var(--unknown-fg)]">{r.error}</span>
                  ) : (
                    previewResult(r.result)
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
