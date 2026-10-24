import type { Plan } from "../types";
import { money, num, pct, riskPoints } from "../format";

export function Header({
  plan,
}: {
  plan: Plan | null;
}) {
  const removed = plan && plan.risk_now > 0 ? (100 * (plan.risk_now - plan.risk_now_after)) / plan.risk_now : 0;
  const tunnels = plan ? new Set(plan.funded.map((f) => f.tunnel_number)).size : 0;
  return (
    <header className="app-header">
      <h1>TunnelTriage</h1>
      <div className="tagline">The drone already flew. The budget still has to choose.</div>
      <div className="hero">
        <Hero
          label="Danger removed today"
          value={plan ? pct(removed) : "-"}
          sub={plan ? `${num(plan.risk_now)} → ${num(plan.risk_now_after)} risk points` : ""}
          tone={removed >= 66 ? "good" : removed >= 33 ? "mid" : "bad"}
        />
        <Hero
          label="Repairs funded"
          value={plan ? num(plan.funded.length) : "-"}
          sub={plan ? `across ${tunnels} tunnel${tunnels === 1 ? "" : "s"}` : ""}
        />
        <Hero
          label="Construction cost (est.)"
          value={plan ? money(plan.total_cost_point) : "-"}
          sub={plan ? `${money(plan.total_cost_low)}–${money(plan.total_cost_high)} · ${money(plan.program_cost_point)} all-in` : ""}
        />
        <Hero
          label="If we wait 2 years"
          value={plan && plan.funded.length === 0 ? "—" : plan ? `${plan.waiting.cost_increase_pct >= 0 ? "+" : "−"}${Math.abs(Math.round(plan.waiting.cost_increase_pct))}% cost` : "-"}
          sub={plan && plan.funded.length === 0 ? "nothing funded yet" : plan ? `+${num(plan.waiting.extra_risk_2y)} risk-years of exposure` : ""}
          tone="bad"
        />
      </div>
      <div className="subtiles" title="Forecast risk five years out, with the plan's repairs aging too.">
        {plan && (
          <>
            <span>5-yr risk, do nothing: <b>{riskPoints(plan.risk_h_do_nothing)}</b></span>
            <span>with this plan: <b>{riskPoints(plan.risk_h_with_plan)}</b></span>
            <span
              title={`${plan.n_rows_no_action} of ${plan.n_rows_scored} scored elements have no repair option here, and repaired elements keep aging, so risk can't reach zero.`}
            >
              best case, every repair funded: <b>{riskPoints(plan.risk_h_floor)}</b>
            </span>
          </>
        )}
      </div>
    </header>
  );
}

function Hero({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: "good" | "mid" | "bad" }) {
  return (
    <div className={`hero-tile ${tone ?? ""}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      <div className="sub">{sub}</div>
    </div>
  );
}
