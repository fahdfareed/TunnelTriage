import { useState } from "react";
import Markdown from "react-markdown";
import { api } from "../api";
import type { Memo, Plan } from "../types";

export function MemoPanel({ plan }: { plan: Plan | null }) {
  const [memo, setMemo] = useState<Memo | null>(null);
  const [busy, setBusy] = useState(false);

  const generate = async () => {
    if (!plan) return;
    setBusy(true);
    const m = await api.memo(plan.plan_id);
    setMemo(m);
    setBusy(false);
  };

  return (
    <div>
      <button onClick={generate} disabled={!plan || busy}>
        {busy ? "Generating…" : "Generate memo"}
      </button>{" "}
      {memo && (
        <>
          <span className="chip">
            {memo.source === "llm" ? "AI-written, numbers verified" : "Template"}
          </span>{" "}
          <button
            className="secondary"
            onClick={() => navigator.clipboard.writeText(memo.markdown)}
          >
            Copy
          </button>
        </>
      )}
      {memo?.warnings.map((w) => (
        <div key={w} className="banner info" style={{ marginTop: 8 }}>{w}</div>
      ))}
      {memo && (
        <div className="memo" style={{ marginTop: 10 }}>
          <Markdown>{memo.markdown}</Markdown>
        </div>
      )}
    </div>
  );
}
