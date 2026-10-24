import { money } from "../format";

const TICKS = [
  { v: 15_300_000, label: "$15.3M 2022 contract", source: "MassDOT board summary, 2022 tunnel contract (SPEC §17)" },
  { v: 25_000_000, label: "$25M", source: "Demo checkpoint" },
  { v: 50_000_000, label: "$50M cap", source: "Demo budget cap" },
];

export function BudgetBar({
  budget,
  loading,
  onChange,
  min,
  max,
  step,
}: {
  min: number;
  max: number;
  step: number;
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
        min={min}
        max={max}
        step={step}
        value={budget}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="ticks">
        {TICKS.filter((t) => t.v >= min && t.v <= max).map((t) => (
          <button
            key={t.v}
            className="secondary"
            style={{ padding: "2px 6px", fontSize: 10, left: `${((t.v - min) / (max - min)) * 100}%`, transform: `translateX(-${Math.round(((t.v - min) / (max - min)) * 100)}%)` }}
            onClick={() => onChange(t.v)}
            title={`Jump to ${money(t.v)} · ${t.source}`}
          >
            {t.label}
          </button>
        ))}
      </div>
    </div>
  );
}
