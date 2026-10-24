import type { Curve, Plan } from "../types";
import { money, num } from "../format";

// Risk today after repairs vs. budget, with the current plan marked.
export function CurveChart({ curve, plan }: { curve: Curve | null; plan: Plan | null }) {
  if (!curve || !curve.points.length) return null;
  const W = 560, H = 105, L = 40, R = 10, T = 10, B = 24;
  const pts = curve.points;
  const x0 = pts[0].budget, x1 = pts[pts.length - 1].budget;
  const ymax = Math.max(curve.risk_now, ...pts.map((p) => p.risk_now_after));
  const X = (b: number) => L + ((b - x0) / (x1 - x0)) * (W - L - R);
  const Y = (r: number) => T + (1 - r / ymax) * (H - T - B);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${X(p.budget).toFixed(1)},${Y(p.risk_now_after).toFixed(1)}`).join(" ");
  const area = `${line} L${X(x1)},${Y(0)} L${X(x0)},${Y(0)} Z`;
  // Knee: first budget that removes 80% of all the risk the slider range can remove.
  const total = ymax - pts[pts.length - 1].risk_now_after;
  const knee = pts.find((p) => ymax - p.risk_now_after >= 0.8 * total) ?? null;
  return (
    <div className="chart" style={{ marginBottom: 0 }}>
      <div className="section-title" style={{ marginTop: 0 }}>Risk today vs. budget</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Risk today after repairs versus budget">
        <path d={area} fill="rgba(74,158,255,0.15)" />
        <path d={line} fill="none" stroke="#4a9eff" strokeWidth={2} />
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={Y(ymax * t)} y2={Y(ymax * t)} stroke="#2e3844" />
            <text x={L - 4} y={Y(ymax * t) + 3} fontSize={9} fill="#8b98a5" textAnchor="end">{num(ymax * t)}</text>
          </g>
        ))}
        {[x0, (x0 + x1) / 2, x1].map((b) => (
          <text key={b} x={X(b)} y={H - 8} fontSize={9} fill="#8b98a5" textAnchor="middle">{money(b)}</text>
        ))}
        {knee && (
          <g>
            <line x1={X(knee.budget)} x2={X(knee.budget)} y1={T} y2={H - B} stroke="#ffd54f" strokeDasharray="3 3" />
            <text x={X(knee.budget) + 4} y={H - B - 6} fontSize={9} fill="#ffd54f">80% of the benefit by {money(knee.budget)}</text>
          </g>
        )}
        {plan && (
          <g>
            <circle cx={X(plan.budget)} cy={Y(plan.risk_now_after)} r={6} fill="#ff5252" stroke="#fff" strokeWidth={1.5} />
            <text x={X(plan.budget) + (plan.budget > (x0 + x1) / 2 ? -9 : 9)} y={Y(plan.risk_now_after) + (Y(plan.risk_now_after) < T + 16 ? 18 : -9)}
              fontSize={10} fill="#fff" textAnchor={plan.budget > (x0 + x1) / 2 ? "end" : "start"}>
              you are here
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
