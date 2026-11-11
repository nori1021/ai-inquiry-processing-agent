type Props = {
  aiMode?: string;
  provider?: string;
  providerError?: string | null;
  providerStatus?: string;
};

const LABELS: Record<string, { label: string; className: string }> = {
  actual_llm: {
    label: "OLLAMA (Actual AI)",
    className: "badge-found",
  },
  mock_heuristic: {
    label: "MOCK HEURISTIC",
    className: "badge-warn",
  },
  mock_fallback: {
    label: "MOCK FALLBACK (explicit escape hatch)",
    className: "badge-warn",
  },
  ollama_unavailable: {
    label: "OLLAMA UNAVAILABLE",
    className: "badge-unknown",
  },
  ollama_error: {
    label: "OLLAMA ERROR",
    className: "badge-unknown",
  },
  unknown: {
    label: "AI MODE UNKNOWN",
    className: "badge-idle",
  },
};

export function AiModeBadge({
  aiMode,
  provider,
  providerError,
  providerStatus,
}: Props) {
  const key = aiMode || "unknown";
  const meta = LABELS[key] || LABELS.unknown;
  return (
    <span
      className={`status-badge ${meta.className}`}
      title={
        [provider ? `provider=${provider}` : "", providerStatus, providerError]
          .filter(Boolean)
          .join(" | ") || undefined
      }
    >
      {meta.label}
      {provider ? (
        <span className="ml-1 font-mono text-[10px] font-normal normal-case opacity-80">
          {provider}
        </span>
      ) : null}
    </span>
  );
}
