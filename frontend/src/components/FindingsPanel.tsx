import { useEffect, useState } from "react";
import { api } from "../api";
import type { Finding, ParseResult, Tunnel } from "../types";
import { tunnelLabel } from "../format";

const DEMO: Partial<Finding>[] = [
  { tunnel_number: "B16T30TWEDOTTE1", element_number: 10132, quantity: 20, condition_state: 4,
    source: "simulated", note: "Simulated drone finding: section loss on overhead element." },
  { tunnel_number: "B16T37SUMDOTV10", element_number: 10061, quantity: 1500, condition_state: 4,
    source: "simulated", note: "Simulated inspector finding: active leak with spalling." },
  { tunnel_number: "B16T36CALDOTV12", element_number: 10070, quantity: 3000, condition_state: 3,
    source: "simulated", note: "Simulated drone finding: delamination on liner." },
];

export function FindingsPanel({
  tunnels,
  onChanged,
}: {
  tunnels: Tunnel[];
  onChanged: () => void;
}) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [text, setText] = useState("");
  const [parse, setParse] = useState<ParseResult | null>(null);
  const [form, setForm] = useState<Partial<Finding>>({
    tunnel_number: "", element_number: undefined, quantity: 1, condition_state: 4,
    source: "simulated", note: "",
  });
  const [busy, setBusy] = useState(false);

  const refresh = () => api.findings().then(setFindings);
  useEffect(() => { refresh(); }, []);

  const apply = async (f: Partial<Finding>) => {
    setBusy(true);
    await api.addFinding(f);
    await refresh();
    onChanged();
    setBusy(false);
  };

  const remove = async (id: string) => {
    await api.removeFinding(id);
    await refresh();
    onChanged();
  };

  const reset = async () => {
    await api.resetFindings();
    await refresh();
    onChanged();
  };

  const loadDemo = async () => {
    setBusy(true);
    for (const f of DEMO) {
      await api.addFinding(f);
      await refresh();
      onChanged();
      await new Promise((r) => setTimeout(r, 1500));
    }
    setBusy(false);
  };

  const doParse = async () => {
    const r = await api.parse(text);
    setParse(r);
    setForm({
      tunnel_number: r.proposal.tunnel_number ?? "",
      element_number: r.proposal.element_number ?? undefined,
      quantity: r.proposal.quantity,
      condition_state: r.proposal.condition_state,
      source: "simulated",
      note: r.proposal.note,
    });
  };

  return (
    <div>
      <div className="section-title">Free-text finding ("the drone already flew")</div>
      <textarea
        style={{ width: "100%", minHeight: 54 }}
        placeholder="e.g. section loss on Ted Williams overhead element 10132, about 20 SF, severe"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div style={{ marginTop: 6 }}>
        <button onClick={doParse} disabled={!text.trim()}>Parse</button>{" "}
        {parse && (
          <span className="chip">{parse.used_llm ? "LLM-parsed" : "heuristic"}</span>
        )}
      </div>

      <div className="section-title">Proposed / structured finding</div>
      <div className="kv">
        <span className="k">Tunnel</span>
        <select
          value={form.tunnel_number}
          onChange={(e) => setForm({ ...form, tunnel_number: e.target.value })}
        >
          <option value="">— choose —</option>
          {tunnels.map((t) => (
            <option key={t.tunnel_number} value={t.tunnel_number}>
              {tunnelLabel(t.name)}
            </option>
          ))}
        </select>
        <span className="k">Element number</span>
        <input
          type="number"
          value={form.element_number ?? ""}
          onChange={(e) => setForm({ ...form, element_number: Number(e.target.value) })}
        />
        <span className="k">Quantity</span>
        <input
          type="number"
          value={form.quantity ?? 1}
          onChange={(e) => setForm({ ...form, quantity: Number(e.target.value) })}
        />
        <span className="k">Condition state</span>
        <select
          value={form.condition_state}
          onChange={(e) => setForm({ ...form, condition_state: Number(e.target.value) })}
        >
          <option value={3}>3 — Poor</option>
          <option value={4}>4 — Severe</option>
        </select>
        <span className="k">Note</span>
        <input value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
      </div>
      <div style={{ marginTop: 8 }}>
        <button
          onClick={() => apply(form)}
          disabled={busy || !form.tunnel_number || !form.element_number}
        >
          Apply
        </button>{" "}
        <button className="secondary" onClick={loadDemo} disabled={busy}>
          Load demo findings
        </button>{" "}
        <button className="secondary" onClick={reset} disabled={busy}>
          Reset all
        </button>
      </div>

      <div className="section-title">Applied findings ({findings.length})</div>
      {findings.length === 0 && <div className="spinner">None applied.</div>}
      {findings.map((f) => (
        <div
          key={f.finding_id}
          style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: "1px solid var(--border)" }}
        >
          <div>
            <span className="chip sim">{f.source}</span> {tunnelLabel(tunnels.find((t) => t.tunnel_number === f.tunnel_number)?.name ?? "Tunnel")} ·
            qty {f.quantity} · CS{f.condition_state}
            <div style={{ color: "var(--muted)", fontSize: 11 }}>{f.note}</div>
          </div>
          <button className="secondary" onClick={() => remove(f.finding_id)}>Remove</button>
        </div>
      ))}
    </div>
  );
}
