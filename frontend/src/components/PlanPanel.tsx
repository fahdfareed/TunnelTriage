import { useState } from "react";
import type { Group, Plan, PlanItem } from "../types";
import { downloadCsv, money, moneyRange, num, tunnelLabel, whyText } from "../format";
import { DiffBanner, type PlanDiff } from "./DiffBanner";

export function PlanPanel({
  plan,
  diff,
  group,
  onClearGroup,
  onSelectTunnel,
}: {
  group: Group | null;
  onClearGroup: () => void;
  plan: Plan | null;
  diff: PlanDiff | null;
  onSelectTunnel: (tn: string) => void;
}) {
  const [sub, setSub] = useState<"funded" | "unfunded">("funded");
  if (!plan) return <div className="spinner">Loading plan…</div>;
  const funded = group ? plan.funded.filter((i) => i.group_id === group.group_id) : plan.funded;
  const unfunded = group ? plan.unfunded_by_group[group.group_id] ?? [] : plan.unfunded_top;

  return (
    <div>
      {plan.forced_unmet.length > 0 && (
        <div className="banner danger">
          Budget does not cover {plan.forced_unmet.length} safety-critical repair
          {plan.forced_unmet.length > 1 ? "s" : ""}.
        </div>
      )}
      {group && (
        <div className="banner info" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>
            Showing <strong>{tunnelLabel(group.name)}</strong> only: {funded.length} funded, {unfunded.length}
            {unfunded.length >= 15 ? "+" : ""} not funded
          </span>
          <button className="secondary" onClick={onClearGroup}>Show all tunnels</button>
        </div>
      )}
      <DiffBanner diff={diff} />
      <div className="tabs sub">
        <button className={sub === "funded" ? "active" : ""} onClick={() => setSub("funded")}>
          Funded ({funded.length})
        </button>
        <button className={sub === "unfunded" ? "active" : ""} onClick={() => setSub("unfunded")}>
          Not funded ({unfunded.length}{unfunded.length >= 15 ? "+" : ""})
        </button>
      </div>
      {sub === "funded" ? (
        <>
          <div style={{ color: "var(--muted)", fontSize: 12, margin: "8px 0 6px" }}>
            Solver: {plan.solver} · point est. {money(plan.total_cost_point)}
          </div>
          <button className="secondary" style={{ marginBottom: 8 }} onClick={() => exportPlan(plan, funded, group)}>
            Export plan (CSV)
          </button>{" "}
          <button className="secondary" style={{ marginBottom: 8 }} onClick={() => window.print()}>
            Print / save PDF
          </button>
          <ItemTable items={funded} onSelectTunnel={onSelectTunnel} ranked />
        </>
      ) : (
        <>
          <div style={{ color: "var(--muted)", fontSize: 12, margin: "8px 0 6px" }}>
            Highest-benefit repairs the budget doesn't cover (top 15).
          </div>
          <ItemTable items={unfunded} onSelectTunnel={onSelectTunnel} />
        </>
      )}
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
  if (!items.length) return <div className="spinner">None at this budget.</div>;
  return (
    <table>
      <thead>
        <tr>
          {ranked && <th>#</th>}
          <th>Where / what</th>
          <th>Repair</th>
          <th>Cost (est.)</th>
          <th>Risk removed</th>
          <th>Why</th>
        </tr>
      </thead>
      <tbody>
        {items.map((i) => (
          <tr key={i.action_id} className="clickable" onClick={() => onSelectTunnel(i.tunnel_number)}>
            {ranked && <td>{i.rank}</td>}
            <td>
              <div>{i.element_name}</div>
              <div className="item-sub">{tunnelLabel(i.tunnel_name)}</div>
            </td>
            <td>
              {i.action === "FIX_SEVERE" ? "Severe only" : "Poor + severe"}
              <div className="item-sub">{num(i.qty)} {i.qty === 1 ? "unit" : "units"}</div>
            </td>
            <td>
              {money(i.cost_point)}
              <div className="item-sub">{moneyRange(i.cost_low, i.cost_high)}</div>
            </td>
            <td title="Risk points removed over the forecast horizon">{num(i.benefit)}</td>
            <td className="why">{whyText(i.reason_codes)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}


function exportPlan(plan: Plan, items: PlanItem[], group: Group | null) {
  const head = [
    "Rank", "Tunnel", "Element", "Action", "Qty",
    "Cost low", "Cost point", "Cost high", "Risk removed", "Risk removed per $M", "Why",
  ];
  const rows = items.map((i) => [
    i.rank, tunnelLabel(i.tunnel_name), i.element_name,
    i.action === "FIX_SEVERE" ? "Fix severe" : "Fix poor+severe",
    Math.round(i.qty), Math.round(i.cost_low), Math.round(i.cost_point), Math.round(i.cost_high),
    Math.round(i.benefit), Math.round(i.benefit_per_million), whyText(i.reason_codes),
  ]);
  downloadCsv(`tunneltriage-plan-${Math.round(plan.budget / 1e6)}M${group ? "-" + tunnelLabel(group.name).replace(/\W+/g, "-") : ""}.csv`, [head, ...rows]);
}
