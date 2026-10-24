import { useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { Group, Plan } from "../types";
import { num } from "../format";

// 5-bin sequential colour scale for risk (colour-blind-safe yellows->reds).
const BINS = ["#fee08b", "#fdae61", "#f46d43", "#d73027", "#a50026"];

function riskColor(risk: number, max: number): string {
  if (max <= 0) return BINS[0];
  const idx = Math.min(BINS.length - 1, Math.floor((risk / max) * BINS.length));
  return BINS[idx];
}

function FitButton({ groups }: { groups: Group[] }) {
  const map = useMap();
  const fit = () => {
    const pts = groups
      .filter((g) => g.lat != null && g.lon != null)
      .map((g) => [g.lat as number, g.lon as number]) as [number, number][];
    if (pts.length) map.fitBounds(pts, { padding: [40, 40] });
  };
  return (
    <button
      className="secondary"
      style={{ position: "absolute", top: 10, right: 10, zIndex: 1000 }}
      onClick={fit}
    >
      Fit all
    </button>
  );
}

export function MapView({
  groups,
  plan,
  onSelectTunnel,
}: {
  groups: Group[];
  plan: Plan | null;
  onSelectTunnel: (tn: string) => void;
}) {
  const maxRisk = useMemo(
    () => Math.max(1, ...groups.map((g) => g.risk_now)),
    [groups]
  );
  const maxAdt = useMemo(
    () => Math.max(1, ...groups.map((g) => g.adt_max)),
    [groups]
  );
  const fundedByGroup = useMemo(() => {
    const m: Record<string, number> = {};
    plan?.by_group.forEach((g) => (m[g.group_id] = g.funded_cost));
    return m;
  }, [plan]);

  return (
    <div className="map-pane" style={{ position: "relative" }}>
      <MapContainer center={[42.355, -71.05]} zoom={13} style={{ height: "100%" }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitButton groups={groups} />
        {groups
          .filter((g) => g.lat != null && g.lon != null)
          .map((g) => (
            <CircleMarker
              key={g.group_id}
              center={[g.lat as number, g.lon as number]}
              radius={6 + 16 * Math.sqrt(g.adt_max / maxAdt)}
              pathOptions={{
                color: "#222",
                weight: 1,
                fillColor: riskColor(g.risk_now, maxRisk),
                fillOpacity: 0.8,
              }}
            >
              <Popup>
                <strong>{g.name}</strong>
                <div>Risk: {num(g.risk_now)} risk points</div>
                <div>Max ADT: {num(g.adt_max)}</div>
                {fundedByGroup[g.group_id] != null && (
                  <div>Funded in plan: {num(fundedByGroup[g.group_id])}</div>
                )}
                <div style={{ marginTop: 6 }}>
                  {g.segments.map((s) => (
                    <div key={s}>
                      <a href="#" onClick={(e) => { e.preventDefault(); onSelectTunnel(s); }}>
                        {s}
                      </a>
                    </div>
                  ))}
                </div>
              </Popup>
            </CircleMarker>
          ))}
      </MapContainer>
    </div>
  );
}
