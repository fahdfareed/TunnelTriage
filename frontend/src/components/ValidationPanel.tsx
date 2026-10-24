import { useEffect, useState } from "react";
import { api } from "../api";
import type { Validation } from "../types";
import { money, num, tunnelLabel } from "../format";

const pctText = (n: number) => `${n >= 0 ? "+" : "−"}${Math.abs(n).toFixed(1)}%`;

export function ValidationPanel() {
  const [v, setV] = useState<Validation | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.validation().then(setV).catch((e) => setErr(String(e)));
  }, []);
  if (err) return <div className="banner danger">{err}</div>;
  if (!v) return <div className="spinner">Loading validation…</div>;

  const b = v.backtest;
  const maxCat = Math.max(...v.spend_by_category.map((c) => c.amount));
  return (
    <div>
      <div className="section-title" style={{ marginTop: 0 }}>Checked against a real award</div>
      <p style={{ margin: "0 0 8px" }}>
        MassDOT Contract {v.contract.contract}, <em>{v.contract.title}</em>, bids opened {v.contract.bid_opening}.
        Awarded at <strong>{money(v.bid.low_bid)}</strong>, {pctText(v.bid.low_bid_vs_estimate_pct)} over MassDOT&apos;s
        own estimate of {money(v.bid.office_estimate)}. It covers Callahan, Ted Williams, Thomas P. O&apos;Neill and
        the I-90 connector tunnels.
      </p>

      <div className="section-title">Does the model agree?</div>
      <table>
        <tbody>
          <tr>
            <td>Total severe-damage backlog, all tunnels</td>
            <td><strong>{money(b.backlog_severe_all)}</strong></td>
            <td className="why">
              Sits between MassDOT&apos;s {money(b.program_5yr_anchor)} five-year tunnels program and the {money(b.need_10yr_anchor)} ten-year need
              for the whole highway system (all asset types). Neither number was used to set the rates.
            </td>
          </tr>
          <tr>
            <td>Where the model spends a {money(b.plan_budget)} budget</td>
            <td><strong>{Math.round(b.scope_share_of_funded_pct)}%</strong> in those four tunnels</td>
            <td className="why">{b.scope_tunnels_in_top5} of the model&apos;s top 5 tunnels are in the contract, and all {b.scope_tunnels_funded} of 4 get work.</td>
          </tr>
          <tr>
            <td>Where it disagrees: Callahan</td>
            <td>
              <strong>{money(b.callahan_model_funded)}</strong> vs {money(b.callahan_contract_spend)} (ceiling, plenums, ducts)
            </td>
            <td className="why">
              The model under-ranks Callahan. The federal data rates its ceiling panels{" "}
              {b.callahan_ceiling_panels_good_pct != null ? `${b.callahan_ceiling_panels_good_pct.toFixed(1)}% good` : "mostly good"}, yet
              MassDOT is paying to replace about 230 of them. Condition ratings alone miss life-expired parts, a real gap.
            </td>
          </tr>
          <tr>
            <td>Bid vs estimate</td>
            <td>
              Low bid {pctText(v.bid.low_bid_vs_estimate_pct)}, second bid {pctText(v.bid.second_bid_vs_estimate_pct)}
            </td>
            <td className="why">
              Our assumed range is {pctText(v.assumed_bid_range.low * 100)} to {pctText(v.assumed_bid_range.high * 100)}, which covers both.
              Only {v.bid.bidders_who_bid} of {v.bid.eligible_bidders} eligible bidders bid.
            </td>
          </tr>
        </tbody>
      </table>

      <div className="section-title">Where the unit rates come from</div>
      <p className="why" style={{ margin: "0 0 6px" }}>
        Median awarded unit price per repair type in this contract. Light vs heavy, and component vs whole system, are my grouping of its line items.
        These rates come from this same contract, so this table shows the derivation, not an independent test.
      </p>
      <table>
        <thead>
          <tr><th>Repair type</th><th>Our rate</th><th>Awarded range</th><th>Items</th></tr>
        </thead>
        <tbody>
          {v.unit_rates.map((r) => (
            <tr key={r.unit_type + r.tier}>
              <td>
                {r.unit_type === "system" ? "Whole system, per unit" : r.unit_type === "each" ? "Component, per unit" : "Per sq ft / ft"},{" "}
                {r.tier === "light" ? "lighter repair" : "heavier repair"}
              </td>
              <td>{money(r.our_rate)}</td>
              <td className="why">{money(r.observed_min)} to {money(r.observed_max)}</td>
              <td>{r.n_items}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="section-title">What else we took from it</div>
      <ul style={{ margin: 0, paddingLeft: 18 }}>
        <li>
          <strong>All-in cost:</strong> the program budget was {money(v.bid.program_total)}, {v.bid.program_over_bid_pct.toFixed(0)}% over the
          bid (15% contingency, 5% construction engineering, traffic police). The header shows both numbers.
        </li>
        <li>
          <strong>Mobilization:</strong> {money(v.bid.mobilization_low_bid)} once for all four tunnels, {v.bid.mobilization_pct_of_bid.toFixed(1)}% of
          the bid. We add {(v.assumptions.mobilization_pct * 100).toFixed(0)}% to repair costs instead of charging a fee per tunnel.
        </li>
      </ul>

      <div className="section-title">Where the {money(v.bid.low_bid)} went</div>
      {v.spend_by_category.map((c) => (
        <div key={c.category} style={{ display: "flex", alignItems: "center", gap: 8, margin: "3px 0", fontSize: 12 }}>
          <div style={{ width: 190 }}>{c.category}</div>
          <div style={{ flex: 1, background: "var(--panel2)", borderRadius: 3 }}>
            <div style={{ width: `${(100 * c.amount) / maxCat}%`, background: "#4a9eff", height: 10, borderRadius: 3 }} />
          </div>
          <div style={{ width: 60, textAlign: "right" }}>{money(c.amount)}</div>
        </div>
      ))}

      <div className="section-title">Limits</div>
      <ul style={{ margin: 0, paddingLeft: 18 }} className="why">
        <li>One contract, two bids. It anchors the model but does not prove it.</li>
        <li>Quantities come from federal condition data, not site takeoffs, and the model prices elements, not MassDOT pay items.</li>
        <li>Line items were transcribed by hand from the public bid tabulation ({v.contract.items_note})</li>
        <li>Planning tool, not an engineering assessment or a bid.</li>
      </ul>
      <div style={{ height: 8 }} />
      <span className="chip">{num(v.unit_rates.reduce((a, r) => a + r.n_items, 0))} line items used for rates</span>
      {b.scope_tunnels_funded === 4 && (
        <span className="chip">{b.contract.scope_tunnels.map(tunnelLabel).join(" · ")}</span>
      )}
    </div>
  );
}
