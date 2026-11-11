type RagRef = {
  source?: string;
  id?: string | null;
  text?: string;
};

export function RagReferenceViewer({ refs }: { refs: RagRef[] }) {
  if (!refs.length) {
    return (
      <p className="text-xs text-[color:var(--text-muted)]">
        No RAG references retrieved (viewer shows only real retrieval).
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="ops-table w-full text-left">
        <thead>
          <tr>
            <th>Source</th>
            <th>Id</th>
            <th>Excerpt</th>
          </tr>
        </thead>
        <tbody>
          {refs.map((r, i) => (
            <tr key={`${r.source}-${r.id}-${i}`}>
              <td>
                <span className="status-badge badge-partial">
                  {r.source || "unknown"}
                </span>
              </td>
              <td className="font-mono text-xs">{r.id != null && r.id !== "" ? r.id : "—"}</td>
              <td className="max-w-xl whitespace-pre-wrap text-xs leading-snug text-[color:var(--text)]">
                {r.text || "(empty)"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
