"use client";

import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { api, EvalSummary } from "@/lib/api";

export default function EvaluationsPage() {
  const [data, setData] = useState<EvalSummary | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .latestEval()
      .then(setData)
      .catch(() => setData(null));
  }, []);

  return (
    <Shell title="Evaluation Dashboard">
      <p className="mb-4 max-w-2xl text-sm text-mist/75">
        Synthetic evaluation runner. Metrics below are from the local dataset only —
        not marketed as production accuracy targets.
      </p>
      <button
        className="bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            setData(await api.runEval());
          } catch (e) {
            setError(e instanceof Error ? e.message : "Eval failed");
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Running…" : "Run synthetic evaluation"}
      </button>
      {error ? <p className="mt-3 text-sm text-warn">{error}</p> : null}
      {data ? (
        <div className="mt-6 space-y-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <Metric label="Total" value={String(data.total)} />
            <Metric label="Passed" value={String(data.passed)} />
            <Metric label="Failed" value={String(data.failed)} />
            <Metric
              label="Tool select hit-rate"
              value={`${Math.round((data.metrics.tool_selection_hit_rate || 0) * 100)}%`}
            />
          </div>
          <p className="text-xs text-mist/60">{data.note}</p>
          <div className="overflow-hidden border border-[var(--line)]">
            <table className="w-full text-left text-sm">
              <thead className="bg-panel/80 text-mist/70">
                <tr>
                  <th className="px-3 py-2">Case</th>
                  <th className="px-3 py-2">OK</th>
                  <th className="px-3 py-2">Detail</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r, i) => (
                  <tr key={i} className="border-t border-[var(--line)]">
                    <td className="px-3 py-2">{String(r.id)}</td>
                    <td className="px-3 py-2">{r.ok ? "pass" : "fail"}</td>
                    <td className="px-3 py-2 text-mist/80">{String(r.detail || "")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </Shell>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="border border-[var(--line)] bg-panel/40 p-3">
      <p className="text-xs text-mist/60">{label}</p>
      <p className="text-xl text-white">{value}</p>
    </div>
  );
}
