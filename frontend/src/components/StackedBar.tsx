import { CS_COLORS, CS_LABELS } from "../format";

// 100% stacked bar for condition states 1-4 (SPEC §11.2/11.3).
export function StackedBar({ shares }: { shares: number[] }) {
  const title = shares
    .map((s, i) => `${CS_LABELS[i]}: ${Math.round(s * 100)}%`)
    .join(" · ");
  return (
    <div className="stacked" title={title}>
      {shares.map((s, i) => (
        <span key={i} style={{ width: `${s * 100}%`, background: CS_COLORS[i] }} />
      ))}
    </div>
  );
}
