import type { Plan, PlanItem } from "../types";
import { money, moneyRange, num } from "../format";
import { DiffBanner, type PlanDiff } from "./DiffBanner";

export function PlanPanel({
  plan,
  diff,
  onSelectTunnel,
}: {
  plan: Plan | null;
  diff: PlanDiff | null;
  onSelectTunnel: (tn: string) => void;
}) {
  if (!plan) return <div className="spinner">Loading plan…</div>;

  return (
    <div>
      {plan.forced_unmet.length > 0 && (
        <div className="banner danger">
          Budget does not cover {plan.forced_unmet.length} safety-critical repair
          {plan.forced_unmet.length > 1 ? "s" : ""}.
        </div>
      )}
      <DiffBanner diff={diff} />
      <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 6 }}>
        Solver: {plan.solver} · {plan.funded.length} funded · point est. {money(plan.total_cost_point)}
      </div>
      <ItemTable items={plan.funded} onSelectTunnel={onSelectTunnel} ranked />
      <div className="section-title">Not funded (top 15)</div>
      <ItemTable items={plan.unfunded_top} onSelectTunnel={onSelectTunnel} />
    </div>
  );
}

function ItemTable({
  items,
  onSelectTunnel,
  ranked,
}: {
  items: PlanItem[];
  onSelectTunnel: (tn: string) => void;
  ranked?: boolean;
}) {
  if (!items.length) return <div className="spinner">None.</div>;
  return (
    <table>
      <thead>
        <tr>
          {ranked && <th>#</th>}
          <th>Tunnel</th>
          <th>Element</th>
          <th>Action</th>
          <th>Qty</th>
          <th>Cost (est.)</th>
          <th>Risk</th>
          <th>Why</th>
        </tr>
      </thead>
      <tbody>
        {items.map((i) => (
          <tr key={i.action_id} className="clickable" onClick={() => onSelectTunnel(i.tunnel_number)}>
            {ranked && <td>{i.rank}</td>}
            <td>{i.tunnel_name}</td>
            <td>
              {i.element_name}
              <span className="chip">{i.element_number}</span>
            </td>
            <td>{i.action === "FIX_SEVERE" ? "Fix severe" : "Fix poor+severe"}</td>
            <td>{num(i.qty)}</td>
            <td>{moneyRange(i.cost_low, i.cost_high)}</td>
            <td title="Risk points removed">{num(i.benefit)}</td>
            <td>
              {i.reason_codes.map((c) => (
                <span key={c} className="chip">
                  {c.replace(/_/g, " ").toLowerCase()}
                </span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
