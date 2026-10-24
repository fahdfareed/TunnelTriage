import type { Plan } from "../types";
import { money, pct, riskPoints } from "../format";

export function Header({ plan }: { plan: Plan | null }) {
  return (
    <header className="app-header">
      <h1>TunnelTriage</h1>
      <div className="tagline">The drone already flew. The budget still has to choose.</div>
      <div className="tiles">
        <Tile label="Risk now" value={plan ? riskPoints(plan.risk_now) : "-"} />
        <Tile
          label="Risk in 5 yrs (do nothing)"
          value={plan ? riskPoints(plan.risk_h_do_nothing) : "-"}
        />
        <Tile
          label="With this plan"
          value={plan ? `${riskPoints(plan.risk_h_with_plan)} (-${pct(plan.risk_reduction_pct)})` : "-"}
        />
        <Tile
          label="Plan cost (est.)"
          value={plan ? `${money(plan.total_cost_low)}-${money(plan.total_cost_high)}` : "-"}
        />
        <Tile
          label="Waiting 2 yrs"
          value={plan ? `+${pct(plan.waiting.cost_increase_pct)} cost` : "-"}
        />
      </div>
    </header>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="tile">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}
