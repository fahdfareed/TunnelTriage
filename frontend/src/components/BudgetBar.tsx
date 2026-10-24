import { money } from "../format";

const TICKS = [
  { v: 15_300_000, label: "$15.3M 2022 contract" },
  { v: 64_727_001, label: "$64.7M 2025 Preservation" },
  { v: 74_000_000, label: "$74M ~1yr program" },
  { v: 128_482_140, label: "$128.5M CANA" },
];

export function BudgetBar({
  budget,
  loading,
  onChange,
}: {
  budget: number;
  loading: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <div className="budget-bar">
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <strong>Budget: {money(budget)}</strong>
        {loading && <span className="spinner">updating plan…</span>}
      </div>
      <input
        type="range"
        min={0}
        max={150_000_000}
        step={1_000_000}
        value={budget}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="ticks">
        {TICKS.map((t) => (
          <button
            key={t.v}
            className="secondary"
            style={{ padding: "2px 6px", fontSize: 10 }}
            onClick={() => onChange(t.v)}
            title={`Jump to ${money(t.v)}`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
