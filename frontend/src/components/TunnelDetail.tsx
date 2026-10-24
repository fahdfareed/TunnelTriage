import { useEffect, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import type { TunnelDetail as TD } from "../types";
import { num } from "../format";
import { StackedBar } from "./StackedBar";

export function TunnelDetail({ tunnelNumber }: { tunnelNumber: string | null }) {
  const [data, setData] = useState<TD | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!tunnelNumber) return;
    setData(null);
    setErr(null);
    api.tunnel(tunnelNumber).then(setData).catch((e) => setErr(String(e)));
  }, [tunnelNumber]);

  if (!tunnelNumber) return <div className="spinner">Select a tunnel from the map or plan.</div>;
  if (err) return <div className="banner danger">{err}</div>;
  if (!data) return <div className="spinner">Loading…</div>;

  const t = data.tunnel;
  return (
    <div>
      <h3 style={{ margin: "0 0 8px" }}>
        {t.name} <span className="chip">{t.tunnel_number}</span>
      </h3>
      <div className="kv">
        <span className="k">Year built</span><span>{t.year_built || "-"}</span>
        <span className="k">Rehabilitated</span><span>{t.year_rehab || "-"}</span>
        <span className="k">ADT</span><span>{num(t.adt)}</span>
        <span className="k">Length (ft)</span><span>{num(Number(t.length_ft) || 0)}</span>
        <span className="k">Last inspected</span><span>{t.last_inspection_date || "-"}</span>
        <span className="k">Under navigable water</span><span>{t.under_water ? "Yes" : "No"}</span>
      </div>

      <div className="section-title">Risk over 10 years</div>
      <div style={{ height: 180 }}>
        <ResponsiveContainer>
          <LineChart data={data.forecast}>
            <CartesianGrid stroke="#2e3844" />
            <XAxis dataKey="year" stroke="#8b98a5" fontSize={11} />
            <YAxis stroke="#8b98a5" fontSize={11} />
            <Tooltip
              contentStyle={{ background: "#1a2029", border: "1px solid #2e3844" }}
              formatter={(v: number) => [`${num(v)} risk points`, "Do nothing"]}
            />
            <Line type="monotone" dataKey="risk" stroke="#f46d43" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="section-title">Elements</div>
      <table>
        <thead>
          <tr>
            <th>Element</th>
            <th>Condition</th>
            <th>Total</th>
            <th>Crit.</th>
            <th>Risk</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {data.elements.map((e) => (
            <tr key={e.key}>
              <td>
                {e.element_name}
                <span className="chip">{e.element_number}</span>
              </td>
              <td><StackedBar shares={e.shares} /></td>
              <td>{num(e.total)}</td>
              <td>{e.criticality}</td>
              <td>{e.scored ? num(e.risk_now) : "-"}</td>
              <td>
                {e.dq_flags.map((f) => (
                  <span key={f} className="chip" title={f}>
                    {f.replace("DQ_", "").toLowerCase()}
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
