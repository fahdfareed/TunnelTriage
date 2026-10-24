import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Group, Plan, Tunnel } from "./types";
import { Header } from "./components/Header";
import { BudgetBar } from "./components/BudgetBar";
import { MapView } from "./components/MapView";
import { PlanPanel } from "./components/PlanPanel";
import { TunnelDetail } from "./components/TunnelDetail";
import { FindingsPanel } from "./components/FindingsPanel";
import { MemoPanel } from "./components/MemoPanel";
import { AssumptionsPanel } from "./components/AssumptionsPanel";
import { DataNotesPanel } from "./components/DataNotesPanel";
import { computeDiff, type PlanDiff } from "./components/DiffBanner";

type Tab = "Plan" | "Tunnel" | "Findings" | "Memo" | "Assumptions" | "Data notes";
const TABS: Tab[] = ["Plan", "Tunnel", "Findings", "Memo", "Assumptions", "Data notes"];

export default function App() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [tunnels, setTunnels] = useState<Tunnel[]>([]);
  const [budget, setBudget] = useState(74_000_000);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState<Tab>("Plan");
  const [selected, setSelected] = useState<string | null>(null);
  const [diff, setDiff] = useState<PlanDiff | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const prevPlan = useRef<Plan | null>(null);
  const debounceRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    api.groups().then(setGroups).catch((e) => setErr(String(e)));
    api.tunnels().then(setTunnels).catch((e) => setErr(String(e)));
  }, []);

  const fetchPlan = useCallback(async (b: number, trackDiff: boolean) => {
    setLoading(true);
    try {
      const p = await api.plan(b);
      if (trackDiff) setDiff(computeDiff(prevPlan.current, p));
      else setDiff(null);
      prevPlan.current = p;
      setPlan(p);
      setGroups(await api.groups());
    } catch (e) {
      setErr(String(e));
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

  const selectTunnel = (tn: string) => {
    setSelected(tn);
    setTab("Tunnel");
  };

  return (
    <div className="app">
      <Header plan={plan} />
      <BudgetBar budget={budget} loading={loading} onChange={onBudget} />
      {err && <div className="banner danger" style={{ margin: 10 }}>{err}</div>}
      <div className="main">
        <MapView groups={groups} plan={plan} onSelectTunnel={selectTunnel} />
        <div className="right-pane">
          <div className="tabs">
            {TABS.map((t) => (
              <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
                {t}
              </button>
            ))}
          </div>
          <div className="tab-body">
            {tab === "Plan" && <PlanPanel plan={plan} diff={diff} onSelectTunnel={selectTunnel} />}
            {tab === "Tunnel" && <TunnelDetail tunnelNumber={selected} />}
            {tab === "Findings" && <FindingsPanel tunnels={tunnels} onChanged={onFindingsChanged} />}
            {tab === "Memo" && <MemoPanel plan={plan} />}
            {tab === "Assumptions" && <AssumptionsPanel />}
            {tab === "Data notes" && <DataNotesPanel />}
          </div>
        </div>
      </div>
      <div className="footer-note">
        Planning tool using public FHWA data and stated assumptions. Not an engineering assessment.
      </div>
    </div>
  );
}
