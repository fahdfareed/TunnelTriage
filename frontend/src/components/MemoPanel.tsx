import { useRef, useState } from "react";
import Markdown from "react-markdown";
import { api } from "../api";
import type { Memo, Plan } from "../types";

export function MemoPanel({ plan }: { plan: Plan | null }) {
  const [memo, setMemo] = useState<Memo | null>(null);
  const [busy, setBusy] = useState(false);
  const memoRef = useRef<HTMLDivElement>(null);

  const generate = async () => {
    if (!plan) return;
    setBusy(true);
    const m = await api.memo(plan.plan_id);
    setMemo(m);
    setBusy(false);
  };

  // Open the rendered memo in a print window; the browser's print dialog offers
  // "Save as PDF". Keeps the markdown formatting without adding a PDF dependency.
  const downloadPdf = () => {
    const html = memoRef.current?.innerHTML;
    if (!html) return;
    const w = window.open("", "_blank", "width=800,height=1000");
    if (!w) return;
    w.document.write(`<!doctype html>
<html>
  <head>
    <title>TunnelTriage memo</title>
    <style>
      body { font-family: Georgia, "Times New Roman", serif; color: #111;
             max-width: 720px; margin: 40px auto; line-height: 1.5; padding: 0 16px; }
      h1 { font-size: 22px; } h2 { font-size: 16px; margin-top: 20px; }
      ul { padding-left: 20px; }
      footer { margin-top: 28px; font-size: 11px; color: #666;
               border-top: 1px solid #ccc; padding-top: 8px; }
    </style>
  </head>
  <body>
    ${html}
    <footer>Planning tool using public FHWA data and stated assumptions. Not an engineering assessment.</footer>
  </body>
</html>`);
    w.document.close();
    w.focus();
    // Give the new window a tick to lay out before invoking print.
    setTimeout(() => w.print(), 250);
  };

  return (
    <div>
      <button onClick={generate} disabled={!plan || busy}>
        {busy ? "Generating…" : "Generate memo"}
      </button>{" "}
      {memo && (
        <>
          {memo.source === "llm" && (
            <span className="chip">AI-written, numbers verified</span>
          )}{" "}
          <button
            className="secondary"
            onClick={() => navigator.clipboard.writeText(memo.markdown)}
          >
            Copy
          </button>{" "}
          <button className="secondary" onClick={downloadPdf}>
            Download PDF
          </button>
        </>
      )}
      {memo?.warnings.map((w) => (
        <div key={w} className="banner info" style={{ marginTop: 8 }}>{w}</div>
      ))}
      {memo && (
        <div className="memo" style={{ marginTop: 10 }} ref={memoRef}>
          <Markdown>{memo.markdown}</Markdown>
        </div>
      )}
    </div>
  );
}
