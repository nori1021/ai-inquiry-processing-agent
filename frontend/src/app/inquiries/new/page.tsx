"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

export default function NewInquiryPage() {
  const router = useRouter();
  const [subject, setSubject] = useState("Password reset request");
  const [fromEmail, setFromEmail] = useState("manager@acme.com");
  const [body, setBody] = useState(
    "Please help alice@acme.com reset their password. Urgency: medium."
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const wf = await api.createWorkflow({
        subject,
        body,
        from_email: fromEmail,
        auto_advance: true,
      });
      router.push(`/inquiries/${wf.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
      setBusy(false);
    }
  }

  return (
    <Shell title="New Inquiry">
      <form onSubmit={onSubmit} className="max-w-2xl space-y-4">
        <label className="block text-sm">
          Subject
          <input
            className="mt-1 w-full border border-[var(--line)] bg-panel px-3 py-2"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
          />
        </label>
        <label className="block text-sm">
          From email
          <input
            className="mt-1 w-full border border-[var(--line)] bg-panel px-3 py-2"
            value={fromEmail}
            onChange={(e) => setFromEmail(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Body
          <textarea
            className="mt-1 min-h-40 w-full border border-[var(--line)] bg-panel px-3 py-2"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            required
          />
        </label>
        {error ? <p className="text-sm text-warn">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="bg-accent px-4 py-2 text-sm font-medium text-ink disabled:opacity-50"
        >
          {busy ? "Analyzing…" : "Submit inquiry"}
        </button>
        <p className="text-xs text-mist/60">
          No unrestricted send — workflow will stop for human approvals.
        </p>
      </form>
    </Shell>
  );
}
