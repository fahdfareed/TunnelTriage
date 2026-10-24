export interface Health {
  ok: boolean;
  data_year: number;
  n_tunnels: number;
  n_rows: number;
  n_scored_rows: number;
  dictionary_source: string;
  llm_provider: string;
}

export interface Group {
  group_id: string;
  name: string;
  lat: number | null;
  lon: number | null;
  segments: string[];
  adt_max: number;
  risk_now: number;
}

export interface Tunnel {
  tunnel_number: string;
  name: string;
  year_built: number;
  year_rehab: number;
  adt: number;
  adtt: number;
  length_ft: number;
  under_water: boolean;
  lat: number | null;
  lon: number | null;
  last_inspection_date: string | null;
  inspection_interval_months: number;
  group_id: string;
  risk_now?: number;
}

export interface ElementRow {
  key: string;
  element_number: number;
  epn: number;
  total: number;
  cs: [number, number, number, number];
  shares: [number, number, number, number];
  dq_flags: string[];
  scored: boolean;
  element_name: string;
  category: string;
  criticality: number;
  risk_now: number;
}

export interface ForecastPoint {
  year: number;
  risk: number;
}

export interface TunnelDetail {
  tunnel: Tunnel;
  elements: ElementRow[];
  forecast: ForecastPoint[];
}

export interface PlanItem {
  action_id: string;
  rank: number;
  tunnel_number: string;
  tunnel_name: string;
  group_id: string;
  element_number: number;
  element_name: string;
  action: string;
  qty: number;
  cost_point: number;
  cost_low: number;
  cost_high: number;
  benefit: number;
  benefit_per_million: number;
  risk_now_row: number;
  reason_codes: string[];
}

export interface Waiting {
  cost_now: number;
  cost_in_2y: number;
  cost_increase_pct: number;
  extra_risk_2y: number;
  note: string;
}

export interface Plan {
  plan_id: string;
  budget: number;
  horizon: number;
  solver: string;
  funded: PlanItem[];
  unfunded_top: PlanItem[];
  total_cost_point: number;
  total_cost_low: number;
  total_cost_high: number;
  risk_now: number;
  risk_h_do_nothing: number;
  risk_h_with_plan: number;
  risk_reduction_pct: number;
  by_group: { group_id: string; funded_cost: number }[];
  forced_unmet: string[];
  waiting: Waiting;
}

export interface Finding {
  finding_id: string;
  tunnel_number: string;
  element_number: number;
  epn: number;
  quantity: number;
  condition_state: number;
  source: string;
  note: string;
  created_at: string;
}

export interface ParseResult {
  proposal: {
    tunnel_number: string | null;
    element_number: number | null;
    quantity: number;
    condition_state: number;
    note: string;
  };
  tunnel_candidates: { tunnel_number: string; label: string; score: number }[];
  element_candidates: { element_number: number; label: string; score: number }[];
  used_llm: boolean;
}

export interface Memo {
  markdown: string;
  source: string;
  warnings: string[];
}
