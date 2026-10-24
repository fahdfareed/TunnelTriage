import { useMemo } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { Group, Plan } from "../types";
import { num, tunnelLabel } from "../format";

// Multi-stop sequential ramp (green -> yellow -> orange -> red -> purple),
// interpolated continuously so small risk changes are visible.
const STOPS: [number, number, number][] = [
  [26, 152, 80], [145, 207, 96], [217, 239, 139], [254, 224, 139],
  [253, 174, 97], [244, 109, 67], [215, 48, 39], [165, 0, 38], [103, 0, 92],
];

function riskColor(risk: number, max: number): string {
  const t = max <= 0 ? 0 : Math.min(1, Math.sqrt(Math.max(0, risk) / max));
  const x = t * (STOPS.length - 1);
  const i = Math.min(STOPS.length - 2, Math.floor(x));
  const f = x - i;
  const c = STOPS[i].map((v, k) => Math.round(v + (STOPS[i + 1][k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

const radiusFor = (risk: number, max: number) => 5 + 36 * Math.sqrt(Math.max(0, risk) / max);

function FitButton({ groups }: { groups: Group[] }) {
  const map = useMap();
  const fit = () => {
    const pts = groups
      .filter((g) => g.lat != null && g.lon != null)
      .map((g) => [g.lat as number, g.lon as number]) as [number, number][];
    if (pts.length) map.fitBounds(pts, { padding: [60, 60] });
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

function ClearOnMapClick({ onClear }: { onClear: () => void }) {
  useMapEvents({ click: onClear });
  return null;
}

const LEGEND_STEPS = [0, 0.1, 0.25, 0.5, 0.75, 1];

function Legend({ fundedCount, total }: { fundedCount: number; total: number }) {
  return (
    <div className="map-legend">
      <div style={{ fontWeight: 600, marginBottom: 4 }}>Risk today</div>
      <div style={{ display: "flex", height: 10, width: 170, borderRadius: 4, overflow: "hidden" }}>
        {LEGEND_STEPS.map((t) => (
          <div key={t} style={{ flex: 1, background: riskColor(t * t * 1000, 1000) }} />
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", width: 170, color: "var(--muted)" }}>
        <span>low</span>
        <span>high</span>
      </div>
      <div style={{ color: "var(--muted)", marginTop: 4 }}>Bubble size = same risk</div>
      <div style={{ color: "var(--muted)" }}>Dashed ring = before repairs</div>
      <div style={{ color: "var(--muted)" }}>Click a tunnel to filter the plan</div>
      <div style={{ color: "#66bb6a" }}>Green outline = funded work</div>
      <div style={{ marginTop: 4 }}>{fundedCount} of {total} locations get funded work</div>
    </div>
  );
}

export function MapView({
  groups,
  plan,
  selectedGroup,
  onSelectGroup,
}: {
  groups: Group[];
  plan: Plan | null;
  selectedGroup: string | null;
  onSelectGroup: (gid: string | null) => void;
}) {
  const maxRisk = useMemo(() => Math.max(1, ...groups.map((g) => g.risk_now)), [groups]);
  const fundedByGroup = useMemo(() => {
    const m: Record<string, number> = {};
    plan?.by_group.forEach((g) => (m[g.group_id] = g.funded_cost));
    return m;
  }, [plan]);
  // Exact per-group risk today after the plan's repairs (from the backend).
  const afterByGroup = useMemo(() => {
    const m: Record<string, number> = {};
    plan?.by_group.forEach((g) => (m[g.group_id] = g.risk_now_after));
    return m;
  }, [plan]);
  const shown = (g: Group) => afterByGroup[g.group_id] ?? g.risk_now;
  const fundedCount = groups.filter((g) => (fundedByGroup[g.group_id] ?? 0) > 0).length;

  const placed = useMemo(
    () =>
      groups
        .filter((g) => g.lat != null && g.lon != null)
        .sort((a, b) => b.risk_now - a.risk_now), // big first, small drawn on top
    [groups]
  );
  const labelled = useMemo(() => new Set(placed.slice(0, 6).map((g) => g.group_id)), [placed]);

  return (
    <div className="map-pane" style={{ position: "relative" }}>
      <MapContainer
        center={[42.355, -71.08]}
        zoom={13}
        minZoom={10}
        maxBounds={[[42.1, -71.45], [42.6, -70.75]]}
        style={{ height: "100%" }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitButton groups={groups} />
        <ClearOnMapClick onClear={() => onSelectGroup(null)} />
        <Legend fundedCount={fundedCount} total={groups.length} />
        {/* Ghost rings: where the risk was before repairs. */}
        {placed.map((g) => (
            <CircleMarker
              key={`ghost-${g.group_id}`}
              center={[g.lat as number, g.lon as number]}
              radius={radiusFor(g.risk_now, maxRisk)}
              interactive={false}
              pathOptions={{ color: "#ffffff", weight: 2, dashArray: "5 5", fill: false, opacity: 0.85 }}
            />
          ))}
        {placed.map((g) => {
          const funded = (fundedByGroup[g.group_id] ?? 0) > 0;
          const selected = selectedGroup === g.group_id;
          const dim = selectedGroup != null && !selected;
          return (
            <CircleMarker
              key={g.group_id}
              center={[g.lat as number, g.lon as number]}
              radius={radiusFor(shown(g), maxRisk)}
              pathOptions={{
                color: selected ? "#ffffff" : funded ? "#66bb6a" : "#111",
                weight: selected ? 4 : funded ? 3 : 1.5,
                fillColor: riskColor(shown(g), maxRisk),
                fillOpacity: dim ? 0.3 : 0.85,
                opacity: dim ? 0.4 : 1,
                bubblingMouseEvents: false,
              }}
              eventHandlers={{ click: () => onSelectGroup(selected ? null : g.group_id) }}
            >
              {labelled.has(g.group_id) && (
                <Tooltip permanent direction="right" offset={[8, 0]} className="map-label">
                  {tunnelLabel(g.name)}
                </Tooltip>
              )}
              <Popup>
                <strong>{tunnelLabel(g.name)}</strong>
                <div>Risk before repairs: {num(g.risk_now)}</div>
                <div>Risk after this plan: {num(afterByGroup[g.group_id] ?? g.risk_now)}</div>
                <div>Max ADT: {num(g.adt_max)}</div>
                {fundedByGroup[g.group_id] != null && (
                  <div>Funded in plan: ${num(fundedByGroup[g.group_id])}</div>
                )}
              </Popup>
            </CircleMarker>
          );
        })}
      </MapContainer>
    </div>
  );
}
