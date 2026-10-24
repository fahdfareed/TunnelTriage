import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Curve, Group, Plan, Tunnel } from "./types";
import { CurveChart } from "./components/CurveChart";
import { Header } from "./components/Header";
import { BudgetBar } from "./components/BudgetBar";
import { MapView } from "./components/MapView";
import { PlanPanel } from "./components/PlanPanel";
import { TunnelDetail } from "./components/TunnelDetail";
import { FindingsPanel } from "./components/FindingsPanel";
import { MemoPanel } from "./components/MemoPanel";
import { ValidationPanel } from "./components/ValidationPanel";
import { computeDiff, type PlanDiff } from "./components/DiffBanner";

type Tab = "Plan" | "Tunnel" | "Findings" | "Memo" | "Validation";
const TABS: Tab[] = ["Plan", "Tunnel", "Findings", "Memo", "Validation"];

export default function App() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [tunnels, setTunnels] = useState<Tunnel[]>([]);
  const [budget, setBudget] = useState(() => Number(new URLSearchParams(window.location.search).get("budget") ?? 0) || 0);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>(() => {
    const t = new URLSearchParams(window.location.search).get("tab") as Tab | null;
    return t && TABS.includes(t) ? t : "Plan";
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [diff, setDiff] = useState<PlanDiff | null>(null);
  const [slider, setSlider] = useState({ min: 0, max: 50_000_000, step: 1_000_000 });
  const [selectedGroup, setSelectedGroup] = useState<string | null>(() => new URLSearchParams(window.location.search).get("group"));
  const [curve, setCurve] = useState<Curve | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const prevPlan = useRef<Plan | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    api.groups().then(setGroups).catch((e) => setErr(String(e)));
    api.tunnels().then(setTunnels).catch((e) => setErr(String(e)));
    api.curve().then(setCurve).catch(() => {});
    api.config().then((c) => {
      const b = c.budget_slider as { min: number; max: number; step: number } | undefined;
      if (b) setSlider({ min: b.min, max: b.max, step: b.step });
    }).catch(() => {});
  }, []);

  const fetchPlan = useCallback(async (b: number, trackDiff: boolean) => {
    setLoading(true);
    try {
      const p = await api.plan(b);
      const d = trackDiff ? computeDiff(prevPlan.current, p) : null;
      setDiff(d);
      prevPlan.current = p;
      setPlan(p);
      setGroups(await api.groups());
      api.curve().then(setCurve).catch(() => {});
      return d;
    } catch (e) {
      setErr(String(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial plan.
  useEffect(() => { fetchPlan(budget, false); /* eslint-disable-next-line */ }, []);

  // Debounced budget changes (SPEC §11.1).
  const onBudget = (v: number) => {
    setBudget(v);
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => fetchPlan(v, false), 250);
  };

  // Findings changed -> re-plan at the same budget, show diff.
  const onFindingsChanged = () => fetchPlan(budget, true);

  const pickGroup = (gid: string | null) => {
    setSelectedGroup(gid);
    if (gid) setTab("Plan");
  };

  const selectTunnel = (tn: string) => {
    setSelected(tn);
    setTab("Tunnel");
  };

  return (
    <div className="app">
      <div className="layout">
        <div className="left-col">
          <Header plan={plan} />
          <BudgetBar budget={budget} loading={loading} onChange={onBudget} {...slider} />
          {err && <div className="banner danger" style={{ margin: 10 }}>{err}</div>}
          <div className="map-wrap">
          <MapView groups={groups} plan={plan} selectedGroup={selectedGroup} onSelectGroup={pickGroup} />
          </div>
        </div>
        <div className="right-pane">
          <div style={{ padding: "10px 14px 0" }}>
            <CurveChart curve={curve} plan={plan} />
          </div>
          <div className="tabs">
            {TABS.map((t) => (
              <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
          <div className="tab-body">
            {tab === "Plan" && <PlanPanel
                plan={plan}
                diff={diff}
                group={groups.find((g) => g.group_id === selectedGroup) ?? null}
                onClearGroup={() => setSelectedGroup(null)}
                onSelectTunnel={selectTunnel}
              />}
            {tab === "Tunnel" && <TunnelDetail tunnelNumber={selected} />}
            {tab === "Findings" && <FindingsPanel tunnels={tunnels} onChanged={onFindingsChanged} />}
            {tab === "Memo" && <MemoPanel plan={plan} />}
            {tab === "Validation" && <ValidationPanel />}
          </div>
        </div>
      </div>
      <div className="footer-note">
        Planning tool using public FHWA data and stated assumptions. Not an engineering assessment.
      </div>
    </div>
  );
}
