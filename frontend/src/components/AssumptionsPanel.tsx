import { useEffect, useState } from "react";
import { api } from "../api";
import { money } from "../format";

export function AssumptionsPanel() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null);
  const [notes, setNotes] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.config().then(setConfig);
    api.dataNotes().then(setNotes);
  }, []);

  if (!config) return <div className="spinner">Loading…</div>;
  const calibration = (notes?.calibration ?? {}) as Record<string, number>;

  return (
    <div>
      <div className="banner info">
        Unit costs are <strong>planning assumptions</strong>, not MassDOT costs.
        Deterioration rates are <strong>defaults (not calibrated)</strong>.
      </div>

      <div className="section-title">Cost calibration check</div>
      <div className="kv">
        <span className="k">Backlog: fix all CS4</span>
        <span>{money(calibration.backlog_cs4_cost ?? 0)} (est.)</span>
        <span className="k">Backlog: fix all CS3+CS4</span>
        <span>{money(calibration.backlog_cs34_cost ?? 0)} (est.)</span>
        <span className="k">5-year tunnels program</span>
        <span>{money(calibration.tunnels_5yr_program_anchor ?? 370_000_000)}</span>
      </div>

      <div className="section-title">Config (read-only)</div>
      <pre
        style={{
          background: "var(--panel2)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: 12,
          fontSize: 11,
          overflow: "auto",
          whiteSpace: "pre-wrap",
        }}
      >
        {JSON.stringify(config, null, 2)}
      </pre>
    </div>
  );
}
